import streamlit as st
import pandas as pd
import os
import tempfile
import plotly.express as px
import json

from src.pipelines.data_processing import sync_strava_to_app
from src.pipelines.fit_pipeline import process_fit_file # <-- Adicionado para o upload manual funcionar
from src.core.metrics import calculate_decoupling, calculate_efficiency_factor
from src.core.segmentation import filter_telemetry_by_laps
from src.core.weather import normalize_metrics_for_climate
from src.storage.file_manager import save_fit_data, TELEMETRY_DIR, LAPS_DIR, METADATA_DIR

st.set_page_config(page_title="RunDev Analytics", page_icon="🏃‍♀️", layout="wide")

def format_pace(speed_ms):
    if pd.isna(speed_ms) or speed_ms == 0:
        return "0:00"
    pace_min_decimal = (1000 / speed_ms) / 60
    mins = int(pace_min_decimal)
    secs = int((pace_min_decimal - mins) * 60)
    return f"{mins}:{secs:02d}"

# ==========================================
# SIDEBAR (BARRA LATERAL DE CONTROLES)
# ==========================================
with st.sidebar:
    st.header("⚙️ Painel de Controle")
    
    # 1. Botão de Sincronização Principal
    if st.button("🔄 Sincronizar Strava", use_container_width=True, type="primary"):
        with st.spinner("Conectando aos satélites do Strava..."):
            novos = sync_strava_to_app()
            if novos > 0:
                st.success(f"{novos} novo(s) treino(s) puxado(s) com sucesso!")
                st.rerun() # Recarrega a página para exibir os novos dados instantaneamente
            else:
                st.info("O seu Laboratório já está 100% atualizado.")
    
    st.divider()
    
    # 2. Seletor de Treinos
    st.subheader("Analisar Treino")
    treino_selecionado = None
    if os.path.exists(TELEMETRY_DIR):
        treinos_salvos = [f.replace('.csv', '') for f in os.listdir(TELEMETRY_DIR) if f.endswith('.csv')]
        treinos_salvos.sort(reverse=True)
        
        if treinos_salvos:
            treino_selecionado = st.selectbox("Selecione a atividade:", treinos_salvos)
        else:
            st.info("Nenhum treino salvo. Sincronize com o Strava.")
    else:
        st.info("Diretório de telemetria não encontrado.")
        
    st.divider()

    # 3. Upload Manual (Escondido num Expander para manter o layout limpo)
    with st.expander("🛠️ Opções Avançadas: Upload Manual (.FIT)"):
        st.markdown("Use esta opção para análises de alta fidelidade ou se a API do Strava falhar.")
        arquivo_fit_upload = st.file_uploader("Suba o arquivo bruto", type=["fit"])

        if arquivo_fit_upload is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".fit") as tmp_file:
                tmp_file.write(arquivo_fit_upload.read())
                temp_path = tmp_file.name

            with st.spinner("Processando..."):
                df_fit_clean, decoupling, efficiency, df_laps, weather_info = process_fit_file(temp_path)
                
                if df_fit_clean is not None:
                    activity_id = save_fit_data(temp_path, df_fit_clean, df_laps, weather_info)
                    st.success(f"Salvo! ID: {activity_id}")
            os.remove(temp_path)
            st.rerun() # Atualiza a barra lateral para mostrar o treino que acabou de subir


# ==========================================
# ÁREA PRINCIPAL
# ==========================================
st.title("🏃‍♀️ RunDev Analytics")
st.markdown("Bem-vinda ao seu centro de comando de alta performance.")

# Criação das Abas
tab_fit, tab_strava = st.tabs([
    "🔬 Laboratório FIT (Análise Detalhada)", 
    "📊 Histórico Strava (Baseline)"
])

# --- ABA 1: LABORATÓRIO FIT ---
with tab_fit:
    if treino_selecionado:
        st.subheader(f"Visão Detalhada: {treino_selecionado}")
        
        # Carrega dados
        df_telemetry = pd.read_csv(os.path.join(TELEMETRY_DIR, f"{treino_selecionado}.csv"))
        caminho_laps = os.path.join(LAPS_DIR, f"{treino_selecionado}.csv")
        df_laps = pd.read_csv(caminho_laps) if os.path.exists(caminho_laps) else None

        # Carrega o Clima
        weather_info = None
        caminho_metadata = os.path.join(METADATA_DIR, f"{treino_selecionado}.json")
        if os.path.exists(caminho_metadata):
            with open(caminho_metadata, 'r', encoding='utf-8') as f:
                weather_info = json.load(f)

        if weather_info:
            st.info(f"🌦️ **Clima:** {weather_info['temperatura_celsius']}°C | **Umidade:** {weather_info['umidade_percentual']}% | **Fuso:** {weather_info['timezone_name']}")

        # Seletor de Laps
        df_analise = df_telemetry.copy()
        laps_selecionados = []
        
        if df_laps is not None and not df_laps.empty:
            laps_disponiveis = df_laps['lap_number'].tolist()
            laps_selecionados = st.multiselect(
                "🎯 Selecione os Trechos (Quilómetros) para isolar o cálculo:",
                options=laps_disponiveis,
                default=[],
                help="Deixe vazio para ver o treino total."
            )
            
            if laps_selecionados:
                df_telemetry['timestamp'] = pd.to_datetime(df_telemetry['timestamp'])
                df_laps['start_time'] = pd.to_datetime(df_laps['start_time'])
                df_laps['timestamp'] = pd.to_datetime(df_laps['timestamp'])
                 
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
                    st.success(f"Métricas recalculadas para os quilómetros: {laps_selecionados}")

        # Métricas
        decoupling_atual = calculate_decoupling(df_analise)
        efficiency_atual = calculate_efficiency_factor(df_analise)
        
        clima_temp = weather_info['temperatura_celsius'] if weather_info else None
        clima_humidity = weather_info['umidade_percentual'] if weather_info else None

        efficiency_normalized, decoupling_normalized = normalize_metrics_for_climate(efficiency_atual, decoupling_atual, clima_temp, clima_humidity)

        efficiency_delta = (efficiency_normalized - efficiency_atual) if (efficiency_normalized is not None and efficiency_atual is not None) else 0
        decoupling_delta = (decoupling_normalized - decoupling_atual) if (decoupling_normalized is not None and decoupling_atual is not None) else 0

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            if decoupling_atual is not None and not df_analise.empty:
                st.metric(
                    label="Desacoplamento (Norm. 15°C)", 
                    value=f"{decoupling_normalized:.2f}%" if decoupling_normalized is not None else f"{decoupling_atual:.2f}%",
                    delta=f"Clima inflou {decoupling_delta:.2f}%" if clima_temp else "S/ Clima",
                    delta_color="inverse"
                )
            else:
                st.metric("Desacoplamento", "N/A")
                
        with col_m2:
            if efficiency_atual is not None and not df_analise.empty:
                st.metric(
                    label="EF (Norm. 15°C)", 
                    value=f"{efficiency_normalized:.2f}" if efficiency_normalized is not None else f"{efficiency_atual:.2f}",
                    delta=f"Clima roubou {efficiency_delta:.2f}" if clima_temp else "S/ Clima",
                    delta_color="normal"
                )
            else:
                st.metric("Fator de Eficiência (EF)", "N/A")

        with col_m3:
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

        # Gráficos
        st.markdown("### 📈 Gráficos de Telemetria")
        col_graf_hr, col_graf_pace = st.columns(2)
        
        with col_graf_hr:
            if 'timestamp' in df_telemetry.columns and 'heartrate' in df_telemetry.columns:
                df_telemetry['timestamp'] = pd.to_datetime(df_telemetry['timestamp'])
                fig_hr = px.line(df_telemetry, x='timestamp', y='heartrate', title="Frequência Cardíaca (BPM)")
                fig_hr.update_traces(line_color='#FF4B4B') 
                st.plotly_chart(fig_hr, use_container_width=True)

        with col_graf_pace:
            if 'velocity_smooth' in df_telemetry.columns:
                df_telemetry['speed_kmh'] = df_telemetry['velocity_smooth'] * 3.6
                fig_speed = px.line(df_telemetry, x='timestamp', y='speed_kmh', title="Velocidade (km/h)")
                fig_speed.update_traces(line_color='#1f77b4')
                st.plotly_chart(fig_speed, use_container_width=True)

        # Tabela Laps
        if df_laps is not None and not df_laps.empty:
            st.markdown("### ⏱️ Parciais Automáticas (Laps)")
            df_laps_view = df_laps.rename(columns={
                'lap_number': 'Volta', 'distance_km': 'Dist. (km)', 
                'total_elapsed_time': 'Tempo (s)', 'pace_str': 'Pace', 
                'avg_heart_rate': 'FC Média', 'max_heart_rate': 'FC Máxima'
            })
            st.dataframe(df_laps_view, use_container_width=True, hide_index=True)
    else:
        st.info("👈 Selecione um treino na barra lateral para iniciar a análise.")

# --- ABA 2: HISTÓRICO STRAVA ---
with tab_strava:
    st.header("Histórico Consolidado (Strava)")
    caminho_dados = 'data/processed/atividades_processadas.csv'

    if os.path.exists(caminho_dados):
        df_strava = pd.read_csv(caminho_dados)
        
        if 'start_date' in df_strava.columns:
            df_strava['start_date'] = pd.to_datetime(df_strava['start_date']).dt.tz_localize(None)
            
        # ESTADO DA PAGINAÇÃO SEMANAL
        if 'semana_offset' not in st.session_state:
            st.session_state.semana_offset = 0 # 0 = Semana Atual

        # Cálculo das datas da semana selecionada (Segunda a Domingo)
        hoje = pd.Timestamp.today().normalize()
        segunda_base = hoje - pd.Timedelta(days=hoje.weekday())
        
        data_inicio = segunda_base + pd.Timedelta(weeks=st.session_state.semana_offset)
        data_fim = data_inicio + pd.Timedelta(days=6)
        
        # Filtra os dados reais do Strava para a semana selecionada
        mask = (df_strava['start_date'].dt.date >= data_inicio.date()) & (df_strava['start_date'].dt.date <= data_fim.date())
        df_filtrado = df_strava[mask].copy()


        #------- semanal ---------
        # ENGENHARIA DO GRÁFICO (7 DIAS FIXOS)
        st.markdown("### 📈 Evolução do Volume Semanal")
        
        # Cria o "Esqueleto" da semana com os 7 dias
        dias_pt = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sáb', 6: 'Dom'}
        datas_semana = [data_inicio + pd.Timedelta(days=i) for i in range(7)]
        
        df_esqueleto = pd.DataFrame({'Data Real': [d.date() for d in datas_semana]})
        df_esqueleto['Eixo_X'] = [f"{dias_pt[d.weekday()]}<br>{d.strftime('%d/%m')}" for d in datas_semana]
        
        # Agrupa os treinos do Strava por dia (caso você corra 2x no mesmo dia)
        if not df_filtrado.empty:
            df_filtrado['Data Real'] = df_filtrado['start_date'].dt.date
            df_agrupado = df_filtrado.groupby('Data Real')['distance'].sum().reset_index()
            df_agrupado['Distância (km)'] = (df_agrupado['distance'] / 1000).round(2)
        else:
            df_agrupado = pd.DataFrame(columns=['Data Real', 'Distância (km)'])
            
        # Cruza o Esqueleto com os Dados Reais (Preenche com 0 onde não tem treino)
        df_grafico = pd.merge(df_esqueleto, df_agrupado, on='Data Real', how='left')
        df_grafico['Distância (km)'] = df_grafico['Distância (km)'].fillna(0)

        # Renderiza o Gráfico
        fig_vol = px.bar(
            df_grafico, 
            x='Eixo_X', 
            y='Distância (km)',
            text='Distância (km)',
            color_discrete_sequence=['#FC4C02'] 
        )
        
        # Formatação - Oculta o texto "0" nas barras vazias para ficar limpo
        fig_vol.update_traces(
            textposition='outside',
            textfont_size=14,
            texttemplate='%{text:.2f}',
            cliponaxis=False
        )
        # Esconde o label "0.00" nos dias de descanso
        fig_vol.for_each_trace(lambda t: t.update(text=[str(v) if v > 0 else "" for v in t.y]))
        
        fig_vol.update_layout(
            xaxis_title="",
            yaxis_title="Volume Diário (km)",
            xaxis={'type': 'category'}, # Trava os 7 espaços independentemente do volume
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(t=10, l=10, r=10, b=10),
            height=320
        )
        
        st.plotly_chart(fig_vol, use_container_width=True)

        # BOTÕES DE NAVEGAÇÃO (Abaixo do Gráfico)
        col_esq, col_meio, col_dir = st.columns([1, 4, 1])
        
        with col_esq:
            if st.button("⬅️ Anterior", use_container_width=True):
                st.session_state.semana_offset -= 1
                st.rerun()
                
        with col_meio:
            label_data = f"{data_inicio.strftime('%d/%m')} a {data_fim.strftime('%d/%m/%Y')}"
            st.markdown(f"<h4 style='text-align: center; color: #666; margin-top: 5px;'>Semana: {label_data}</h4>", unsafe_allow_html=True)
            
        with col_dir:
            # O botão de "Próximo" ou "Voltar a Hoje"
            if st.session_state.semana_offset < 0:
                if st.button("Próximo ➡️", use_container_width=True):
                    st.session_state.semana_offset += 1
                    st.rerun()
            else:
                st.button("Atual 🎯", disabled=True, use_container_width=True)

        st.divider()

        # MÉTRICAS GLOBAIS DA SEMANA E TABELA
        if not df_filtrado.empty:
            df_filtrado = df_filtrado.sort_values(by='start_date', ascending=False).reset_index(drop=True)
            
            df_view = pd.DataFrame()
            if 'start_date' in df_filtrado.columns:
                df_view['Data'] = df_filtrado['start_date'].dt.strftime('%d/%m/%Y')
                
            df_view['Treino'] = df_filtrado['name']
            df_view['Distância (km)'] = (df_filtrado['distance'] / 1000).round(2) 
            df_view['Duração (min)'] = (df_filtrado['moving_time'] / 60).round(2)
            df_view['Pace Médio'] = df_filtrado['average_speed'].apply(format_pace)
            df_view['FC Média (bpm)'] = df_filtrado['average_heartrate'].round(0).astype('Int64')
            df_view['EF'] = df_filtrado['efficiency_factor'].round(2)

            col_strava_1, col_strava_2, col_strava_3 = st.columns(3)
            with col_strava_1:
                ef_medio = df_filtrado['efficiency_factor'].mean()
                st.metric("Fator de Eficiência (EF)", f"{ef_medio:.2f}" if not pd.isna(ef_medio) else "N/A")
            with col_strava_2:
                if 'decoupling' in df_filtrado.columns:
                    dec_medio = df_filtrado['decoupling'].mean()
                    st.metric("Desacoplamento Médio", f"{dec_medio:.2f}%" if not pd.isna(dec_medio) else "N/A")
                else:
                    st.metric("Desacoplamento Médio", "N/A")
            with col_strava_3:
                st.metric("Volume da Semana", f"{df_view['Distância (km)'].sum():.2f} km")
            
            st.dataframe(df_view, hide_index=True, use_container_width=True)
        else:
            st.info("Você não registrou nenhum treino nesta semana.")
    else:
        st.info("Arquivo de histórico do Strava não encontrado. Clique em Sincronizar na barra lateral.")