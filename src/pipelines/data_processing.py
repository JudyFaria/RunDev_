import pandas as pd
import os
from src.ingestors.strava_api import get_recent_activities, get_activity_streams
from src.core.metrics import calculate_efficiency_factor, calculate_decoupling

def run_pipeline():
    print("🚀 Iniciando o Processamento de Dados (RunDev Pipeline)...")
    
    # Busca as últimas 100 corridas
    corridas = get_recent_activities(limit=100)
    
    if not corridas:
        print("❌ Nenhuma corrida encontrada ou erro na API.")
        return

    # DataFrame inicial com o resumo das atividades
    df_summary = pd.DataFrame(corridas)
    
    # Aplica métricas simples
    df_summary['efficiency_factor'] = df_summary.apply(calculate_efficiency_factor, axis=1)
    
    resultados_avancados = []

    # Baixar dados segundo a segundo de cada corrida
    for corrida in corridas:
        print(f"📥 Processando: {corrida['name']}...")
        streams = get_activity_streams(corrida['id'])
        
        if streams and 'time' in streams:
            
            # Transforma o JSON em DataFrame
            df_stream = pd.DataFrame({
                'time': streams['time']['data'],
                'heartrate': streams['heartrate']['data'],
                'velocity_smooth': streams['velocity_smooth']['data']
            })

            # Limpeza de dados (Filtra ruídos de GPS/BPM)
            df_stream = df_stream[(df_stream['heartrate'] > 40) & (df_stream['velocity_smooth'] < 8.0)]
            
            # Chama a fórmula de Desacoplamento
            decoupling = calculate_decoupling(df_stream)
            
            if decoupling is not None:
                resultados_avancados.append({
                    'id': corrida['id'],  # Usamos 'id' para bater com o df_summary
                    'decoupling': decoupling
                })
                print(f"   📈 Desacoplamento: {decoupling:.2f}%")

    # Junta os resultados avançados com o resumo
    if resultados_avancados:
        df_avancado = pd.DataFrame(resultados_avancados)
        df_final = df_summary.merge(df_avancado, on='id', how='left')
        
        # Cria a pasta data/processed se não existir
        os.makedirs('data/processed', exist_ok=True)
        
        # Salva o arquivo CSV para o Streamlit ler depois!
        caminho_arquivo = 'data/processed/atividades_processadas.csv'
        df_final.to_csv(caminho_arquivo, index=False)
        print(f"\n✅ Sucesso! Dados salvos em: {caminho_arquivo}")

if __name__ == "__main__":
    run_pipeline()