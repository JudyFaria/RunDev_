import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Cria uma pasta "data" na raiz do projeto (se não existir) para guardar o banco
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "rundev.db")

# Cria a URL de conexão do SQLite
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# O 'engine' é o motor que executa os comandos SQL
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# A Sessão é o que usaremos para salvar e buscar dados
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# O Base é a classe mãe que todas as nossas tabelas vão herdar
Base = declarative_base()

# Função auxiliar para pegar a sessão do banco quando precisarmos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()