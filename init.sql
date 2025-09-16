-- Script de inicialización para PostgreSQL
-- Este script se ejecuta automáticamente cuando se crea el contenedor

-- Crear extensiones útiles
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Crear tabla questions si no existe
CREATE TABLE IF NOT EXISTS questions (
    id SERIAL PRIMARY KEY,
    question_title TEXT NOT NULL,
    question_content TEXT DEFAULT '',
    original_answer TEXT,
    llm_answer TEXT,
    quality_score FLOAT DEFAULT 0.0,
    access_count INTEGER DEFAULT 1,
    original_class INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    first_access TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_access TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crear índices para optimizar búsquedas
CREATE INDEX IF NOT EXISTS idx_questions_title_content ON questions(question_title, question_content);
CREATE INDEX IF NOT EXISTS idx_questions_quality_score ON questions(quality_score);
CREATE INDEX IF NOT EXISTS idx_questions_access_count ON questions(access_count);
CREATE INDEX IF NOT EXISTS idx_questions_created_at ON questions(created_at);
CREATE INDEX IF NOT EXISTS idx_questions_class ON questions(original_class);

-- Crear función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Crear trigger para actualizar updated_at
DROP TRIGGER IF EXISTS update_questions_updated_at ON questions;
CREATE TRIGGER update_questions_updated_at
    BEFORE UPDATE ON questions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Crear función para estadísticas
CREATE OR REPLACE FUNCTION get_questions_stats()
RETURNS TABLE(
    total_questions BIGINT,
    processed_questions BIGINT,
    avg_quality_score NUMERIC,
    top_class INTEGER,
    most_accessed_question TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) as total_questions,
        COUNT(llm_answer) as processed_questions,
        ROUND(AVG(quality_score)::numeric, 3) as avg_quality_score,
        MODE() WITHIN GROUP (ORDER BY original_class) as top_class,
        (SELECT question_title FROM questions ORDER BY access_count DESC LIMIT 1) as most_accessed_question
    FROM questions;
END;
$$ LANGUAGE plpgsql;

-- Crear vista para análisis rápido
CREATE OR REPLACE VIEW questions_summary AS
SELECT 
    original_class,
    COUNT(*) as question_count,
    COUNT(llm_answer) as processed_count,
    ROUND(AVG(quality_score)::numeric, 3) as avg_score,
    MAX(access_count) as max_access_count
FROM questions
GROUP BY original_class
ORDER BY original_class;
