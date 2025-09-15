"""
Servicio LLM Remoto con APIs Externas
=====================================
Sistema de LLM que usa APIs remotas con fallback automático cuando se agota la cuota.
"""

import asyncio
import aiohttp
import logging
import time
import json
from typing import Dict, List, Optional, Union
from collections import defaultdict

from api_config import get_enabled_providers, validate_api_keys

logger = logging.getLogger(__name__)

class RemoteLLMService:
    """Servicio LLM con APIs remotas y fallback automático"""
    
    def __init__(self):
        """Inicializar servicio con múltiples proveedores de LLM"""
        self.current_provider = 0
        self.request_count = {}
        self.quota_exceeded = set()
        
        # Cargar configuración de proveedores
        self.providers = validate_api_keys()
        
        # Detectar modo demo
        self.demo_mode = len(self.providers) == 0
        
        if self.demo_mode:
            logger.warning("⚠️  Ejecutando en modo DEMO - sin APIs reales configuradas")
            self.providers = []
        else:
            logger.info(f"Cargados {len(self.providers)} proveedores LLM")
        
        # Inicializar contadores
        for provider in self.providers:
            self.request_count[provider["name"]] = {"count": 0, "last_reset": time.time()}
    
    async def _make_request(self, provider: Dict, prompt: str) -> Optional[str]:
        """Hacer request a un proveedor específico"""
        try:
            # Verificar límites de rate
            if not self._check_rate_limit(provider):
                logger.warning(f"Rate limit excedido para {provider['name']}")
                return None
            
            headers = {
                "Authorization": f"Bearer {provider['api_key']}",
                "Content-Type": "application/json"
            }
            
            # Prompt optimizado para análisis de calidad
            system_prompt = "Eres un experto en evaluar la calidad de respuestas. Analiza si la respuesta responde correctamente a la pregunta. Responde solo con: ALTA, MEDIA o BAJA."
            
            payload = {
                "model": provider["model"],
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Pregunta: {prompt[:200]}...\nEvalúa la calidad de esta respuesta en una palabra."}
                ],
                "max_tokens": provider["max_tokens"],
                "temperature": provider["temperature"]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    provider["base_url"],
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 429:  # Rate limit exceeded
                        logger.warning(f"Cuota agotada para {provider['name']}")
                        self.quota_exceeded.add(provider["name"])
                        return None
                    
                    if response.status != 200:
                        logger.error(f"Error {response.status} en {provider['name']}")
                        return None
                    
                    data = await response.json()
                    
                    # Incrementar contador de requests
                    self.request_count[provider["name"]]["count"] += 1
                    
                    # Extraer respuesta
                    if "choices" in data and len(data["choices"]) > 0:
                        content = data["choices"][0]["message"]["content"].strip()
                        logger.info(f"Respuesta de {provider['name']}: {content[:50]}...")
                        return content
                    
                    return None
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout en {provider['name']}")
            return None
        except Exception as e:
            logger.error(f"Error en {provider['name']}: {e}")
            return None
    
    def _check_rate_limit(self, provider: Dict) -> bool:
        """Verificar si podemos hacer request a este proveedor"""
        provider_name = provider["name"]
        
        # Si está en lista de cuota agotada, skip
        if provider_name in self.quota_exceeded:
            return False
        
        current_time = time.time()
        counter = self.request_count[provider_name]
        
        # Reset contador cada minuto
        if current_time - counter["last_reset"] > 60:
            counter["count"] = 0
            counter["last_reset"] = current_time
        
        # Verificar límite
        return counter["count"] < provider["requests_per_minute"]
    
    def _get_available_providers(self) -> List[Dict]:
        """Obtener proveedores disponibles ordenados por prioridad"""
        if self.demo_mode:
            return []  # En modo demo no hay proveedores reales
            
        available = []
        for provider in self.providers:
            if self._check_rate_limit(provider):
                available.append(provider)
        
        # Ordenar por prioridad (menor número = mayor prioridad)
        return sorted(available, key=lambda x: x["priority"])
    
    async def analyze_quality_with_fallback(self, question: str, answer: str) -> Dict:
        """Analizar calidad con sistema de fallback automático"""
        start_time = time.time()
        
        # Crear prompt optimizado
        prompt = f"Pregunta: {question[:200]}\nRespuesta: {answer[:300]}"
        
        # Intentar con proveedores disponibles
        available_providers = self._get_available_providers()
        
        if not available_providers:
            logger.warning("No hay proveedores disponibles, usando fallback")
            return {
                "quality": "MEDIA",
                "score": 60,
                "provider": "fallback",
                "response_time": time.time() - start_time,
                "error": "No providers available"
            }
        
        for provider in available_providers:
            try:
                logger.info(f"🤖 Intentando con {provider['name']}...")
                result = await self._make_request(provider, prompt)
                
                if result:
                    # Procesar respuesta del LLM
                    quality = self._parse_quality_response(result)
                    score = self._quality_to_score(quality)
                    
                    return {
                        "quality": quality,
                        "score": score,
                        "provider": provider["name"],
                        "response_time": time.time() - start_time,
                        "raw_response": result
                    }
                    
            except Exception as e:
                logger.error(f"Error con {provider['name']}: {e}")
                continue
        
        # Si todos fallan, usar fallback
        logger.warning("Todos los proveedores fallaron, usando respuesta por defecto")
        return {
            "quality": "MEDIA", 
            "score": 60,
            "provider": "fallback",
            "response_time": time.time() - start_time,
            "error": "All providers failed"
        }
    
    def _parse_quality_response(self, response: str) -> str:
        """Parsear respuesta del LLM para extraer calidad"""
        response_upper = response.upper().strip()
        
        if "ALTA" in response_upper or "HIGH" in response_upper:
            return "ALTA"
        elif "BAJA" in response_upper or "LOW" in response_upper:
            return "BAJA"
        else:
            return "MEDIA"
    
    def _quality_to_score(self, quality: str) -> int:
        """Convertir calidad a score numérico"""
        quality_scores = {
            "ALTA": 85,
            "MEDIA": 65,
            "BAJA": 35
        }
        return quality_scores.get(quality, 60)
    
    def get_status(self) -> Dict:
        """Obtener estado del servicio"""
        available_providers = self._get_available_providers()
        
        return {
            "service_type": "remote_llm_apis",
            "available_providers": [p["name"] for p in available_providers],
            "quota_exceeded": list(self.quota_exceeded),
            "total_providers": len(self.providers),
            "is_available": len(available_providers) > 0,
            "current_provider": available_providers[0]["name"] if available_providers else None,
            "request_counts": {
                name: counter["count"] 
                for name, counter in self.request_count.items()
            }
        }
    
    def reset_quota_status(self):
        """Reset estado de cuotas (útil para testing)"""
        self.quota_exceeded.clear()
        for provider_name in self.request_count:
            self.request_count[provider_name] = {"count": 0, "last_reset": time.time()}


class MultipleLLMService:
    """Servicio que combina múltiples estrategias de LLM"""
    
    def __init__(self):
        self.primary_llm = RemoteLLMService()
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0,
            "provider_usage": {}
        }
    
    async def analyze_with_fallbacks(self, question: str, answer: str) -> Dict:
        """Analizar con sistema completo de fallbacks"""
        self.stats["total_requests"] += 1
        
        try:
            result = await self.primary_llm.analyze_quality_with_fallback(question, answer)
            
            if "error" not in result:
                self.stats["successful_requests"] += 1
                
                # Actualizar estadísticas por proveedor
                provider = result.get("provider", "unknown")
                if provider not in self.stats["provider_usage"]:
                    self.stats["provider_usage"][provider] = 0
                self.stats["provider_usage"][provider] += 1
            else:
                self.stats["failed_requests"] += 1
            
            # Actualizar tiempo promedio
            if self.stats["successful_requests"] > 0:
                current_avg = self.stats["average_response_time"]
                new_time = result.get("response_time", 0)
                self.stats["average_response_time"] = (
                    (current_avg * (self.stats["successful_requests"] - 1) + new_time) / 
                    self.stats["successful_requests"]
                )
            
            return result
            
        except Exception as e:
            self.stats["failed_requests"] += 1
            logger.error(f"Error en análisis LLM: {e}")
            return {
                "quality": "MEDIA",
                "score": 60,
                "provider": "error_fallback",
                "response_time": 0,
                "error": str(e)
            }
    
    def get_comprehensive_status(self) -> Dict:
        """Obtener estado completo del servicio"""
        primary_status = self.primary_llm.get_status()
        
        return {
            **primary_status,
            "stats": self.stats,
            "success_rate": (
                self.stats["successful_requests"] / max(self.stats["total_requests"], 1) * 100
            )
        }
