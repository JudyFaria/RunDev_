from sqlalchemy import Column, Integer, String, Float, DateTime
from src.storage.database import Base, engine

class Treino(Base):
    __tablename__ = "treinos"

    id = Column(Integer, primary_key=True, index=True)
    strava_id = Column(String, unique=True, index=True) # Para não salvar o mesmo treino 2x
    nome = Column(String, nullable=False)
    data_treino = Column(DateTime, nullable=False)
    distancia_km = Column(Float, nullable=False)
    ritmo_medio = Column(String) # Ex: "04:50"
    tipo_treino = Column(String) # Ex: "VO2", "Limiar", "Rodagem" (IA vai preencher isso depois)

# Essa linha cria a tabela no arquivo rundev.db caso ela não exista ainda
Base.metadata.create_all(bind=engine)