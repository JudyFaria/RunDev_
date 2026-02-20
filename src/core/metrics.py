import pandas as pd

def calculate_efficiency_factor(row):
    """
        Calcula o Fator de Eficiência (EF).
        EF = Velocidade (m/min) / FC (bpm).
    """
    hr_media = row.get('average_heartrate', 0)
    
    if hr_media and hr_media > 0:
        
        # Converte m/s para m/min
        velocidade_m_min = row['average_speed'] * 60
        return velocidade_m_min / hr_media
    
    return None


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