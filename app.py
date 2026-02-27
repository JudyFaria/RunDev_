import streamlit as st
import pandas as pd
import os
import tempfile
import plotly.express as px
import json

from src.pipelines.fit_pipeline import process_fit_file
from src.core.metrics import calculate_decoupling, calculate_efficiency_factor
from src.core.segmentation import filter_telemetry_by_laps
from src.core.weather import normalize_metrics_for_climate
from src.storage.file_manager import save_fit_data, TELEMETRY_DIR, LAPS_DIR, METADATA_DIR

st.set_page_config(page_title="RunDev Analytics", page_icon="🏃‍♀️", layout="wide")

st.title("🏃‍♀️ RunDev Analytics")
st.markdown("Dashboard de telemetria e histórico de performance.")

def format_pace(speed_ms):
    if pd.isna(speed_ms) or speed_ms == 0:
        return "0:00"
    pace_min_decimal = (1000 / speed_ms) / 60
    mins = int(pace_min_decimal)
    secs = int((pace_min_decimal - mins) * 60)
    return f"{mins}:{secs:02d}"

# abas
tab_fit, tab_strava = st.tabs(
    [
        "🔬 Laboratório FIT (Análise Detalhada)", 
        "📊 Histórico Strava (Baseline)"
    ]
)

# ABA 1: LABORATÓRIO FIT
with tab_fit:
    st.header("Análise de Arquivos .FIT")
    
    # Dividindo a tela de controles em duas colunas
    col_upload, col_select = st.columns(2)
    
    with col_upload:
        st.subheader("1. Novo Upload")
        arquivo_fit_upload = st.file_uploader("Suba um novo arquivo .fit", type=["fit"])

        if arquivo_fit_upload is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".fit") as tmp_file:
                tmp_file.write(arquivo_fit_upload.read())
                temp_path = tmp_file.name

            with st.spinner("Processando e salvando dados..."):
                df_fit_clean, decoupling, efficiency, df_laps, weather_info = process_fit_file(temp_path)
                
                if df_fit_clean is not None:
                    activity_id = save_fit_data(temp_path, df_fit_clean, df_laps, weather_info)
                    st.success(f"Treino salvo! ID: {activity_id}")
                    
                    if weather_info:
                        st.info(
                            f"**Clima Local:** {weather_info['temperatura_celsius']}°C | "
                            f"**Umidade:** {weather_info['umidade_percentual']}% \n\n"
                            f"🌍 **Fuso Horário Aplicado:** {weather_info['timezone_name']}"
                        )

                    else:
                        st.warning("⚠️ Clima não detectado (GPS ausente ou falha na API). Fuso UTC-3 aplicado.")
            
            os.remove(temp_path)
            
    with col_select:
        st.subheader("2. Selecionar Treino Salvo")
        if os.path.exists(TELEMETRY_DIR):
            treinos_salvos = [f.replace('.csv', '') for f in os.listdir(TELEMETRY_DIR) if f.endswith('.csv')]
            treinos_salvos.sort(reverse=True)
            
            if treinos_salvos:
                treino_selecionado = st.selectbox("Escolha a atividade para gerar os gráficos:", treinos_salvos)
            else:
                treino_selecionado = None
                st.info("Nenhum treino salvo.")
        else:
            treino_selecionado = None
            st.info("Diretório de telemetria não encontrado.")

    st.divider()

    # --- RENDERIZAÇÃO DOS GRÁFICOS DO TREINO SELECIONADO ---
    if treino_selecionado:
        st.subheader(f"Visão Detalhada: {treino_selecionado}")
        
        # Carrega a telemetria segundo a segundo  
        df_telemetry = pd.read_csv(os.path.join(TELEMETRY_DIR, f"{treino_selecionado}.csv"))
        
        # tenta carregar as Laps geradas
        caminho_laps = os.path.join(LAPS_DIR, f"{treino_selecionado}.csv")
        df_laps = pd.read_csv(caminho_laps) if os.path.exists(caminho_laps) else None

        # 🔥 AQUI ESTÁ A LEITURA DO JSON DE CLIMA
        weather_info = None
        caminho_metadata = os.path.join(METADATA_DIR, f"{treino_selecionado}.json")
        if os.path.exists(caminho_metadata):
            with open(caminho_metadata, 'r', encoding='utf-8') as f:
                weather_info = json.load(f)

        # Exibe as informações de clima do treino salvo, se houver
        if weather_info:
            st.markdown(f"**Clima:** {weather_info['temperatura_celsius']}°C, Umidade: {weather_info['umidade_percentual']}%")

        # ==========================================
        # SELETOR DE LAPS E MÉTRICAS
        # ==========================================
        df_analise = df_telemetry.copy() # Por padrão, analisa o treino inteiro
        laps_selecionados = []
        
        if df_laps is not None and not df_laps.empty:
            laps_disponiveis = df_laps['lap_number'].tolist()
            
            laps_selecionados = st.multiselect(
                "🎯 Selecione os Trechos (Quilómetros) para isolar o cálculo das métricas:",
                options=laps_disponiveis,
                default=[],
                help="Se não selecionar nada, as métricas em baixo referem-se ao treino total. Selecione quilómetros específicos para ver o desempenho isolado."
            )
            
            # --- Filtro da telemetria baseado nos auto-laps
            if laps_selecionados:
                
                # O autolap grava o start_time e o timestamp de fim
                df_telemetry['timestamp'] = pd.to_datetime(df_telemetry['timestamp'])
                df_laps['start_time'] = pd.to_datetime(df_laps['start_time'])
                df_laps['timestamp'] = pd.to_datetime(df_laps['timestamp']) # Momento em que o lap termina
                 
                df_filtered = pd.DataFrame()
                for lap_num in laps_selecionados:
                    lap_info = df_laps[df_laps['lap_number'] == lap_num]
                    if not lap_info.empty:
                        start = lap_info['start_time'].iloc[0]
                        end = lap_info['timestamp'].iloc[0]
                        mask = (df_telemetry['timestamp'] >= start) & (df_telemetry['timestamp'] <= end)
                        df_filtered = pd.concat([df_filtered, df_telemetry[mask]])

                if not df_filtered.empty:
                    df_analise = df_filtered.sort_values(by='timestamp')
                    st.info(f"Métricas recalculadas exclusivamente para os quilómetros: {laps_selecionados}")

        else:
           st.info("Treino contínuo sem trechos gerados. Exibindo métricas totais.")
    
        # --- MÉTRICAS DO TRECHO (OU TOTAIS) ---
        decoupling_atual = calculate_decoupling(df_analise)
        efficiency_atual = calculate_efficiency_factor(df_analise)
        
        clima_temp = weather_info['temperatura_celsius'] if weather_info else None
        clima_humidity = weather_info['umidade_percentual'] if weather_info else None

        efficiency_normalized, decoupling_normalized = normalize_metrics_for_climate(efficiency_atual, decoupling_atual, clima_temp, clima_humidity)

        # calcula o delta (impacto do clima no treino)
        # Protegendo contra NoneTypes se as métricas originais não puderem ser calculadas
        if efficiency_normalized is not None and efficiency_atual is not None:
            efficiency_delta = efficiency_normalized - efficiency_atual 
        else:
            efficiency_delta = 0

        if decoupling_normalized is not None and decoupling_atual is not None:
            decoupling_delta = decoupling_normalized - decoupling_atual 
        else:
            decoupling_delta = 0

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            
            if decoupling_atual is not None and not df_analise.empty:
                st.metric(
                    label="Desacoplamento | Normalizado 15°C", 
                    value=f"{decoupling_normalized:.2f}%" if decoupling_normalized is not None else f"{decoupling_atual:.2f}%",
                    delta=f"Clima inflou {decoupling_delta:.2f}%" if clima_temp else "S/ Clima",
                    delta_color="inverse" # -> seta verde para baixo (queremos menos desacoplamento)
                )
            else:
                st.metric("Desacoplamento", "N/A")
                
        with col_m2:

            if efficiency_atual is not None and not df_analise.empty:
                st.metric(
                    label="Fator de Eficiência (EF) | Normalizado 15°C", 
                    value=f"{efficiency_normalized:.2f}" if efficiency_normalized is not None else f"{efficiency_atual:.2f}",
                    delta=f"Clima roubou {efficiency_delta:.2f}" if clima_temp else "S/ Clima",
                    delta_color="normal" # -> seta verde para cima
                )
            else:
                st.metric("Fator de Eficiência (EF)", "N/A")

        with col_m3:
            # Calcula a distância: soma as laps selecionadas ou pega a distância total do FIT
            if laps_selecionados and df_laps is not None:
                dist_trecho = df_laps[df_laps['lap_number'].isin(laps_selecionados)]['distance_km'].sum()
                st.metric("Distância (Trecho)", f"{dist_trecho:.2f} km")
            
            elif not df_telemetry.empty and 'distance' in df_telemetry.columns:
                dist_trecho = (df_telemetry['distance'].max() / 1000)
                st.metric("Distância Total", f"{dist_trecho:.2f} km")
            
            else:
                 st.metric("Distância", "0.00 km")
                
        with col_m4:
            if not df_analise.empty and 'heartrate' in df_analise.columns:
                fc_media = df_analise['heartrate'].mean()
                st.metric("FC Média", f"{fc_media:.0f} bpm")

        st.divider()

        # ==========================================
        # GRÁFICOS E TABELAS
        # ==========================================
        st.markdown("### 📈 Gráficos de Telemetria")
        col_graf_hr, col_graf_pace = st.columns(2)
        
        with col_graf_hr:
            if 'timestamp' in df_telemetry.columns and 'heartrate' in df_telemetry.columns:
                df_telemetry['timestamp'] = pd.to_datetime(df_telemetry['timestamp'])
                fig_hr = px.line(
                    df_telemetry, x='timestamp', y='heartrate', 
                    title="Frequência Cardíaca (BPM)",
                    labels={'heartrate': 'BPM', 'timestamp': 'Tempo'}
                )
                fig_hr.update_traces(line_color='#FF4B4B') 
                st.plotly_chart(fig_hr, use_container_width=True)

        with col_graf_pace:
            if 'velocity_smooth' in df_telemetry.columns:
                df_telemetry['speed_kmh'] = df_telemetry['velocity_smooth'] * 3.6
                fig_speed = px.line(
                    df_telemetry, x='timestamp', y='speed_kmh', 
                    title="Velocidade (km/h)",
                    labels={'speed_kmh': 'km/h', 'timestamp': 'Tempo'}
                )
                fig_speed.update_traces(line_color='#1f77b4')
                st.plotly_chart(fig_speed, use_container_width=True)

        # Parciais (Laps)
        if df_laps is not None and not df_laps.empty:
            st.markdown("### ⏱️ Tabela de Laps (Parciais)")
            df_laps_view = df_laps.rename(columns={
                'lap_number': 'Volta', 'distance_km': 'Dist. (km)', 
                'total_elapsed_time': 'Tempo (s)', 'pace_str': 'Pace', 
                'avg_heart_rate': 'FC Média', 'max_heart_rate': 'FC Máxima'
            })
            st.dataframe(df_laps_view, use_container_width=True, hide_index=True)



# ABA 2: HISTÓRICO STRAVA
with tab_strava:
    st.header("Histórico Consolidado (Strava)")
    caminho_dados = 'data/processed/atividades_processadas.csv'

    if os.path.exists(caminho_dados):
        df_strava = pd.read_csv(caminho_dados)

        df_view = pd.DataFrame()
        df_view['ID'] = df_strava['id'].astype(str)
        df_view['Treino'] = df_strava['name']
        df_view['Distância (km)'] = (df_strava['distance'] / 1000).round(2) 
        df_view['Duração (min)'] = (df_strava['moving_time'] / 60).round(2)
        df_view['Pace Médio'] = df_strava['average_speed'].apply(format_pace)
        df_view['FC Média (bpm)'] = df_strava['average_heartrate'].round(0).astype('Int64')
        df_view['EF'] = df_strava['efficiency_factor'].round(2)

        if 'decoupling' in df_strava.columns:
            df_view['Desacoplamento (%)'] = df_strava['decoupling'].round(2)
        else:
            df_view['Desacoplamento (%)'] = None

        # Métricas Globais do Strava
        col_strava_1, col_strava_2, col_strava_3 = st.columns(3)
        with col_strava_1:
            st.metric("Fator de Eficiência Médio (EF)", f"{df_strava['efficiency_factor'].mean():.2f}")
        with col_strava_2:
            if 'decoupling' in df_strava.columns:
                st.metric("Desacoplamento Médio", f"{df_strava['decoupling'].mean():.2f}%")
        with col_strava_3:
            st.metric("Volume Total (Amostra)", f"{df_view['Distância (km)'].sum():.2f} km")
        
        st.divider()
        st.dataframe(df_view, hide_index=True, use_container_width=True)
    else:
        st.info("Arquivo de histórico do Strava não encontrado em 'data/processed/atividades_processadas.csv'.")