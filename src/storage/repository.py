from sqlalchemy.orm import Session
from src.storage.db_models import Treino
from datetime import datetime

def salvar_treino(db: Session, strava_data: dict):
    
    # Verifica se o treino já existe no banco para não duplicar
    treino_existente = db.query(Treino).filter(Treino.strava_id == str(strava_data['id'])).first()
    
    if treino_existente:
        print(f"Treino {strava_data['name']} já existe no banco. Pulando...")
        return treino_existente

    # converte de String do Strava para Objeto Datetime do Python
    data_str = strava_data['start_date']
    # O Strava manda "2026-03-12T09:20:25Z", o strptime traduz isso:
    data_obj = datetime.strptime(data_str, "%Y-%m-%dT%H:%M:%SZ")

    # Cria um novo objeto Treino com os dados do Strava
    novo_treino = Treino(
        strava_id=str(strava_data['id']),
        nome=strava_data['name'],
        data_treino=data_obj,
        distancia_km=strava_data['distance'] / 1000.0, # Strava manda em metros, o banco guarda em km
        ritmo_medio="00:00", # Deixando zerado por enquanto, calcularemos depois
        tipo_treino="A Classificar" # A sua inteligência vai preencher isso no futuro!
    )

    # Adiciona e salva no banco
    db.add(novo_treino)
    db.commit()
    db.refresh(novo_treino)
    
    print(f"Treino {novo_treino.nome} salvo com sucesso no banco!")
    return novo_treino