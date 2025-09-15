import os
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, Index, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class Question(Base):
    """Modelo para almacenar las preguntas y respuestas"""
    __tablename__ = 'questions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_title = Column(Text, nullable=False)
    question_content = Column(Text, nullable=False, default='')
    original_answer = Column(Text, nullable=True)
    llm_answer = Column(Text, nullable=True)
    quality_score = Column(Float, nullable=True, default=0.0)
    access_count = Column(Integer, default=1)
    original_class = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    first_access = Column(DateTime, default=datetime.utcnow)
    last_access = Column(DateTime, default=datetime.utcnow)
    
    # Crear índices para mejorar el rendimiento
    __table_args__ = (
        Index('idx_questions_title_content', 'question_title', 'question_content'),
        Index('idx_questions_quality_score', 'quality_score'),
        Index('idx_questions_access_count', 'access_count'),
        Index('idx_questions_created_at', 'created_at'),
        Index('idx_questions_class', 'original_class'),
    )

class DatabaseManager:
    """Gestor de la base de datos"""
    
    def __init__(self):
        # Obtener configuración desde variables de entorno
        db_host = os.getenv('POSTGRES_HOST', 'localhost')  # Para Docker y local
        db_port = os.getenv('POSTGRES_PORT', '5432')
        db_name = os.getenv('POSTGRES_DB', 'yahoo_answers')
        db_user = os.getenv('POSTGRES_USER', 'postgres')
        db_password = os.getenv('POSTGRES_PASSWORD', 'postgres123')
        
        # Crear URL de conexión
        self.database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        # Crear engine y session con configuración robusta
        self.engine = create_engine(
            self.database_url, 
            echo=False,
            pool_pre_ping=True,  # Verificar conexiones antes de usar
            pool_recycle=3600,   # Reciclar conexiones cada hora
            connect_args={
                "connect_timeout": 10,
                "options": "-c timezone=UTC"
            }
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def test_connection(self):
        """Probar la conexión a la base de datos"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                logger.info("✅ Conexión a base de datos exitosa")
                return True
        except Exception as e:
            logger.error(f"❌ Error conectando a la base de datos: {e}")
            return False
    
    def wait_for_db(self, max_retries=30, delay=2):
        """Esperar a que la base de datos esté disponible"""
        import time
        
        for attempt in range(max_retries):
            logger.info(f"🔍 Intento {attempt + 1}/{max_retries} - Verificando conexión BD...")
            
            if self.test_connection():
                logger.info("🎉 Base de datos lista!")
                return True
            
            if attempt < max_retries - 1:
                logger.info(f"⏳ Esperando {delay} segundos antes del siguiente intento...")
                time.sleep(delay)
        
        logger.error("💥 No se pudo conectar a la base de datos después de múltiples intentos")
        return False
        
    def create_tables(self):
        """Crear todas las tablas"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Tablas creadas exitosamente")
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")
            raise
    
    def get_session(self):
        """Obtener una sesión de base de datos"""
        return self.SessionLocal()
    
    def close_session(self, session):
        """Cerrar una sesión de base de datos"""
        session.close()

class PostgreSQLManager(DatabaseManager):
    """Gestor especializado para almacenar resultados de consultas"""
    
    def store_query_result(self, record_data):
        """
        Almacena o actualiza un resultado de consulta en la base de datos.
        
        Args:
            record_data (dict): Diccionario con los datos del record:
                - question_title: título de la pregunta
                - question_content: contenido de la pregunta  
                - original_answer: respuesta original
                - llm_answer: respuesta del LLM (puede ser None)
                - quality_score: puntuación de calidad (puede ser None)
                - cache_hit: si fue hit o miss del cache
                - timestamp: tiempo de la consulta
        """
        session = self.get_session()
        try:
            # Buscar si ya existe una pregunta con el mismo título y contenido
            existing_question = session.query(Question).filter(
                Question.question_title == record_data['question_title'],
                Question.question_content == record_data.get('question_content')
            ).first()
            
            if existing_question:
                # Actualizar pregunta existente
                existing_question.access_count += 1
                existing_question.updated_at = datetime.utcnow()
                
                # Actualizar respuesta LLM y score si se proporcionan
                if record_data.get('llm_answer'):
                    existing_question.llm_answer = record_data['llm_answer']
                if record_data.get('quality_score') is not None:
                    existing_question.quality_score = record_data['quality_score']
                    
                logger.info(f"Actualizada pregunta existente: {record_data['question_title'][:50]}... "
                           f"(accesos: {existing_question.access_count})")
            else:
                # Crear nueva pregunta
                new_question = Question(
                    question_title=record_data['question_title'],
                    question_content=record_data.get('question_content'),
                    original_answer=record_data['original_answer'],
                    llm_answer=record_data.get('llm_answer'),
                    quality_score=record_data.get('quality_score'),
                    access_count=1
                )
                session.add(new_question)
                logger.info(f"Nueva pregunta almacenada: {record_data['question_title'][:50]}...")
            
            session.commit()
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error almacenando resultado: {e}")
            raise
        finally:
            self.close_session(session)

# Función para obtener una instancia del gestor de BD
def get_database_manager():
    return DatabaseManager()

if __name__ == "__main__":
    # Crear las tablas al ejecutar el script directamente
    db_manager = DatabaseManager()
    db_manager.create_tables()
    print("Base de datos inicializada correctamente")
