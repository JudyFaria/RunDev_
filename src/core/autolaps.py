import pandas as pd

def generate_auto_laps(df_telemetry, lap_distance_m=1000):
    """
    Gera as parciais (laps) artificialmente cortando a telemetria a cada X metros (padrão 1km).
    """
    if df_telemetry is None or df_telemetry.empty or 'distance' not in df_telemetry.columns:
        return None

    # Prepara os dados
    df_telemetry = df_telemetry.copy()
    df_telemetry['timestamp'] = pd.to_datetime(df_telemetry['timestamp'])
    df_telemetry = df_telemetry.sort_values('timestamp').reset_index(drop=True)

    laps_data = []
    current_lap = 1
    start_idx = 0
    target_distance = lap_distance_m

    for idx, row in df_telemetry.iterrows():
        # Quando atingir a marca de 1000m, 2000m, etc.
        if row['distance'] >= target_distance:
            # Recorta os dados apenas dessa volta
            lap_df = df_telemetry.iloc[start_idx:idx+1]
            
            dist_m = lap_df['distance'].iloc[-1] - lap_df['distance'].iloc[0]
            elapsed_time = (lap_df['timestamp'].iloc[-1] - lap_df['timestamp'].iloc[0]).total_seconds()
            
            # Calcula Pace real do trecho
            avg_speed = dist_m / elapsed_time if elapsed_time > 0 else 0
                
            avg_hr = lap_df['heartrate'].mean()
            max_hr = lap_df['heartrate'].max()

            # Formata o pace para min/km
            if avg_speed > 0:
                pace_decimal = (1000 / avg_speed) / 60
                mins = int(pace_decimal)
                secs = int((pace_decimal - mins) * 60)
                pace_str = f"{mins}:{secs:02d}"
            else:
                pace_str = "0:00"

            laps_data.append({
                'lap_number': current_lap,
                'distance_km': round(dist_m / 1000, 3),
                'total_elapsed_time': round(elapsed_time, 1),
                'pace_str': pace_str,
                'avg_heart_rate': round(avg_hr),
                'max_heart_rate': round(max_hr),
                'start_time': lap_df['timestamp'].iloc[0],
                'timestamp': lap_df['timestamp'].iloc[-1]
            })
            
            current_lap += 1
            start_idx = idx
            target_distance += lap_distance_m
            
    # Captura a última lap (o "quebrado" do final do treino, ex: os 300m finais de um treino de 5.3km)
    if start_idx < len(df_telemetry) - 1:
        lap_df = df_telemetry.iloc[start_idx:]
        dist_m = lap_df['distance'].iloc[-1] - lap_df['distance'].iloc[0]
        
        # Só salva se tiver corrido pelo menos 50 metros para evitar "lap fantasma" de GPS
        if dist_m > 50:
            elapsed_time = (lap_df['timestamp'].iloc[-1] - lap_df['timestamp'].iloc[0]).total_seconds()
            avg_speed = dist_m / elapsed_time if elapsed_time > 0 else 0
            avg_hr = lap_df['heartrate'].mean()
            max_hr = lap_df['heartrate'].max()

            if avg_speed > 0:
                pace_decimal = (1000 / avg_speed) / 60
                mins = int(pace_decimal)
                secs = int((pace_decimal - mins) * 60)
                pace_str = f"{mins}:{secs:02d}"
            else:
                pace_str = "0:00"

            laps_data.append({
                'lap_number': current_lap,
                'distance_km': round(dist_m / 1000, 3),
                'total_elapsed_time': round(elapsed_time, 1),
                'pace_str': pace_str,
                'avg_heart_rate': round(avg_hr),
                'max_heart_rate': round(max_hr),
                'start_time': lap_df['timestamp'].iloc[0],
                'timestamp': lap_df['timestamp'].iloc[-1]
            })

    return pd.DataFrame(laps_data)