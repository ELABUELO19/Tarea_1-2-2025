#!/usr/bin/env python3
"""
Prueba DENTRO del contenedor Docker
"""

import asyncio
from database import PostgreSQLManager, Question
from remote_llm_service import MultipleLLMService

async def test_inside_container():
    print("=== PRUEBA DENTRO DEL CONTENEDOR ===")
    
    # Configurar servicios IGUAL que el analyzer
    db = PostgreSQLManager()
    llm_service = MultipleLLMService()
    
    # Obtener una pregunta específica SIN PROCESAR
    session = db.get_session()
    try:
        question = session.query(Question).filter(
            Question.quality_score == 0.0
        ).first()
        
        if not question:
            print("❌ No hay preguntas sin procesar")
            return
        
        print(f"🔍 Procesando pregunta ID {question.id}")
        print(f"📝 Título: {question.question_title[:50]}...")
        
        # Analizar con LLM (esto debería usar fallback)
        result = await llm_service.analyze_with_fallbacks(
            question.question_title, 
            question.question_content
        )
        
        print(f"🤖 Resultado LLM: {result}")
        
        # Verificar que tenemos un resultado válido
        if result.get("quality"):
            quality_map = {"ALTA": 3.0, "MEDIA": 2.0, "BAJA": 1.0}
            quality_score = quality_map.get(result["quality"], 1.0)
            
            print(f"✅ Calidad obtenida: {result['quality']} -> Score: {quality_score}")
            
            # Actualizar IGUAL que el analyzer
            print("💾 Intentando guardar en base de datos...")
            question.quality_score = quality_score
            question.llm_answer = f"Calidad: {result['quality']} (Provider: {result.get('provider', 'unknown')})"
            
            print(f"📝 Datos a guardar:")
            print(f"   - quality_score: {question.quality_score}")
            print(f"   - llm_answer: {question.llm_answer}")
            
            # COMMIT
            session.commit()
            print("✅ ¡Commit realizado!")
            
            # Verificar que se guardó correctamente
            session.refresh(question)
            print(f"🔍 Verificación después del commit:")
            print(f"   - quality_score: {question.quality_score}")
            print(f"   - llm_answer: {question.llm_answer}")
            
        else:
            print(f"❌ No se obtuvo calidad válida: {result}")
            
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()
    
    print("✅ Prueba completada")

if __name__ == "__main__":
    asyncio.run(test_inside_container())