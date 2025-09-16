import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración de API Keys - usando variables de entorno
API_KEYS = {
    # APIs ACTUALES - Cargadas desde variables de entorno
    "groq": os.getenv("GROQ_API_KEY", ""),
    "deepseek": os.getenv("DEEPSEEK_API_KEY", ""),
    "openai": os.getenv("OPENAI_API_KEY", ""),
    "gemini": os.getenv("GEMINI_API_KEY", "")
}

# Configuración de proveedores
PROVIDERS_CONFIG = [
    {
        "name": "groq",
        "enabled": True,
        "api_key": API_KEYS["groq"],
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "model": "llama-3.1-70b-versatile",
        "max_tokens": 256,  # Reducido para mayor velocidad
        "temperature": 0.7,
        "requests_per_minute": 30,  # Límite oficial
        "tokens_per_minute": 6000,  # 6K TPM límite oficial
        "requests_per_day": 14400,  # 14.4K RPD límite oficial
        "priority": 1
    },
    {
        "name": "deepseek",
        "enabled": True,  # ✅ HABILITADO - ya tienes API key
        "api_key": API_KEYS["deepseek"],
        "base_url": "https://api.deepseek.com/chat/completions",
        "model": "deepseek-chat",
        "max_tokens": 800,  # Más generoso para análisis profundo
        "temperature": 0.7,
        "requests_per_minute": 20,  # Conservador basado en datos comunitarios
        "tokens_per_minute": 8000,  # Estimado conservador
        "requests_per_day": 900,  # Límite diario reportado
        "priority": 2
    },
    {
        "name": "gemini",
        "enabled": True,
        "api_key": API_KEYS["gemini"],
        "base_url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
        "model": "gemini-1.5-flash",  # Modelo Flash más rápido y con mayor cuota
        "max_tokens": 512,  # Reducido para evitar problemas
        "temperature": 0.7,
        "requests_per_minute": 15,  # Límite oficial Gemini Flash
        "tokens_per_minute": 1000000,  # 1M TPM límite oficial Flash
        "requests_per_day": 1500,  # 1.5K RPD límite oficial Flash
        "priority": 3
    },
    {
        "name": "openai",
        "enabled": True,
        "api_key": API_KEYS["openai"],
        "base_url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-3.5-turbo",
        "max_tokens": 150,  # Muy conservador para no agotar cuota rápido
        "temperature": 0.7,
        "requests_per_minute": 3,  # Límite oficial free tier
        "tokens_per_minute": 40000,  # 40K TPM límite oficial chat
        "requests_per_day": 200,  # Estimado conservador para free tier
        "priority": 4
    }
]

def get_enabled_providers():
    """Obtener solo los proveedores habilitados"""
    return [p for p in PROVIDERS_CONFIG if p["enabled"]]

def validate_api_keys():
    """Validar que al menos un proveedor está configurado o activar modo demo"""
    enabled = get_enabled_providers()
    if not enabled:
        print("⚠️  No hay proveedores habilitados. Activando modo demo.")
        return []
    
    invalid_keys = []
    valid_providers = []
    
    for provider in enabled:
        if not provider["api_key"] or "xxxx" in provider["api_key"].lower() or "XXXXX" in provider["api_key"]:
            invalid_keys.append(provider["name"])
        else:
            valid_providers.append(provider)
    
    if invalid_keys and not valid_providers:
        print(f"⚠️  API keys no configuradas para: {invalid_keys}. Activando modo demo.")
        return []
    elif invalid_keys:
        print(f"⚠️  API keys inválidas para: {invalid_keys}. Usando proveedores válidos.")
    
    return valid_providers if valid_providers else []
