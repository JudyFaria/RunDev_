import pandas as pd
from fitparse import FitFile

def read_fit_file(file_path):
    """
        Lê um arquivo .fit bruto do relógio e extrai a telemetria segundo a segundo.
    """
    print(f"⏱️ Lendo arquivo FIT: {file_path}...")
    try:
        # Abre o arquivo binário do relógio
        fitfile = FitFile(file_path)
    
    except Exception as e:
        print(f"❌ Erro ao ler o arquivo FIT: {e}")
        return None
    
    registros = []

    # O relógio grava os dados segundo a segundo nas mensagens do tipo 'record'
    for record in fitfile.get_messages('record'):
        registro = {}
        
        for data in record:
            # Adicionamos position_lat e position_long na lista de busca
            if data.name in ['timestamp', 'heart_rate', 'speed', 'distance', 'position_lat', 'position_long']:
                registro[data.name] = data.value

        # Só adiciona se tiver timestamp e batimento
        if 'timestamp' in registro and 'heart_rate' in registro:
            # Converte as coordenadas de semicírculos para graus (se existirem no registro)
            if 'position_lat' in registro and registro['position_lat'] is not None:
                registro['lat'] = registro['position_lat'] * (180.0 / (2**31))
            if 'position_long' in registro and registro['position_long'] is not None:
                registro['lon'] = registro['position_long'] * (180.0 / (2**31))
                
            registros.append(registro)

    # Transforma a lista de dados brutos num DataFrame
    df = pd.DataFrame(registros)

    if df.empty:
        print("⚠️ Nenhum registro válido encontrado no arquivo FIT.")
        return None
    
    print(f"✅ Arquivo FIT processado com sucesso! {len(df)} registros extraídos.")
    return df

def read_fit_laps(file_path):
    """
        Lê um arquivo .fit e extrai o resumo de cada volta (lap),
        ideal para Fartleks, intervalados e autolaps do relógio.
    """
    print(f"⏱️ Lendo LAPS do arquivo FIT: {file_path}...")
    try:
        fitfile = FitFile(file_path)
    except Exception as e:
        print(f"❌ Erro ao ler o arquivo FIT para laps: {e}")
        return None

    laps_data = []

    for i, lap_msg in enumerate(fitfile.get_messages('lap')):
        lap_dict = {'lap_number': i + 1}
        
        for data in lap_msg:
            # Pegamos as métricas de resumo da volta
            if data.name in ['start_time', 'timestamp', 'total_elapsed_time', 'total_distance', 'avg_speed', 'avg_heart_rate', 'max_heart_rate']:
                lap_dict[data.name] = data.value
        
        # Formatação de Distância (metros para km)
        distancia_m = lap_dict.get('total_distance', 0)
        if pd.notnull(distancia_m):
            lap_dict['distance_km'] = round(distancia_m / 1000, 3)

        # Formatação do Pace (min/km)
        velocidade_ms = lap_dict.get('avg_speed', 0)
        if pd.notnull(velocidade_ms) and velocidade_ms > 0:
            pace_decimal = (1000 / velocidade_ms) / 60
            minutos = int(pace_decimal)
            segundos = int((pace_decimal - minutos) * 60)
            lap_dict['pace_str'] = f"{minutos}:{segundos:02d}"
        else:
            lap_dict['pace_str'] = "0:00"

        laps_data.append(lap_dict)

    df_laps = pd.DataFrame(laps_data)

    if df_laps.empty:
        print("⚠️ Nenhuma lap válida encontrada no arquivo FIT.")
        return None
    
    print(f"✅ Laps processadas com sucesso! {len(df_laps)} voltas extraídas.")
    
    # --- ADICIONE ESTE PRINT AQUI ---
    print(f"✅ DEBUG INGESTOR: Laps extraídas com sucesso! Colunas encontradas: {df_laps.columns.tolist()}")
    print(df_laps.head()) 
    # ---------------------------------
    
    return df_laps