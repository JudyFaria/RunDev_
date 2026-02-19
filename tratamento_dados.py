import pandas as pd
import numpy as np
import requests

from handshake import activities, access_token

# --- 1. MÉTRICAS FISIOLÓGICAS (O Diferencial do App) ---

def calculate_efficiency_factor(row):
    """
    EF = Velocidade Média (m/min) / Frequência Cardíaca Média (bpm)[cite: 34].
    Prova matemática de que o treino base está funcionando[cite: 36].
    """
    # O Strava usa 'average_heartrate' no JSON de resumo [cite: 23]
    hr_media = row.get('average_heartrate', 0)
    
    if hr_media and hr_media > 0:
        # average_speed vem em m/s; convertemos para m/min [cite: 34]
        velocidade_m_min = row['average_speed'] * 60
        return velocidade_m_min / hr_media
    return None

def calculate_decoupling(df_stream):
    """
    Compara a eficiência da 1ª metade do treino com a 2ª metade[cite: 38].
    Se o desvio for > 5%, a resistência aeróbica precisa melhorar[cite: 39].
    """
    if df_stream is None or 'heartrate' not in df_stream:
        return None
        
    metade = len(df_stream) // 2
    bloco_1 = df_stream.iloc[:metade]
    bloco_2 = df_stream.iloc[metade:]

    # EF do Bloco 1
    ef_1 = (bloco_1['velocity_smooth'].mean() * 60) / bloco_1['heartrate'].mean()
    # EF do Bloco 2
    ef_2 = (bloco_2['velocity_smooth'].mean() * 60) / bloco_2['heartrate'].mean()

    # Fórmula: ((EF_1 - EF_2) / EF_1) * 100 [cite: 40]
    decoupling = ((ef_1 - ef_2) / ef_1) * 100
    return decoupling


# --- 2. COMUNICAÇÃO COM API (O Cérebro) ---

def get_activity_streams(activity_id, token):
    """Baixa os dados segundo a segundo (Streams)[cite: 23]."""
    url = f"https://www.strava.com/api/v3/activities/{activity_id}/streams"
    params = {'keys': 'time,heartrate,velocity_smooth', 'key_by_type': True}
    headers = {'Authorization': f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        if 'message' in data:
            return None
        return data
    except Exception:
        return None


# --- 3. EXECUÇÃO DO MOTOR DE DADOS ---

if __name__ == "__main__":
    print(f"🚀 Rodando RunDev Analytics - Versão {1.0} (Draft) [cite: 1, 2]")
    
    # Criando o DataFrame do Pandas [cite: 14, 51]
    df_summary = pd.DataFrame(activities)

    # Aplicando sua função de Fator de Eficiência [cite: 52]
    df_summary['efficiency_factor'] = df_summary.apply(calculate_efficiency_factor, axis=1)

    print(f"✅ EF calculado para {len(df_summary)} atividades.")

    # Analisando desacoplamento aeróbico para todas as atividades [cite: 53]
    decoupling_results = []
    
    for activity in activities:
        streams = get_activity_streams(activity['id'], access_token)
        
        if streams and 'time' in streams:
            df_stream = pd.DataFrame({
                'time': streams['time']['data'],
                'heartrate': streams['heartrate']['data'],
                'velocity_smooth': streams['velocity_smooth']['data']
            })

            # Limpeza de ruídos conforme o guia de estudos [cite: 23, 67]
            df_stream = df_stream[(df_stream['heartrate'] > 40) & (df_stream['velocity_smooth'] < 8.0)]
            
            decoupling = calculate_decoupling(df_stream)
            if decoupling is not None:
                decoupling_results.append({
                    'activity_name': activity['name'],
                    'activity_id': activity['id'],
                    'decoupling': decoupling
                })
                print(f"📈 {activity['name']}: Desacoplamento Aeróbico (Pw:Hr): {decoupling:.2f}% [cite: 37]")
    
    # Adicionando resultados ao DataFrame
    if decoupling_results:
        df_decoupling = pd.DataFrame(decoupling_results)
        df_summary = df_summary.merge(df_decoupling[['activity_id', 'decoupling']], 
                                      left_on='id', right_on='activity_id', how='left')

    # Exportando para o banco local do Mobile [cite: 54]
    df_summary.to_csv('atividades_processadas.csv', index=False)
    print("\n📂 Dados salvos para a Fase 3 (Mobile)[cite: 55].")