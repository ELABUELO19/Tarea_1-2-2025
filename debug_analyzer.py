#!/usr/bin/env python3
"""
Script de depuración para verificar el guardado en base de datos
"""

import asyncio
import psycopg2
from remote_llm_service import MultipleLLMService

async def test_single_question():
    print("=== PRUEBA DE UNA SOLA PREGUNTA ===")
    
    # Configurar servicios SIN database manager, usando conexión directa
    llm_service = MultipleLLMService()
    
    # Usar conexión directa con psycopg2
    conn = psycopg2.connect(
        host='localhost', 
        port=5432, 
        database='yahoo_answers', 
        user='postgres', 
        password='postgres123'
    )
    cur = conn.cursor()
    
    # Obtener una pregunta específica
    cur.execute("SELECT id, question_title, question_content FROM questions WHERE quality_score = 0.0 LIMIT 1")
    row = cur.fetchone()
    
    if not row:
        print("❌ No hay preguntas sin procesar")
        conn.close()
        return
    
    question_id, question_title, question_content = row
    print(f"🔍 Procesando pregunta ID {question_id}")
    print(f"📝 Título: {question_title[:50]}...")
    
    # Analizar con LLM (esto debería usar fallback)
    result = await llm_service.analyze_with_fallbacks(
        question_title, 
        question_content
    )
    
    print(f"🤖 Resultado LLM: {result}")
    
    # Verificar que tenemos un resultado válido
    if result.get("quality"):
        quality_map = {"ALTA": 3.0, "MEDIA": 2.0, "BAJA": 1.0}
        quality_score = quality_map.get(result["quality"], 1.0)
        
        print(f"✅ Calidad obtenida: {result['quality']} -> Score: {quality_score}")
        
        try:
            # Actualizar en base de datos usando psycopg2 directamente
            print("💾 Intentando guardar en base de datos...")
            llm_answer = f"Calidad: {result['quality']} (Provider: {result.get('provider', 'unknown')})"
            
            print(f"📝 Datos a guardar:")
            print(f"   - quality_score: {quality_score}")
            print(f"   - llm_answer: {llm_answer}")
            
            cur.execute(
                "UPDATE questions SET quality_score = %s, llm_answer = %s WHERE id = %s",
                (quality_score, llm_answer, question_id)
            )
            affected = cur.rowcount
            conn.commit()
            
            print(f"✅ ¡Guardado exitoso! Filas afectadas: {affected}")
            
            # Verificar que se guardó correctamente
            cur.execute("SELECT quality_score, llm_answer FROM questions WHERE id = %s", (question_id,))
            row = cur.fetchone()
            print(f"🔍 Verificación:")
            print(f"   - quality_score: {row[0]}")
            print(f"   - llm_answer: {row[1]}")
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Error guardando: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"❌ No se obtuvo calidad válida: {result}")
    
    conn.close()
    print("✅ Prueba completada")

if __name__ == "__main__":
    asyncio.run(test_single_question())