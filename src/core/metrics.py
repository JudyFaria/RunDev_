import pandas as pd

def calculate_efficiency_factor(df):
    """
    Calcula o Fator de Eficiência (EF) = Velocidade (metros/minuto) / Frequência Cardíaca Média.
    """
    if df is None or df.empty:
        return None

    # Aceita tanto o nome antigo (speed) quanto o novo gerado no pipeline (velocity_smooth)
    coluna_vel = 'velocity_smooth' if 'velocity_smooth' in df.columns else 'speed'
    
    if coluna_vel not in df.columns or 'heartrate' not in df.columns:
        return None

    # Calcula as médias do trecho
    avg_speed_ms = df[coluna_vel].mean()
    avg_hr = df['heartrate'].mean()

    # Proteção contra divisões por zero ou dados ausentes
    if pd.isna(avg_hr) or avg_hr == 0 or pd.isna(avg_speed_ms) or avg_speed_ms == 0:
        return None

    # O EF padrão na corrida é calculado usando metros por minuto
    speed_m_min = avg_speed_ms * 60
    ef = speed_m_min / avg_hr

    return round(ef, 2)


def calculate_decoupling(df_stream):
    """
        Calcula o Desacoplamento Aeróbico (%).
        Compara a eficiência da 1ª metade vs 2ª metade.
    """
    if df_stream is None or df_stream.empty or 'heartrate' not in df_stream:
        return None
        
    # Divide o treino ao meio
    metade = len(df_stream) // 2
    bloco_1 = df_stream.iloc[:metade]
    bloco_2 = df_stream.iloc[metade:]

    # Evita divisão por zero se o HR for 0 ou nulo
    if bloco_1['heartrate'].mean() == 0 or bloco_2['heartrate'].mean() == 0:
        return None

    # EF do Bloco 1
    ef_1 = (bloco_1['velocity_smooth'].mean() * 60) / bloco_1['heartrate'].mean()
    # EF do Bloco 2
    ef_2 = (bloco_2['velocity_smooth'].mean() * 60) / bloco_2['heartrate'].mean()

    # Fórmula: ((EF_1 - EF_2) / EF_1) * 100
    if ef_1 == 0: return None
    
    decoupling = ((ef_1 - ef_2) / ef_1) * 100
    return decoupling