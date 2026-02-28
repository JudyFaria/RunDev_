import os
import pandas as pd
import shutil
import json

from datetime import datetime


# Definindo as patas 
DATA_DIR = "data"
TELEMETRY_DIR = os.path.join(DATA_DIR, "telemetry")
LAPS_DIR = os.path.join(DATA_DIR, "laps")
METADATA_DIR = os.path.join(DATA_DIR, "metadata")
RAW_DIR = os.path.join(DATA_DIR, "raw")

def ensure_directories_exist():
    '''
        Garante que a estrutura das pastas existe.
    '''
    os.makedirs(TELEMETRY_DIR, exist_ok=True)
    os.makedirs(LAPS_DIR, exist_ok=True)
    os.makedirs(METADATA_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)

def save_fit_data(temp_file_path, df_telemetry, df_laps, weather_info=None):
    '''
        Salva o arquivo .fit original e os DataFrames processados em CSV e metadados em JSON.
    '''
    
    ensure_directories_exist()

    # Vamos criar um ID único baseado na data e hora atual (ou você pode puxar o timestamp do primeiro recorde do df_telemetry)
    # Por simplicidade, vamos usar o momento do upload como ID, ou se df_telemetry não for vazio, o timestamp do primeiro registro.
    try:
        if not df_telemetry.empty and 'timestamp' in df_telemetry.columns:
            # Pega o primeiro timestamp para nomear o arquivo (formato YYYYMMDD_HHMMSS)
            primeiro_ts = pd.to_datetime(df_telemetry['timestamp'].iloc[0])
            activity_id = primeiro_ts.strftime("%Y%m%d_%H%M%S")
        else:
            activity_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    except:
         activity_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    
    # 1. copia o .fit bruto
    if temp_file_path and os.path.exists(temp_file_path):
        fit_dest = os.path.join(RAW_DIR, f"{activity_id}.fit")
        shutil.copy2(temp_file_path, fit_dest)
    else:
        print(f"ℹ️ Origem API detectada. Pulando cópia RAW, salvando apenas telemetria para ID: {activity_id}")
        
    # 2. salva a telemetria 
    telemetry_dest = os.path.join(TELEMETRY_DIR, f"{activity_id}.csv")
    df_telemetry.to_csv(telemetry_dest, index=False)

    # 3. salva as laps
    if df_laps is not None and not df_laps.empty:
        laps_dest = os.path.join(LAPS_DIR, f"{activity_id}.csv")
        df_laps.to_csv(laps_dest, index=False)

    # 4. salva o Clima
    if weather_info is not None:
        metadata_path = os.path.join(METADATA_DIR, f"{activity_id}.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(weather_info, f, ensure_ascii=False, indent=4)

    
    return activity_id 