import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración de API Keys - usando variables de entorno
API_KEYS = {
    "openai": os.getenv("OPENAI_API_KEY"),
}

# Configuración de proveedores
PROVIDERS_CONFIG = [
    {
        "name": "openai",
        "enabled": True,
        "api_key": API_KEYS["openai"],
        "base_url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-3.5-turbo",
        "max_tokens": 150,
        "temperature": 0.7,
        "requests_per_minute": 3,
        "tokens_per_minute": 40000,
        "requests_per_day": 200,
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