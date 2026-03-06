import streamlit as st
import pandas as pd
import plotly.express as px
from src.backend.strava_service import get_strava_weekly_data

def render_tab_strava():
    st.header("Histórico Consolidado (Strava)")
    
    if 'semana_offset' not in st.session_state:
        st.session_state.semana_offset = 0

    df_filtrado, df_grafico, data_inicio, data_fim = get_strava_weekly_data(st.session_state.semana_offset)

    if df_filtrado is None:
        st.info("Arquivo de histórico não encontrado. Clique em Sincronizar na barra lateral.")
        return

    st.markdown("### 📈 Evolução do Volume Semanal")
    fig_vol = px.bar(df_grafico, x='Eixo_X', y='Distância (km)', text='Distância (km)', color_discrete_sequence=['#FC4C02'])
    fig_vol.update_traces(textposition='outside', textfont_size=14, texttemplate='%{text:.2f}', cliponaxis=False)
    fig_vol.for_each_trace(lambda t: t.update(text=[str(v) if v > 0 else "" for v in t.y]))
    fig_vol.update_layout(xaxis_title="", yaxis_title="Volume Diário (km)", xaxis={'type': 'category'}, plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=10, l=10, r=10, b=10), height=320)
    st.plotly_chart(fig_vol, use_container_width=True)

    col_esq, col_meio, col_dir = st.columns([1, 4, 1])
    with col_esq:
        if st.button("⬅️ Anterior", use_container_width=True):
            st.session_state.semana_offset -= 1
            st.rerun()
    with col_meio:
        label_data = f"{data_inicio.strftime('%d/%m')} a {data_fim.strftime('%d/%m/%Y')}"
        st.markdown(f"<h4 style='text-align: center; color: #666; margin-top: 5px;'>Semana: {label_data}</h4>", unsafe_allow_html=True)
    with col_dir:
        if st.session_state.semana_offset < 0:
            if st.button("Próximo ➡️", use_container_width=True):
                st.session_state.semana_offset += 1
                st.rerun()
        else:
            st.button("Atual 🎯", disabled=True, use_container_width=True)
            
    st.divider()

    if not df_filtrado.empty:
        df_view = pd.DataFrame({
            'Data': df_filtrado['Data Formatada'], 'Treino': df_filtrado['name'],
            'Distância (km)': (df_filtrado['distance'] / 1000).round(2),
            'Duração (min)': (df_filtrado['moving_time'] / 60).round(2), 'Pace Médio': df_filtrado['Pace Formatado'],
            'FC Média (bpm)': df_filtrado['average_heartrate'].round(0).astype('Int64'),
            'EF': df_filtrado['efficiency_factor'].round(2),
            'Desacoplamento (%)': df_filtrado['decoupling'].round(2) if 'decoupling' in df_filtrado.columns else None
        })
        col_1, col_2, col_3 = st.columns(3)
        with col_1: st.metric("EF Médio", f"{df_filtrado['efficiency_factor'].mean():.2f}")
        with col_2: st.metric("Desacoplamento", f"{df_filtrado['decoupling'].mean():.2f}%" if 'decoupling' in df_filtrado.columns else "N/A")
        with col_3: st.metric("Volume Semanal", f"{df_view['Distância (km)'].sum():.2f} km")
        st.dataframe(df_view, hide_index=True, use_container_width=True)
    else:
        st.info("Você não registrou nenhum treino nesta semana.")