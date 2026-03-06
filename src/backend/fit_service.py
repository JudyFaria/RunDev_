import os
import tempfile
import json
import pandas as pd

from src.pipelines.fit_pipeline import process_fit_file
from src.core.metrics import calculate_decoupling, calculate_efficiency_factor
from src.core.weather import normalize_metrics_for_climate
from src.storage.file_manager import save_fit_data, TELEMETRY_DIR, LAPS_DIR, METADATA_DIR

def get_available_activities():
    """Lista todos os treinos disponíveis no banco local."""
    if os.path.exists(TELEMETRY_DIR):
        treinos = [f.replace('.csv', '') for f in os.listdir(TELEMETRY_DIR) if f.endswith('.csv')]
        treinos.sort(reverse=True)
        return treinos
    return []

def process_manual_upload(file_bytes):
    """Lida com a criação de arquivo temporário, processamento e salvamento do FIT."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".fit") as tmp_file:
        tmp_file.write(file_bytes)
        temp_path = tmp_file.name

    try:
        df_fit_clean, decoupling, efficiency, df_laps, weather_info = process_fit_file(temp_path)
        if df_fit_clean is not None:
            activity_id = save_fit_data(temp_path, df_fit_clean, df_laps, weather_info)
            return activity_id
        return None
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def get_activity_analysis(activity_id, laps_selecionados=None):
    """
    Busca os dados do treino, aplica filtros de trecho (laps) e calcula as métricas finais.
    Retorna um dicionário pronto para o Front-end renderizar.
    """
    # 1. Carrega Dados
    caminho_telemetria = os.path.join(TELEMETRY_DIR, f"{activity_id}.csv")
    caminho_laps = os.path.join(LAPS_DIR, f"{activity_id}.csv")
    caminho_metadata = os.path.join(METADATA_DIR, f"{activity_id}.json")

    df_telemetry = pd.read_csv(caminho_telemetria) if os.path.exists(caminho_telemetria) else pd.DataFrame()
    df_laps = pd.read_csv(caminho_laps) if os.path.exists(caminho_laps) else pd.DataFrame()
    
    weather_info = None
    if os.path.exists(caminho_metadata):
        with open(caminho_metadata, 'r', encoding='utf-8') as f:
            weather_info = json.load(f)

    # 2. Lógica de Filtragem de Laps
    df_analise = df_telemetry.copy()
    if laps_selecionados and not df_laps.empty:
        df_telemetry['timestamp'] = pd.to_datetime(df_telemetry['timestamp'])
        df_laps['start_time'] = pd.to_datetime(df_laps['start_time'])
        df_laps['timestamp'] = pd.to_datetime(df_laps['timestamp'])
         
        df_filtered = pd.DataFrame()
        for lap_num in laps_selecionados:
            lap_info = df_laps[df_laps['lap_number'] == lap_num]
            if not lap_info.empty:
                start = lap_info['start_time'].iloc[0]
                end = lap_info['timestamp'].iloc[0]
                mask = (df_telemetry['timestamp'] >= start) & (df_telemetry['timestamp'] <= end)
                df_filtered = pd.concat([df_filtered, df_telemetry[mask]])

        if not df_filtered.empty:
            df_analise = df_filtered.sort_values(by='timestamp')

    # 3. Cálculo de Métricas
    decoupling_atual = calculate_decoupling(df_analise)
    efficiency_atual = calculate_efficiency_factor(df_analise)
    
    clima_temp = weather_info['temperatura_celsius'] if weather_info else None
    clima_humidity = weather_info['umidade_percentual'] if weather_info else None

    efficiency_normalized, decoupling_normalized = normalize_metrics_for_climate(
        efficiency_atual, decoupling_atual, clima_temp, clima_humidity
    )

    efficiency_delta = (efficiency_normalized - efficiency_atual) if (efficiency_normalized is not None and efficiency_atual is not None) else 0
    decoupling_delta = (decoupling_normalized - decoupling_atual) if (decoupling_normalized is not None and decoupling_atual is not None) else 0

    # Distância e FC
    if laps_selecionados and not df_laps.empty:
        dist_trecho = df_laps[df_laps['lap_number'].isin(laps_selecionados)]['distance_km'].sum()
    elif not df_telemetry.empty and 'distance' in df_telemetry.columns:
        dist_trecho = (df_telemetry['distance'].max() / 1000)
    else:
        dist_trecho = 0.0

    fc_media = df_analise['heartrate'].mean() if not df_analise.empty and 'heartrate' in df_analise.columns else 0

    return {
        "weather_info": weather_info,
        "df_telemetry": df_telemetry,
        "df_laps": df_laps,
        "df_analise": df_analise, # Para os gráficos
        "metrics": {
            "decoupling_atual": decoupling_atual,
            "decoupling_normalized": decoupling_normalized,
            "decoupling_delta": decoupling_delta,
            "efficiency_atual": efficiency_atual,
            "efficiency_normalized": efficiency_normalized,
            "efficiency_delta": efficiency_delta,
            "clima_temp": clima_temp,
            "dist_trecho": dist_trecho,
            "fc_media": fc_media
        }
    }