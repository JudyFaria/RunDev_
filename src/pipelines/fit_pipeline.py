import pandas as pd

from src.ingestors.fit_loader import read_fit_file, read_fit_laps
from src.core.metrics import calculate_efficiency_factor, calculate_decoupling
from src.core.autolaps import generate_auto_laps
from src.core.weather import fetch_weather_and_timezone

def process_fit_file(file_path):
    """
        Processa um arquivo FIT, calculando métricas, Auto-Laps, fuso horário dinâmico e clima.
    """
    # Extração
    print("🚀 PIPELINE INICIADO: Chamando ingestores...")
    df_fit = read_fit_file(file_path)

    if df_fit is None or df_fit.empty:
        print("❌ PIPELINE: Falha ao extrair telemetria do arquivo.")
        return None, None, None, None
    
   
    # Formata a data inicial
    df_fit['timestamp'] = pd.to_datetime(df_fit['timestamp'])

    # --- Integração com API de Clima e Fuso Horário ---
    lat, lon = None, None
    weather_info = None
    timezone_offset = -3.0 # Default para Brasil (UTC-3)

    #  Tenta pegar as coordenadas do treino a partir da telemetria
    if 'lat' in df_fit.columns and 'lon' in df_fit.columns:
        df_coords = df_fit.dropna(subset=['lat', 'lon'])

        if not df_coords.empty:
            lat = df_coords.iloc[0]['lat']
            lon = df_coords.iloc[0]['lon']

    # Horário de início do treino (primeiro timestamp) \ ainda em UTC
    start_time_utc = df_fit['timestamp'].iloc[0]

    # Faz a requisição para a API de clima e fuso horário se tivermos as coordenadas
    if lat is not None and lon is not None:
        print(f"🌍 GPS detectado (Lat: {lat:.4f}, Lon: {lon:.4f}). Buscando API Open-Meteo...")
        weather_info = fetch_weather_and_timezone(lat, lon, start_time_utc)

        if weather_info:
            timezone_offset = weather_info['timezone_offset_hours']
            print(f"🌦️ Sucesso API! {weather_info['temperatura_celsius']}°C | Fuso: {weather_info['timezone_name']} (UTC{timezone_offset:+})")

        else:
            print("⚠️ API falhou. Usando UTC-3 padrão.")

    else:
        print("⚠️ Sem GPS no treino. Usando UTC-3 padrão.")

    df_fit['timestamp'] = df_fit['timestamp'] + pd.to_timedelta(timezone_offset, unit='h')
    
    # limpeza e transformação de dados 
    df_fit = df_fit.rename(columns={'heart_rate': 'heartrate', 'speed': 'velocity_smooth'}) 
    df_fit_clean = df_fit[(df_fit['heartrate'] > 40) & (df_fit['velocity_smooth'] > 1.0)].copy()
    df_fit_clean = df_fit_clean.sort_values('timestamp').reset_index(drop=True)

    # Cálculo Matemático da Distância (d = v * t)
    # Se a Zepp não mandou a distância na telemetria, nós criamos a coluna!
    if 'distance' not in df_fit_clean.columns or df_fit_clean['distance'].isnull().all():
        print("⚠️ Coluna 'distance' ausente. A calcular distância via Integração (Velocidade x Tempo)...")

        # calcula a diferença de tempo em segundos entre cada registro
        df_fit_clean['time_diff'] = df_fit_clean['timestamp'].diff().dt.total_seconds().fillna(1.0)

        # Evita saltos absurdos de GPS
        df_fit_clean.loc[df_fit_clean['time_diff'] > 10, 'time_diff'] = 1.0

        # Calcula os metros percorridos naquele segundo e vai somando (cumsum)
        df_fit_clean['dist_step'] = df_fit_clean['velocity_smooth'] * df_fit_clean['time_diff']
        df_fit_clean['distance'] = df_fit_clean['dist_step'].cumsum()

    # Geração de Laps artificiais (Auto-Laps) a cada 1km
    print("⏱️ PIPELINE: A gerar parciais (Auto-Laps) a cada 1000m...")
    df_laps = generate_auto_laps(df_fit_clean, lap_distance_m=1000)

    # Cálculos
    decoupling = calculate_decoupling(df_fit_clean)
    efficiency = calculate_efficiency_factor(df_fit_clean)

    print("✅ PIPELINE CONCLUÍDO")
    # 4. Retorno (Ordem: Telemetria, Decoupling, Efficiency, Laps)
    return df_fit_clean, decoupling, efficiency, df_laps, weather_info