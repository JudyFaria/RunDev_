'''
    O Handshake OAuth 2.0. 
    O Strava não permite baixar dados apenas com uma "chave fixa"; 
    precisa-se de um fluxo onde o usuário autoriza o app a ler as atividades.
'''

# O Fluxo de Autenticação (OAuth 2.0)
#     - Authorization Code: Obtido via navegador (você clica em "Autorizar").
#     - Access Token: Usado para baixar seus treinos (expira rápido).
#     - Refresh Token: Usado para conseguir um novo Access Token sem precisar logar de novo.

import requests
import webbrowser
import json, os, time

import tokens

TOKEN_FILE = 'strava_tokens.json'

def save_tokens(tokens):
    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f)

def load_tokens():
    # Verifica se o arquivo existe E se não está vazio
    if os.path.exists(TOKEN_FILE) and os.path.getsize(TOKEN_FILE) > 0:
        with open(TOKEN_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return None
    return None

def refresh_access_token(refresh_token):
    '''
        Usa o Refresh Token para obter um novo Access Token  
    '''

    print("🔄 Refreshing access token...")
    token_url = "https://www.strava.com/oauth/token"
    payload = {
        'client_id': tokens.client_id,
        'client_secret': tokens.client_secret,
        'refresh_token': refresh_token['refresh_token'],
        'grant_type': 'refresh_token'
    }

    response = requests.post(token_url, data=payload)
    new_tokens = response.json()

    if 'access_token' in new_tokens:
        # Mantem o refresh_token antogo se não vier na resposta
        if 'refresh_token' not in new_tokens:
            new_tokens['refresh_token'] = save_tokens['refresh_token']
        save_tokens(new_tokens)
        
        print("✅ Access token refreshed!")
        return new_tokens
    else:
        print("❌ Failed to refresh token:", new_tokens)
        return None


# Main Logic

# tentar carregar tokens salvos
saved_tokens = load_tokens()

if not saved_tokens:
    # SE NÃO TEM TOKENS: Faz o fluxo que você já conhece (Navegador)
    print("Nenhum token encontrado. Abrindo navegador para autorização...")
    
    # gera URL de autorização e abre no navegador
    auth_url = (
        f"https://www.strava.com/oauth/authorize?client_id={tokens.client_id}"
        f"&response_type=code&redirect_uri=http://localhost/&scope=activity:read_all"
    )
    webbrowser.open(auth_url)
    authorization_code = input("Cole o código de autorização aqui: ")

    # trocar o código por um token de acesso
    token_url = "https://www.strava.com/oauth/token"

    payload = {
        'client_id': tokens.client_id,
        'client_secret': tokens.client_secret,
        'code': authorization_code,
        'grant_type': 'authorization_code'
    }

    response = requests.post(token_url, data=payload)
    saved_tokens = response.json()

    if 'access_token' in saved_tokens:
        save_tokens(saved_tokens)
        print("✅ Tokens salvos com sucesso!")
    else:
        print("❌ Erro na resposta do Strava:", saved_tokens)
        exit()

# Verifica expiração do token 
# O Strava envia 'expires_at' (timestamp em segundos)  
if time.time() > saved_tokens.get('expires_at', 0):
    print("⏰ Access token expirado. Tentando refresh...")
    saved_tokens = refresh_access_token(saved_tokens)

    if not saved_tokens:
        exit()

# Agora o access_token está garantido (seja novo ou renovado)
access_token = saved_tokens['access_token']

# Consumo da API
activities_url = "https://www.strava.com/api/v3/athlete/activities"
headers = {'Authorization': f"Bearer {access_token}"}
params = {'per_page': 5}

activities = requests.get(activities_url, headers=headers, params=params).json()

if isinstance(activities, list):
    print("Atividades: \n")

    for activity in activities:

        if activity['type'] != 'Run':
            continue
        
        dist_km = activity['distance'] / 1000
        print(f"ID: {activity['id']} | Nome: {activity['name']} | Distância: {dist_km:.2f} km")

else:
    print("❌ Erro ao obter atividades:", activities)   