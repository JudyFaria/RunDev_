import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="RunDev Analytics", page_icon="🏃‍♀️")

st.title("🏃‍♀️ RunDev Analytics")
st.markdown("Bem-vinda ao seu dashboard de telemetria de performance.")

caminho_dados = 'data/processed/atividades_processadas.csv'

# Verifica se o pipeline já rodou e gerou os dados
if os.path.exists(caminho_dados):
    
    # Lê os dados limpos em milissegundos
    df = pd.read_csv(caminho_dados)
    
    st.subheader("Últimos Treinos Processados")
    st.dataframe(df)
    
    # Exemplo de uma métrica rápida na tela
    media_ef = df['efficiency_factor'].mean()
    st.metric(label="Fator de Eficiência Médio (EF)", value=f"{media_ef:.2f}")

else:
    st.warning("⚠️ Nenhum dado processado encontrado. Por favor, rode o pipeline primeiro: `python src/pipelines/data_processing.py`")