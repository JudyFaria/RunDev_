import pandas as pd
import os

def format_pace(speed_ms):
    if pd.isna(speed_ms) or speed_ms == 0:
        return "0:00"
    pace_min_decimal = (1000 / speed_ms) / 60
    mins = int(pace_min_decimal)
    secs = int((pace_min_decimal - mins) * 60)
    return f"{mins}:{secs:02d}"

def get_strava_weekly_data(offset=0, caminho_dados='data/processed/atividades_processadas.csv'):
    """
    Atua como um endpoint de API. Recebe a semana desejada (offset) 
    e retorna os dados processados e prontos para o Front-end renderizar.
    """
    if not os.path.exists(caminho_dados):
        return None, None, None, None

    df_strava = pd.read_csv(caminho_dados)
    if 'start_date' in df_strava.columns:
        df_strava['start_date'] = pd.to_datetime(df_strava['start_date']).dt.tz_localize(None)

    # 1. Lógica de Datas
    hoje = pd.Timestamp.today().normalize()
    segunda_base = hoje - pd.Timedelta(days=hoje.weekday())
    data_inicio = segunda_base + pd.Timedelta(weeks=offset)
    data_fim = data_inicio + pd.Timedelta(days=6)

    # 2. Filtragem dos Dados Reais
    mask = (df_strava['start_date'].dt.date >= data_inicio.date()) & (df_strava['start_date'].dt.date <= data_fim.date())
    df_filtrado = df_strava[mask].copy()

    # 3. Construção do Esqueleto do Gráfico (7 dias)
    dias_pt = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sáb', 6: 'Dom'}
    datas_semana = [data_inicio + pd.Timedelta(days=i) for i in range(7)]
    
    df_esqueleto = pd.DataFrame({'Data Real': [d.date() for d in datas_semana]})
    df_esqueleto['Eixo_X'] = [f"{dias_pt[d.weekday()]}<br>{d.strftime('%d/%m')}" for d in datas_semana]

    if not df_filtrado.empty:
        df_filtrado['Data Real'] = df_filtrado['start_date'].dt.date
        df_agrupado = df_filtrado.groupby('Data Real')['distance'].sum().reset_index()
        df_agrupado['Distância (km)'] = (df_agrupado['distance'] / 1000).round(2)
        
        # Formata a tabela para o frontend
        df_filtrado = df_filtrado.sort_values(by='start_date', ascending=False).reset_index(drop=True)
        df_filtrado['Data Formatada'] = df_filtrado['start_date'].dt.strftime('%d/%m/%Y')
        df_filtrado['Pace Formatado'] = df_filtrado['average_speed'].apply(format_pace)
    else:
        df_agrupado = pd.DataFrame(columns=['Data Real', 'Distância (km)'])

    # Cruza o esqueleto com os dados
    df_grafico = pd.merge(df_esqueleto, df_agrupado, on='Data Real', how='left')
    df_grafico['Distância (km)'] = df_grafico['Distância (km)'].fillna(0)

    return df_filtrado, df_grafico, data_inicio, data_fim