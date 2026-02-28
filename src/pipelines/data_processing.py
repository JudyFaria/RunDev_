import pandas as pd
import os
from src.ingestors.strava_api import get_recent_activities, get_activity_streams
from src.core.metrics import calculate_decoupling
from src.core.autolaps import generate_auto_laps
from src.core.weather import fetch_weather_and_timezone
from src.storage.file_manager import save_fit_data


def sync_strava_to_app():
    print("🔄 Sincronização Inteligente Iniciada...")

    # Puxa os treinos recentes do Strava
    corridas = get_recent_activities(limit=30)

    if not corridas:
        return 0 # 0 novos treinos
    
    path_file = 'data/processed/atividades_processadas.csv'
    ids_existentes = []

    # Verifica se o arquivo já existe e carrega os IDs existentes
    if os.path.exists(path_file):
        df_existente = pd.read_csv(path_file)
        ids_existentes = df_existente['id'].astype(str).tolist()

    df_summary = pd.DataFrame(corridas)
    
    # Calcula o EF diretamente com os dados agregados do Strava
    def calc_ef_resumo(row):
        hr = row.get('average_heartrate', 0)
        spd = row.get('average_speed', 0)
        if pd.isna(hr) or hr == 0 or pd.isna(spd) or spd == 0:
            return None
        return round((spd * 60) / hr, 2)

    df_summary['efficiency_factor'] = df_summary.apply(calc_ef_resumo, axis=1)

    resultados_avancados = []
    novos_treinos_baixados = 0

    # Processa APENAS os treinos que ainda não estão no banco de dados
    for corrida in corridas:
        atividade_id = str(corrida['id'])
        
        if atividade_id in ids_existentes:
            continue # Pula se já foi sincronizado antes!
            
        print(f"📥 Novo treino detectado: {corrida['name']}...")
        streams = get_activity_streams(atividade_id)
        
        if streams and 'time' in streams:
            # Pega a data e hora oficial de início do treino
            start_date = pd.to_datetime(corrida['start_date'])
            
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
            
            # Converte os segundos em timestamps reais (Obrigatório para o Clima e Gráficos)
            df_stream['timestamp'] = start_date + pd.to_timedelta(df_stream['time_seconds'], unit='s')
            
            # Limpeza
            df_stream = df_stream[(df_stream['heartrate'] > 40) & (df_stream['velocity_smooth'] > 1.0)].copy()
            
            # --- CHAMA A NOSSA INTELIGÊNCIA (Clima, Laps, EF, Decoupling) ---
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
            
            # 🔥 O Pulo do Gato: Salva na pasta do Laboratório FIT! (Passando df_stream renomeado temporalmente para arquivo virtual)
            save_fit_data(f"Strava_{atividade_id}.fit", df_stream, df_laps, weather_info)
            
            if decoupling is not None:
                resultados_avancados.append({'id': corrida['id'], 'decoupling': decoupling})
            
            novos_treinos_baixados += 1

    # Atualiza o CSV do Histórico Strava com os novos treinos combinados
    if novos_treinos_baixados > 0:
        if resultados_avancados:
            df_avancado = pd.DataFrame(resultados_avancados)
            df_novos = df_summary[df_summary['id'].astype(str).isin([str(x['id']) for x in resultados_avancados])].copy()
            df_novos = df_novos.merge(df_avancado, on='id', how='left')
        else:
            df_novos = df_summary[df_summary['id'].astype(str).isin([r['id'] for r in corridas if str(r['id']) not in ids_existentes])]
            
        os.makedirs('data/processed', exist_ok=True)
        
        # Se o arquivo já existe, anexa (append). Se não, cria um novo.
        if os.path.exists(path_file):
            df_existente = pd.read_csv(path_file)
            df_final = pd.concat([df_existente, df_novos], ignore_index=True)
        else:
            df_final = df_novos
            
        df_final.to_csv(path_file, index=False)
        print(f"✅ {novos_treinos_baixados} novos treinos sincronizados e salvos!")
    else:
        print("✅ Tudo atualizado! Nenhum treino novo no Strava.")

    return novos_treinos_baixados
