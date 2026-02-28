import requests
import webbrowser
import json, os, time

import streamlit as st
# puxa as credenciais com segurança do cofre do streamlit
CLIENT_ID = st.secrets["client_id"]
CLIENT_SECRET = st.secrets["client_secret"]
ACCESS_TOKEN = st.secrets["access_token"]
UPDATE_TOKEN = st.secrets["update_tokens"]

TOKEN_FILE = 'strava_tokens.json'

def save_tokens(token_data):
    with open(TOKEN_FILE, 'w') as f:
        json.dump(token_data, f)

def load_tokens():
    if os.path.exists(TOKEN_FILE) and os.path.getsize(TOKEN_FILE) > 0:
        with open(TOKEN_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return None
    return None

def refresh_access_token(saved_tokens):
    """
        Usa o Refresh Token para obter um novo Access Token
    """
    print("🔄 Refreshing access token...")
    token_url = "https://www.strava.com/oauth/token"
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': saved_tokens['refresh_token'],
        'grant_type': 'refresh_token'
    }

    try:
        response = requests.post(token_url, data=payload)
        response.raise_for_status()
        new_tokens = response.json()

        # Mantem o refresh_token antigo se não vier na resposta
        if 'refresh_token' not in new_tokens:
            new_tokens['refresh_token'] = saved_tokens['refresh_token']
            
        save_tokens(new_tokens)
        print("✅ Access token refreshed!")
        return new_tokens
        
    except Exception as e:
        print(f"❌ Failed to refresh token: {e}")
        return None

def get_valid_access_token():
    """
        Verifica se o token existe e é válido. Se não, renova. 
        Se não existir de todo, faz o fluxo do navegador.
        Retorna a string do access_token válido.
    """
    saved_tokens = load_tokens()

    if not saved_tokens:
        print("Nenhum token encontrado. Abrindo navegador para autorização...")
        auth_url = (
            f"https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}"
            f"&response_type=code&redirect_uri=http://localhost/&scope=activity:read_all"
        )
        webbrowser.open(auth_url)
        authorization_code = input("Cole o código de autorização aqui: ")

        token_url = "https://www.strava.com/oauth/token"
        payload = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'code': authorization_code,
            'grant_type': 'authorization_code'
        }

        response = requests.post(token_url, data=payload)
        saved_tokens = response.json()

        if 'access_token' in saved_tokens:
            save_tokens(saved_tokens)
            print("✅ Tokens salvos com sucesso!")
        else:
            raise Exception(f"❌ Erro na resposta do Strava: {saved_tokens}")

    # Verifica expiração
    if time.time() > saved_tokens.get('expires_at', 0):
        print("⏰ Access token expirado. Tentando refresh...")
        saved_tokens = refresh_access_token(saved_tokens)
        if not saved_tokens:
            raise Exception("Falha ao renovar o token.")

    return saved_tokens['access_token']


def get_recent_activities(limit=5):
    """
        Obtém o resumo das últimas atividades (apenas corridas).
    """
    access_token = get_valid_access_token()
    activities_url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {'Authorization': f"Bearer {access_token}"}
    params = {'per_page': limit}

    try:
        response = requests.get(activities_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Filtra apenas por corridas
        runs = [act for act in data if act.get('type') == 'Run']
        return runs
    
    except Exception as e:
        print(f"❌ Erro ao obter atividades: {e}")
        return []
    

def get_activity_streams(activity_id):
    """
        Baixa os dados telemétricos de uma atividade.
    """
    access_token = get_valid_access_token()
    url = f"https://www.strava.com/api/v3/activities/{activity_id}/streams"
    params = {'keys': 'time,heartrate,velocity_smooth', 'key_by_type': 'true'}
    headers = {'Authorization': f"Bearer {access_token}"}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        if 'message' in data:
            return None
        return data
    except Exception as e:
        print(f"Erro ao baixar streams da atividade {activity_id}: {e}")
        return None
