import streamlit as st
from src.pipelines.data_processing import sync_strava_to_app
from src.backend.fit_service import get_available_activities, process_manual_upload

def render_sidebar():
    with st.sidebar:
        st.header("⚙️ Painel de Controle")
        
        # Sincronização
        if st.button("🔄 Sincronizar Strava", use_container_width=True, type="primary"):
            with st.spinner("Conectando aos satélites do Strava..."):
                novos = sync_strava_to_app()
                if novos > 0:
                    st.success(f"{novos} novo(s) treino(s) puxado(s) com sucesso!")
                    st.rerun()
                else:
                    st.info("O seu Laboratório já está 100% atualizado.")
        
        st.divider()
        
        # Seletor
        st.subheader("Analisar Treino")
        treinos_salvos = get_available_activities()
        treino_selecionado = None
        if treinos_salvos:
            treino_selecionado = st.selectbox("Selecione a atividade:", treinos_salvos)
        else:
            st.info("Nenhum treino salvo. Sincronize com o Strava.")
            
        st.divider()

        # Upload Manual
        with st.expander("🛠️ Opções Avançadas: Upload Manual (.FIT)"):
            st.markdown("Use esta opção para análises de alta fidelidade.")
            arquivo_fit_upload = st.file_uploader("Suba o arquivo bruto", type=["fit"])

            if arquivo_fit_upload is not None:
                with st.spinner("Processando e salvando..."):
                    activity_id = process_manual_upload(arquivo_fit_upload.read())
                    if activity_id:
                        st.success(f"Salvo! ID: {activity_id}")
                        st.rerun()
                    else:
                        st.error("Erro ao processar o arquivo.")
                        
        return treino_selecionado # Retorna a escolha para o app.py