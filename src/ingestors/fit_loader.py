import pandas as pd
from fitparse import FitFile

def read_fit_file(file_path):
    """
        Lê um arquivo .fit bruto do relógio e extrai a telemetria segundo a segundo.
    """
    print(f"⏱️ Lendo arquivo FIT: {file_path}...")
    try:
        # Abre o arquivo binário do relógio
        fitfile = FitFile(file_path)
    
    except Exception as e:
        print(f"❌ Erro ao ler o arquivo FIT: {e}")
        return None
    
    registros = []

    # O relógio grava os dados segundo a segundo nas mensagens do tipo 'record'
    for record in fitfile.get_messages('record'):
        registro = {}
        
        for data in record:
            # Pegamos apenas as métricas que importam para o RunDev
            if data.name in ['timestamp', 'heart_rate', 'speed', 'distance']:
                registro[data.name] = data.value

        # Só adiciona se tiver timestamp (ou seja, for um registro válido) e batimento
        if 'timestamp' in registro and 'heart_rate' in registro:
            registros.append(registro)

    # Transforma a lista de dados brutos num DataFrame
    df = pd.DataFrame(registros)

    if df.empty:
        print("⚠️ Nenhum registro válido encontrado no arquivo FIT.")
        return None
    
    print(f"✅ Arquivo FIT processado com sucesso! {len(df)} registros extraídos.")
    return df