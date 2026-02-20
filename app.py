import streamlit as st
import pandas as pd
import os

import tempfile
from src.pipelines.fit_pipeline import process_fit_file

def format_pace(speed_ms):
    '''
        Converte velocidade (m/s) para pace (min/km).
    '''
    if pd.isna(speed_ms) or speed_ms == 0:
        return "0:00"
    
    pace_min_decimal = (1000 / speed_ms) / 60  # pace em minutos
    mins = int(pace_min_decimal)
    secs = int((pace_min_decimal - mins) * 60)

    return f"{mins}:{secs:02d}"


# RAW DATA (.FIT) - UPLOAD E PROCESSAMENTO
st.subheader("🔬 Laboratório de Telemetria Bruta (Upload .FIT)")
st.markdown("Faça o upload do arquivo `.fit` original do seu relógio.")

arquivo_fit_upload = st.file_uploader("Arraste seu arquivo .fit aqui", type=["fit"])

if arquivo_fit_upload is not None:
    # O Streamlit precisa salvar temporariamente para o pipeline conseguir ler o caminho
    with tempfile.NamedTemporaryFile(delete=False, suffix=".fit") as tmp_file:
        tmp_file.write(arquivo_fit_upload.read())
        temp_path = tmp_file.name

    with st.spinner("Executando Pipeline de Dados FIT..."):
        # 🔥 AQUI ESTÁ A ARQUITETURA CORRETA! O Frontend chama o Pipeline.
        df_limpo, desacoplamento_fit = process_fit_file(temp_path)
        
    if df_limpo is not None:
        st.success("✅ Arquivo processado com sucesso!")
        
        col_A, col_B = st.columns(2)
        with col_A:
            if desacoplamento_fit is not None:
                st.metric(label="Desacoplamento (Real)", value=f"{desacoplamento_fit:.2f}%")
            else:
                st.warning("Não foi possível calcular o desacoplamento.")
                
        with col_B:
            st.metric(label="Pontos de Telemetria", value=f"{len(df_limpo)} segundos")
            
        with st.expander("Ver Tabela de Telemetria (Segundo a Segundo)"):
            st.dataframe(df_limpo)
            
    # Limpa o arquivo temporário
    os.remove(temp_path)

st.set_page_config(page_title="RunDev Analytics", page_icon="🏃‍♀️")

st.title("🏃‍♀️ RunDev Analytics")
st.markdown("Bem-vinda ao seu dashboard de telemetria de performance.")

caminho_dados = 'data/processed/atividades_processadas.csv'

# Verifica se o pipeline já rodou e gerou os dados
if os.path.exists(caminho_dados):
    
    # Lê os dados limpos em milissegundos
    df = pd.read_csv(caminho_dados)

    # Formatação dos dados para exibição
    df_view = pd.DataFrame()

    df_view['ID'] = df['id'].astype(str) # Transformando em texto para não formatar com vírgulas
    df_view['Treino'] = df['name']
    df_view['Distância (km)'] = (df['distance'] / 1000).round(2) 
    df_view['Duração (min)'] = (df['moving_time'] / 60).round(2)
    df_view['Pace Médio'] = df['average_speed'].apply(format_pace)
    df_view['FC Média (bpm)'] = df['average_heartrate'].round(0).astype('Int64')

    # Métricas avançadas
    df_view['Fator de Eficiência (EF)'] = df['efficiency_factor'].round(2)

    # Como nem toda atividade tem desacoplamento (ex: corridas muito curtas), tratamos isso
    if 'decoupling' in df.columns:
        df_view['Desacoplamento (%)'] = df['decoupling'].round(2)
    else:
        df_view['Desacoplamento (%)'] = None


    # Renderização na tela
    st.subheader("📊 Histórico de Telemetria")
    
    # Mostra o DataFrame formatado, escondendo a coluna de índice (0, 1, 2...)
    st.dataframe(df_view, hide_index=True, use_container_width=True)
    
    st.divider()

    # Métricas rápidas
    st.subheader("⚡ Resumo Global")
    col1, col2, col3 = st.columns(3)

    with col1:
        media_ef = df['efficiency_factor'].mean()
        st.metric(
            label="Fator de Eficiência Médio (EF)", 
            value=f"{media_ef:.2f}",
            help="**Mede a sua velocidade pelo custo cardíaco.**\n\nQuanto MAIOR o valor, mais rápido você corre gastando menos batimentos. Uma tendência de alta nas semanas indica ganho de condicionamento aeróbico."
        )
    with col2:
        if 'decoupling' in df.columns:
            media_dec = df['decoupling'].mean()
            st.metric(
                label="Desacoplamento Médio", 
                value=f"{media_dec:.2f}%",
                help="**Mede a perda de eficiência aeróbica.**\nO quanto o coração acelerou na 2ª metade do treino para manter o pace da 1ª metade.\n\n🟢 **< 5%:** Excelente base aeróbica.\n\n🟡 **5% a 8%:** Normal para treinos duros ou Fator Rio (Calor).\n\n🔴 **> 8%:** Alerta de fadiga, desidratação ou pace forte demais para o dia."
            )
            
    with col3:
        total_km = df_view['Distância (km)'].sum()
        st.metric(
            label="Volume Total (Amostra)", 
            value=f"{total_km:.2f} km",
            help="Soma da distância de todas as atividades processadas nesta visualização."
        )


else:
    st.warning("⚠️ Nenhum dado processado encontrado. Por favor, rode o pipeline primeiro: `python src/pipelines/data_processing.py`")