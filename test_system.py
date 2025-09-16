#!/usr/bin/env python3
"""
Script para probar el sistema con solo OpenAI configurado
"""

import asyncio
from remote_llm_service import MultipleLLMService

async def test_system():
    print("=== PRUEBA DEL SISTEMA CON SOLO OPENAI ===")
    
    llm_service = MultipleLLMService()
    
    # Probar con una pregunta de ejemplo
    test_question = "¿Cuál es la mejor manera de aprender programación?"
    test_answer = "Practicando todos los días y construyendo proyectos reales."
    
    print(f"🤖 Probando análisis de: {test_question}")
    
    result = await llm_service.analyze_with_fallbacks(test_question, test_answer)
    
    print(f"✅ Resultado: {result}")
    
    # Obtener estadísticas del servicio
    try:
        stats = llm_service.get_status()
        print(f"📊 Estado del servicio: {stats}")
    except Exception as e:
        print(f"⚠️ No se pudieron obtener estadísticas: {e}")

if __name__ == "__main__":
    asyncio.run(test_system())