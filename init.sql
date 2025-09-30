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
        COUNT(*)::BIGINT as total_questions,
        COUNT(CASE WHEN llm_answer IS NOT NULL THEN 1 END)::BIGINT as processed_questions,
        ROUND(AVG(CASE WHEN quality_score > 0 THEN quality_score END)::numeric, 3) as avg_quality_score,
        (SELECT original_class FROM questions WHERE original_class IS NOT NULL 
         GROUP BY original_class ORDER BY COUNT(*) DESC LIMIT 1) as top_class,
        (SELECT question_title FROM questions 
         WHERE question_title IS NOT NULL 
         ORDER BY access_count DESC LIMIT 1) as most_accessed_question
    FROM questions;
END;
$$ LANGUAGE plpgsql;

-- Crear vista para análisis rápido
CREATE OR REPLACE VIEW questions_summary AS
SELECT 
    COALESCE(original_class, -1) as original_class,
    COUNT(*) as question_count,
    COUNT(CASE WHEN llm_answer IS NOT NULL THEN 1 END) as processed_count,
    ROUND(AVG(CASE WHEN quality_score > 0 THEN quality_score END)::numeric, 3) as avg_score,
    MAX(access_count) as max_access_count
FROM questions
GROUP BY original_class
ORDER BY original_class NULLS LAST;

-- Crear tabla multi_model_results para almacenar resultados de múltiples modelos LLM
CREATE TABLE IF NOT EXISTS multi_model_results (
    id SERIAL PRIMARY KEY,
    question_id INTEGER REFERENCES questions(id),
    model_name VARCHAR(100),
    model_provider VARCHAR(50),
    answer TEXT,
    quality_score FLOAT,
    response_time FLOAT,
    cost_tier VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(question_id, model_name)
);

-- Crear índices para multi_model_results
CREATE INDEX IF NOT EXISTS idx_multi_model_question_id ON multi_model_results(question_id);
CREATE INDEX IF NOT EXISTS idx_multi_model_model_name ON multi_model_results(model_name);
CREATE INDEX IF NOT EXISTS idx_multi_model_quality_score ON multi_model_results(quality_score);

-- Crear vista para comparación de modelos
CREATE OR REPLACE VIEW model_comparison AS
SELECT 
    m.model_name,
    m.model_provider,
    COUNT(*) as total_answers,
    ROUND(AVG(m.quality_score)::numeric, 3) as avg_quality_score,
    ROUND(AVG(m.response_time)::numeric, 3) as avg_response_time,
    m.cost_tier,
    COUNT(CASE WHEN m.quality_score >= 2.5 THEN 1 END) as high_quality_answers
FROM multi_model_results m
GROUP BY m.model_name, m.model_provider, m.cost_tier
ORDER BY avg_quality_score DESC;
