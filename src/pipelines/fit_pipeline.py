from src.ingestors.fit_loader import read_fit_file
from src.core.metrics import calculate_efficiency_factor, calculate_decoupling

def process_fit_file(file_path):
    """
        Processa um arquivo FIT, calculando as métricas avançadas.
        Retorna um dicionário com os resultados.
    """
    # Extract
    df_fit = read_fit_file(file_path)

    if df_fit is None or df_fit.empty:
        return None, None
    
    # Transform
    df_fit = df_fit.rename(columns={'heart_rate': 'heartrate', 'speed': 'velocity_smooth'})
    df_fit_clean = df_fit[(df_fit['heartrate'] > 40) & (df_fit['velocity_smooth'] > 1.0)]

    # Calcula métricas avançadas
    decoupling = calculate_decoupling(df_fit_clean)

    return df_fit_clean, decoupling
