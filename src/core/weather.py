import requests
import pandas as pd

def fetch_weather_and_timezone(lat, lon, start_timestamp_utc):
    """
    Busca o clima histórico e o fuso horário exato usando a API gratuita Open-Meteo.
    """
    if pd.isna(lat) or pd.isna(lon) or start_timestamp_utc is None:
        return None

    # Formata a data para a API (YYYY-MM-DD) e pega a hora inicial (0 a 23)
    data_treino = start_timestamp_utc.strftime('%Y-%m-%d')
    hora_treino = start_timestamp_utc.hour

    # URL da API do Open-Meteo (Historical Weather)
    url = f"https://archive-api.open-meteo.com/v1/archive"
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": data_treino,
        "end_date": data_treino,
        "hourly": "temperature_2m,relative_humidity_2m",
        "timezone": "auto" # A API descobre o fuso horário 
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        dados = response.json()

        # A API devolve um array de 24 horas. Pega o índice exato da hora em que o treino começou
        temp = dados['hourly']['temperature_2m'][hora_treino]
        umidade = dados['hourly']['relative_humidity_2m'][hora_treino]
        timezone_offset_seconds = dados['utc_offset_seconds'] # Diferença para o UTC em segundos

        return {
            "temperatura_celsius": temp,
            "umidade_percentual": umidade,
            "timezone_offset_hours": timezone_offset_seconds / 3600, # Converte segundos para horas (-3 para Brasil)
            "timezone_name": dados['timezone']
        }
        
    except Exception as e:
        print(f"⚠️ Erro ao buscar dados de clima: {e}")
        return None
    
'''
    Uma regra geral aceita (baseada em estudos de termorregulação no esporte) 
    é que a temperatura ideal para correr é em torno de 10°C a 15°C.

    Para cada 1°C acima de 15°C, o esforço cardíaco sobe em média entre 0.8% e 1.2%. 
    O mesmo vale para a umidade alta, que impede o suor de evaporar.
'''
def normalize_metrics_for_climate(ef_original, decoupling_original, temp_celsius, humidity_percent):
    """
    Normaliza o Fator de Eficiência e o Desacoplamento removendo o "ruído" do calor e umidade.
    Base de cálculo ideal: 15°C e 50% de umidade.
    """
    if ef_original is None or temp_celsius is None or humidity_percent is None:
        return ef_original, decoupling_original

    # Se estiver mais frio que o ideal, não penalizamos (o frio excessivo afeta outras coisas, mas vamos focar no calor)
    # TO-DO -> tratar isso também (excalabilidade)
    if temp_celsius <= 15 and humidity_percent <= 60:
        return ef_original, decoupling_original

    # Calcula o Fator de Estresse Climático
    
    # Exemplo: +1% de batimento a cada 1°C acima de 15°C
    temp_penalty = max(0, (temp_celsius - 15) * 0.01)
    
    # Exemplo: Umidade pune a evaporação. +0.5% a cada 10% acima de 60%
    humidity_penalty = max(0, ((humidity_percent - 60) / 10) * 0.005)
    
    total_penalty_factor = temp_penalty + humidity_penalty

    # Normaliza o EF 
    # -> Se estava quente, seu coração bateu mais rápido. O EF 'real' é maior
    ef_normalized = ef_original * (1 + total_penalty_factor)

    # Normaliza o Desacoplamento 
    # -> O calor infla o desacoplamento. O valor 'real' é menor
    if decoupling_original is not None:
        # Reduzimos o desacoplamento em uma fração baseada no calor extremo
        # Exemplo empírico: Se está 30 graus, o desacoplamento original de 8% pode na verdade ser um esforço muscular de 4%
        decoupling_normalized = decoupling_original - (decoupling_original * total_penalty_factor * 2)
    else:
        decoupling_normalized = None

    return round(ef_normalized, 2), (round(decoupling_normalized, 2) if decoupling_normalized else None)