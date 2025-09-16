#!/usr/bin/env python3
"""
Script para probar la API de OpenAI
"""

import os
from dotenv import load_dotenv
import requests

# Cargar variables de entorno
load_dotenv()

def test_openai_api():
    """Probar conexión con OpenAI"""
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ No se encontró OPENAI_API_KEY en el archivo .env")
        return False
    
    print(f"🔑 API Key encontrada: {api_key[:20]}...")
    
    # Probar con una llamada simple
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {
                "role": "user",
                "content": "Responde solo con 'PRUEBA EXITOSA' si recibes este mensaje."
            }
        ],
        "max_tokens": 10,
        "temperature": 0
    }
    
    try:
        print("🤖 Probando conexión con OpenAI...")
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print(f"✅ ¡Éxito! Respuesta de OpenAI: {content}")
            print(f"📊 Tokens usados: {result.get('usage', {}).get('total_tokens', 'N/A')}")
            return True
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

if __name__ == "__main__":
    print("=== PRUEBA DE API OPENAI ===")
    success = test_openai_api()
    if success:
        print("🎉 ¡La API de OpenAI está funcionando correctamente!")
    else:
        print("⚠️ Hay problemas con la configuración de OpenAI")