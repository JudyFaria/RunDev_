import pandas as pd

def filter_telemetry_by_laps(df_telemetry, df_laps, selected_laps):
    """
    Filtra a telemetria mantendo apenas os dados dos Laps selecionados.
    """
    if df_telemetry.empty or df_laps.empty or not selected_laps:
        return df_telemetry.iloc[0:0] # Retorna DataFrame vazio

    df_filtered = pd.DataFrame()
    
    # Converte as colunas de tempo para o tipo datetime do Pandas
    df_telemetry['timestamp'] = pd.to_datetime(df_telemetry['timestamp'])
    df_laps['start_time'] = pd.to_datetime(df_laps['start_time'])
    df_laps['timestamp'] = pd.to_datetime(df_laps['timestamp']) # Momento em que o lap termina
    
    for lap_num in selected_laps:
        lap_info = df_laps[df_laps['lap_number'] == lap_num]
        
        if not lap_info.empty:
            start = lap_info['start_time'].iloc[0]
            end = lap_info['timestamp'].iloc[0]
            
            # Máscara para pegar a telemetria entre o start_time e o end da volta
            mask = (df_telemetry['timestamp'] >= start) & (df_telemetry['timestamp'] <= end)
            df_filtered = pd.concat([df_filtered, df_telemetry[mask]])
            
    # Retorna os dados filtrados em ordem cronológica
    return df_filtered.sort_values(by='timestamp')