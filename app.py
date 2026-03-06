import streamlit as st

# Importando os componentes modulares do Front-end
from src.frontend.sidebar import render_sidebar
from src.frontend.tab_fit import render_tab_fit
from src.frontend.tab_strava import render_tab_strava

# Configuração da Página 
st.set_page_config(page_title="RunDev Analytics", page_icon="🏃‍♀️", layout="wide")

# Renderiza a Barra Lateral e captura o treino selecionado pelo usuário
treino_selecionado = render_sidebar()

# Cabeçalho Principal
st.title("🏃‍♀️ RunDev Analytics")

# Estrutura de Abas
tab_fit, tab_strava = st.tabs([
    "🔬 Laboratório FIT (Análise Detalhada)", 
    "📊 Histórico Strava (Baseline)"
])

# Injeção dos Componentes nas Abas
with tab_fit:
    # Passamos a variável para a aba FIT saber o que mostrar
    render_tab_fit(treino_selecionado)

with tab_strava:
    render_tab_strava()