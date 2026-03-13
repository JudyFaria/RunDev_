import pandas as pd
import os
from src.ingestors.strava_api import get_recent_activities, get_activity_streams
from src.core.metrics import calculate_decoupling
from src.core.autolaps import generate_auto_laps
from src.core.weather import fetch_weather_and_timezone
from src.storage.file_manager import save_fit_data

from src.storage.database import SessionLocal
from src.storage.db_models import Treino
from src.storage.repository import salvar_treino

def sync_strava_to_app():
    print("🔄 Sincronização Inteligente Iniciada...")

    # Puxa os treinos recentes do Strava
    activities = get_recent_activities(limit=200)

    if not activities:
        return 0 # 0 novos treinos
    
    # path_file = 'data/processed/atividades_processadas.csv'

    # Abre a conexão com o banco de dados
    db = SessionLocal()

    try:
        # pega os IDs do banco de dados
        ids_existentes = [treino.strava_id for treino in db.query(Treino.strava_id).all()]
    
        df_summary = pd.DataFrame(activities)
        
        # Calcula o EF diretamente com os dados agregados do Strava
        def calc_ef_resumo(row):
            hr = row.get('average_heartrate', 0)
            spd = row.get('average_speed', 0)
            if pd.isna(hr) or hr == 0 or pd.isna(spd) or spd == 0:
                return None
            return round((spd * 60) / hr, 2)

        df_summary['efficiency_factor'] = df_summary.apply(calc_ef_resumo, axis=1)

        novos_treinos_baixados = 0

        # Processa APENAS os treinos que ainda não estão no banco de dados
        for atividade in activities:
            atividade_id = str(atividade['id'])
            tipo_atividade = atividade.get('type') # Ex: 'Run', 'WeightTraining', 'Workout'
            
            if atividade_id in ids_existentes:
                continue # Pula se já foi sincronizado antes!
                
            print(f"📥 Nova atividade detectada: {atividade['name']}...")
            streams = get_activity_streams(atividade_id)
            
            if streams and 'time' in streams:
                start_date = pd.to_datetime(atividade['start_date'])
                
                # Constrói o DataFrame compatível com o nosso Laboratório
                df_stream = pd.DataFrame({
                    'time_seconds': streams['time']['data'],
                    'heartrate': streams['heartrate']['data'] if 'heartrate' in streams else None,
                    'velocity_smooth': streams['velocity_smooth']['data'] if 'velocity_smooth' in streams else None,
                    'distance': streams['distance']['data'] if 'distance' in streams else None
                })
                
                # GPS: Separa latitude e longitude se o Strava tiver enviado
                if 'latlng' in streams and streams['latlng']['data']:
                    df_stream['lat'] = [x[0] if len(x) == 2 else None for x in streams['latlng']['data']]
                    df_stream['lon'] = [x[1] if len(x) == 2 else None for x in streams['latlng']['data']]
                
                df_stream['timestamp'] = start_date + pd.to_timedelta(df_stream['time_seconds'], unit='s')
                
                # Limpeza
                df_stream = df_stream[(df_stream['heartrate'] > 40) & (df_stream['velocity_smooth'] > 1.0)].copy()
                
                weather_info = None
                if 'lat' in df_stream.columns and not df_stream.empty:
                    lat, lon = df_stream['lat'].iloc[0], df_stream['lon'].iloc[0]
                    weather_info = fetch_weather_and_timezone(lat, lon, start_date)
                
                if weather_info:
                    df_stream['timestamp'] = df_stream['timestamp'] + pd.Timedelta(hours=weather_info['timezone_offset_hours'])
                else:
                    df_stream['timestamp'] = df_stream['timestamp'] - pd.Timedelta(hours=3) # Fallback BR

                df_laps = generate_auto_laps(df_stream, lap_distance_m=1000)
                decoupling = calculate_decoupling(df_stream)
                
                # Mantemos a geração do arquivo local temporário (útil para backup dos streams brutos)
                save_fit_data(f"Strava_{atividade_id}.fit", df_stream, df_laps, weather_info)
                
            else:
                print("   ℹ️ Atividade sem GPS (Treino Físico). Pulando análise de streams e autolaps.")
                
            novo_registro = salvar_treino(db, atividade)    
            novos_treinos_baixados += 1

        if novos_treinos_baixados > 0:
            print(f"✅ {novos_treinos_baixados} novos treinos sincronizados e salvos no Banco de Dados!")
        else:
            print("✅ Tudo atualizado! Nenhum treino novo no Strava.")

        return novos_treinos_baixados

    finally:
        # Fundamental: Sempre fechar a conexão com o banco no final!
        db.close()

