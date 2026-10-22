import os
import logging
from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# -- 1. Configuración Logging --
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# -- 2. Configuración Base de Datos --
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg2://user:password@db:5432/mydb")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class EstudianteDB(Base):
    __tablename__ = "estudiantes"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    email = Column(String, nullable=False)
    edad = Column(Integer, nullable=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando aplicación y conectando a PostgreSQL...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tablas verificadas/creadas con éxito.")
    yield
    logger.info("Apagando la aplicación...")

app = FastAPI(title="CRUD API Estudiantes", version="1.0.0", lifespan=lifespan)

# Dependencia para inyectar la conexión de la BD en cada endpoint
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -- 3. Modelos Pydantic --
class EstudianteCreate(BaseModel):
    nombre: str
    email: str
    edad: int  # Si envías un string aquí, FastAPI devuelve 422 automáticamente

class EstudianteResponse(BaseModel):
    id: int
    nombre: str
    email: str
    edad: int
    class Config:
        from_attributes = True

# -- 4. Endpoints --
@app.get("/estudiantes", response_model=List[EstudianteResponse])
def listar_estudiantes(db: Session = Depends(get_db)):
    logger.info("GET /estudiantes - Listando todos los estudiantes")
    return db.query(EstudianteDB).all()

@app.get("/estudiantes/{estudiante_id}", response_model=EstudianteResponse)
def obtener_estudiante(estudiante_id: int, db: Session = Depends(get_db)):
    logger.info(f"GET /estudiantes/{estudiante_id} - Buscando estudiante")
    estudiante = db.query(EstudianteDB).filter(EstudianteDB.id == estudiante_id).first()
    
    if not estudiante: 
        logger.warning(f"Error 404: Estudiante con id {estudiante_id} no encontrado")
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    return estudiante

@app.post("/estudiantes", response_model=EstudianteResponse, status_code=status.HTTP_201_CREATED)
def crear_estudiante(estudiante: EstudianteCreate, db: Session = Depends(get_db)):
    logger.info(f"POST /estudiantes - Creando estudiante: {estudiante.nombre}")
    
    db_estudiante = EstudianteDB(**estudiante.model_dump())
    db.add(db_estudiante)
    db.commit()
    db.refresh(db_estudiante)
    
    logger.info(f"Éxito: Estudiante creado con id {db_estudiante.id}")
    return db_estudiante

@app.delete("/estudiantes/{estudiante_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_estudiante(estudiante_id: int, db: Session = Depends(get_db)):
    logger.info(f"DELETE /estudiantes/{estudiante_id} - Intentando borrar")
    estudiante = db.query(EstudianteDB).filter(EstudianteDB.id == estudiante_id).first()
    
    if not estudiante: 
        logger.warning(f"Error 404 al borrar: Estudiante {estudiante_id} no encontrado")
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    
    db.delete(estudiante)
    db.commit()
    logger.info(f"Éxito: Estudiante {estudiante_id} borrado")
    return