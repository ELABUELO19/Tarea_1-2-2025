# Sistema de Análisis LLM - Yahoo Answers

Sistema de análisis de calidad de preguntas y respuestas usando APIs remotas de LLM con fallback automático.

## 🚀 Características

- **APIs Remotas**: Groq, Together, HuggingFace, OpenAI
- **Fallback Automático**: Cambia providers cuando se agota cuota
- **Alta Velocidad**: 3+ consultas/segundo
- **Dockerizado**: Fácil despliegue y escalabilidad
- **Cache Redis**: Optimización de rendimiento
- **PostgreSQL**: Persistencia de datos

## 📋 Requisitos

- Docker & Docker Compose
- Al menos una API key de LLM (recomendado: Groq gratuito)

## ⚙️ Configuración

### 1. Configurar API Keys

Edita `api_config.py`:

```python
API_KEYS = {
    "groq": "gsk_tu_api_key_aqui",  # Gratis en https://console.groq.com/keys
    "together": "tu_api_key_aqui",
    "huggingface": "hf_tu_api_key_aqui",
    "openai": "sk_tu_api_key_aqui"
}

# Habilita los proveedores que tengas configurados
PROVIDERS_CONFIG = [
    {
        "name": "groq",
        "enabled": True,  # Cambiar a True si tienes API key
        ...
    }
]
```

### 2. Preparar Dataset

Asegúrate de tener `train.csv` en el directorio raíz.

## 🐳 Ejecución con Docker

### Iniciar Sistema Completo

```bash
# Construir e iniciar todos los servicios
docker-compose up -d

# Ver logs del analizador
docker-compose logs -f analyzer

# Parar sistema
docker-compose down
```

### Servicios Incluidos

- **PostgreSQL**: Base de datos (puerto 5432)
- **Redis**: Cache (puerto 6379) 
- **Analyzer**: Procesador LLM

## 🖥️ Ejecución Local

```bash
# Instalar dependencias
pip install -r requirements.txt

# Asegurar que PostgreSQL y Redis estén corriendo
docker-compose up postgres redis -d

# Ejecutar analizador
python run.py
```

## 📊 Monitoreo

### Ver Estado de Base de Datos

```bash
# Conectar a PostgreSQL
docker exec -it yahoo_postgres psql -U postgres -d yahoo_answers

# Consultar estadísticas
SELECT 
  COUNT(*) as total,
  COUNT(CASE WHEN quality_score > 0 THEN 1 END) as processed
FROM questions;
```

### Ver Logs

```bash
# Logs del analizador
docker-compose logs analyzer

# Logs en tiempo real
docker-compose logs -f analyzer
```

## 🔧 Configuración Avanzada

### Variables de Entorno

```bash
# Base de datos
POSTGRES_HOST=postgres
POSTGRES_DB=yahoo_answers
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
```

### Parámetros del Analizador

En `analyzer.py`:

```python
await analyzer.run_analysis(
    max_questions=12000,    # Máximo de preguntas a procesar
    batch_size=50,          # Tamaño de lote
    max_concurrent=10       # Requests concurrentes
)
```

## 📈 Rendimiento Esperado

- **Con APIs reales**: 3-5 consultas/segundo
- **12,000 registros**: ~40-60 minutos
- **Cache hits**: Acelera procesamientos repetidos

## 🔍 Estructura del Proyecto

```
├── analyzer.py              # Analizador principal
├── remote_llm_service.py    # Servicio de APIs remotas
├── api_config.py           # Configuración de APIs
├── database.py             # Gestor de base de datos
├── cache_manager.py        # Gestor de cache Redis
├── docker-compose.yml      # Configuración Docker
├── Dockerfile              # Imagen del analizador
├── requirements.txt        # Dependencias Python
├── run.py                  # Script de inicio
└── init.sql               # Esquema inicial de BD
```

## ⚡ Solución de Problemas

### API Keys Inválidas
```
ERROR: API keys no configuradas para: ['groq']
```
**Solución**: Configura al menos una API key válida en `api_config.py`

### Error de Conexión BD
```
ERROR: could not connect to server
```
**Solución**: Verifica que PostgreSQL esté funcionando:
```bash
docker-compose up postgres -d
```

### Cache No Disponible
```
WARNING: Redis connection failed
```
**Solución**: Inicia Redis:
```bash
docker-compose up redis -d
```

## 🎯 Obtener API Keys Gratuitas

1. **Groq** (Recomendado): https://console.groq.com/keys
2. **Together**: https://api.together.xyz/settings/api-keys
3. **HuggingFace**: https://huggingface.co/settings/tokens
4. **OpenAI**: https://platform.openai.com/api-keys (de pago)

## 📞 Soporte

Para problemas o preguntas, revisa los logs:
```bash
docker-compose logs analyzer
tail -f analysis.log
```
