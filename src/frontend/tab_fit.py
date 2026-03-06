import streamlit as st
import pandas as pd
import plotly.express as px
from src.backend.fit_service import get_activity_analysis

def render_tab_fit(treino_selecionado):
    if not treino_selecionado:
        st.info("👈 Selecione um treino na barra lateral para iniciar a análise.")
        return

    st.subheader(f"Visão Detalhada: {treino_selecionado}")
    
    dados_iniciais = get_activity_analysis(treino_selecionado, laps_selecionados=[])
    df_laps = dados_iniciais["df_laps"]
    
    if dados_iniciais["weather_info"]:
        w = dados_iniciais["weather_info"]
        st.info(f"🌦️ **Clima:** {w['temperatura_celsius']}°C | **Umidade:** {w['umidade_percentual']}% | **Fuso:** {w['timezone_name']}")

    laps_selecionados = []
    if not df_laps.empty:
        laps_disponiveis = df_laps['lap_number'].tolist()
        laps_selecionados = st.multiselect(
            "🎯 Selecione os Trechos (Quilómetros) para isolar o cálculo:",
            options=laps_disponiveis, default=[], help="Deixe vazio para ver o treino total."
        )
        if laps_selecionados:
            st.success(f"Métricas recalculadas para os quilómetros: {laps_selecionados}")

    dados_analise = get_activity_analysis(treino_selecionado, laps_selecionados)
    m = dados_analise["metrics"]

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        if m["decoupling_atual"] is not None:
            valor_exibicao = f"{m['decoupling_normalized']:.2f}%" if m['decoupling_normalized'] is not None else f"{m['decoupling_atual']:.2f}%"
            delta_texto = f"Clima inflou {m['decoupling_delta']:.2f}%" if m['clima_temp'] else "S/ Clima"
            st.metric("Desacoplamento (Norm. 15°C)", valor_exibicao, delta=delta_texto, delta_color="inverse")
        else:
            st.metric("Desacoplamento", "N/A")
            
    with col_m2:
        if m["efficiency_atual"] is not None:
            valor_exibicao = f"{m['efficiency_normalized']:.2f}" if m['efficiency_normalized'] is not None else f"{m['efficiency_atual']:.2f}"
            delta_texto = f"Clima roubou {m['efficiency_delta']:.2f}" if m['clima_temp'] else "S/ Clima"
            st.metric("EF (Norm. 15°C)", valor_exibicao, delta=delta_texto, delta_color="normal")
        else:
            st.metric("Fator de Eficiência (EF)", "N/A")

    with col_m3:
        st.metric("Distância (Análise)", f"{m['dist_trecho']:.2f} km")
            
    with col_m4:
        st.metric("FC Média", f"{m['fc_media']:.0f} bpm")

    st.divider()

    st.markdown("### 📈 Gráficos de Telemetria")
    col_graf_hr, col_graf_pace = st.columns(2)
    
    with col_graf_hr:
        if not dados_analise["df_telemetry"].empty and 'heartrate' in dados_analise["df_telemetry"].columns:
            df_hr = dados_analise["df_telemetry"].copy()
            df_hr['timestamp'] = pd.to_datetime(df_hr['timestamp'])
            fig_hr = px.line(df_hr, x='timestamp', y='heartrate', title="Frequência Cardíaca (BPM)")
            fig_hr.update_traces(line_color='#FF4B4B') 
            st.plotly_chart(fig_hr, use_container_width=True)

    with col_graf_pace:
        if not dados_analise["df_telemetry"].empty and 'velocity_smooth' in dados_analise["df_telemetry"].columns:
            df_speed = dados_analise["df_telemetry"].copy()
            df_speed['timestamp'] = pd.to_datetime(df_speed['timestamp'])
            df_speed['speed_kmh'] = df_speed['velocity_smooth'] * 3.6
            fig_speed = px.line(df_speed, x='timestamp', y='speed_kmh', title="Velocidade (km/h)")
            fig_speed.update_traces(line_color='#1f77b4')
            st.plotly_chart(fig_speed, use_container_width=True)

    if not df_laps.empty:
        st.markdown("### ⏱️ Parciais Automáticas (Laps)")
        df_laps_view = df_laps.rename(columns={
            'lap_number': 'Volta', 'distance_km': 'Dist. (km)', 
            'total_elapsed_time': 'Tempo (s)', 'pace_str': 'Pace', 
            'avg_heart_rate': 'FC Média', 'max_heart_rate': 'FC Máxima'
        })
        st.dataframe(df_laps_view, use_container_width=True, hide_index=True)