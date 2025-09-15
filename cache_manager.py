import json
import hashlib
import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

# Importación de Redis con manejo de errores
import redis

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CacheManager:
    """Gestor del sistema de cache usando Redis"""
    
    def __init__(self):
        # Configuración de Redis
        self.redis_host = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', '6379'))
        
        # Estadísticas de cache
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'sets': 0,
            'total_operations': 0,
            'policy_type': 'TTL-LRU',  # Política actual
            'start_time': datetime.now()
        }
        self.redis_db = int(os.getenv('REDIS_DB', '0'))
        
        # Configuración del cache
        self.cache_ttl = int(os.getenv('CACHE_TTL', '3600'))  # TTL en segundos
        self.max_cache_size = int(os.getenv('CACHE_SIZE', '500'))  # Reducido para provocar evictions
        
        # Conectar a Redis
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Verificar conexión
            self.redis_client.ping()
            logger.info(f"Conectado a Redis en {self.redis_host}:{self.redis_port}")
        except Exception as e:
            logger.error(f"Error conectando a Redis: {e}")
            self.redis_client = None
        
        # Métricas del cache
        self.hits = 0
        self.misses = 0
    
    def _generate_key(self, question_title: str, question_content: str = "") -> str:
        """Generar una clave única para la pregunta"""
        content = f"{question_title}|{question_content}".strip()
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def get(self, question_title: str, question_content: str = "") -> Optional[Dict[str, Any]]:
        """Buscar una respuesta en el cache"""
        self.cache_stats['total_operations'] += 1
        
        if not self.redis_client:
            self.misses += 1
            self.cache_stats['misses'] += 1
            return None
            
        try:
            cache_key = self._generate_key(question_title, question_content)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                # Verificar que cached_data es una string antes de deserializar
                if isinstance(cached_data, str):
                    self.hits += 1
                    self.cache_stats['hits'] += 1
                    
                    # Actualizar TTL para simular LRU (acceso reciente)
                    self.redis_client.expire(cache_key, self.cache_ttl)
                    
                    logger.info(f"Cache HIT para pregunta: '{question_title[:100]}'")
                    return json.loads(cached_data)
                else:
                    logger.warning(f"Datos del cache en formato incorrecto")
                    self.misses += 1
                    self.cache_stats['misses'] += 1
                    return None
            else:
                self.misses += 1
                self.cache_stats['misses'] += 1
                logger.info(f"Cache MISS para pregunta: '{question_title[:100]}'")
                return None
                
        except Exception as e:
            logger.error(f"Error accediendo al cache: {e}")
            self.misses += 1
            self.cache_stats['misses'] += 1
            return None
    
    def set(self, question_title: str, question_content: str, data: Dict[str, Any]) -> bool:
        """Almacenar una respuesta en el cache"""
        if not self.redis_client:
            return False
            
        try:
            cache_key = self._generate_key(question_title, question_content)
            
            # Añadir timestamp para gestión de TTL
            data['cached_at'] = datetime.utcnow().isoformat()
            
            # Verificar el tamaño del cache y limpiar si es necesario
            self._manage_cache_size()
            
            # Almacenar en Redis con TTL
            success = self.redis_client.setex(
                cache_key, 
                self.cache_ttl, 
                json.dumps(data, default=str)
            )
            
            if success:
                self.cache_stats['sets'] += 1
                logger.info(f"Cache SET para pregunta: '{question_title[:100]}'")
                return True
            else:
                logger.warning(f"No se pudo almacenar en cache: '{question_title[:100]}'")
                return False
                
        except Exception as e:
            logger.error(f"Error almacenando en cache: {e}")
            return False
    
    def _manage_cache_size(self):
        """Gestionar el tamaño del cache implementando LRU"""
        if not self.redis_client:
            return
            
        try:
            current_size_result = self.redis_client.dbsize()
            
            # Verificar que el resultado es un entero
            if not isinstance(current_size_result, int):
                logger.warning("No se pudo obtener el tamaño del cache")
                return
                
            current_size = current_size_result
            
            if current_size >= self.max_cache_size:
                # Obtener todas las claves con su TTL
                keys_result = self.redis_client.keys('*')
                
                # Verificar que el resultado es una lista
                if not isinstance(keys_result, list):
                    logger.warning("No se pudieron obtener las claves del cache")
                    return
                
                keys = keys_result
                
                # Si hay demasiadas claves, eliminar las más antiguas
                if len(keys) >= self.max_cache_size:
                    # Ordenar por TTL (las que tienen menor TTL son más antiguas)
                    keys_with_ttl = []
                    for key in keys:
                        ttl = self.redis_client.ttl(key)
                        if isinstance(ttl, int):
                            keys_with_ttl.append((key, ttl))
                    
                    # Ordenar por TTL ascendente
                    keys_with_ttl.sort(key=lambda x: x[1])
                    
                    # Eliminar el 10% de las claves más antiguas
                    keys_to_remove = int(len(keys_with_ttl) * 0.1)
                    evicted_keys = 0
                    for i in range(keys_to_remove):
                        if self.redis_client.delete(keys_with_ttl[i][0]):
                            evicted_keys += 1
                    
                    self.cache_stats['evictions'] += evicted_keys
                    logger.info(f"Limpieza de cache: eliminadas {evicted_keys} entradas (política TTL-LRU)")
                    
        except Exception as e:
            logger.error(f"Error gestionando tamaño del cache: {e}")
    
    def update_access_count(self, question_title: str, question_content: str = ""):
        """Actualizar el contador de acceso en el cache"""
        if not self.redis_client:
            return 1
            
        try:
            cache_key = self._generate_key(question_title, question_content)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data and isinstance(cached_data, str):
                data = json.loads(cached_data)
                data['access_count'] = data.get('access_count', 1) + 1
                data['last_accessed'] = datetime.utcnow().isoformat()
                
                # Actualizar en Redis
                self.redis_client.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(data, default=str)
                )
                
                logger.info(f"Contador actualizado para: {question_title[:50]}...")
                return data['access_count']
            
        except Exception as e:
            logger.error(f"Error actualizando contador de acceso: {e}")
        
        return 1
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del cache"""
        try:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
            miss_rate = (self.misses / total_requests * 100) if total_requests > 0 else 0
            
            if self.redis_client:
                cache_size_result = self.redis_client.dbsize()
                memory_info_result = self.redis_client.info('memory')
                
                cache_size = cache_size_result if isinstance(cache_size_result, int) else 0
                
                # Manejo seguro de memory_info
                memory_used = 'N/A'
                memory_peak = 'N/A'
                if isinstance(memory_info_result, dict):
                    memory_used = memory_info_result.get('used_memory_human', 'N/A')
                    memory_peak = memory_info_result.get('used_memory_peak_human', 'N/A')
            else:
                cache_size = 0
                memory_used = 'N/A'
                memory_peak = 'N/A'
            
            return {
                'hits': self.hits,
                'misses': self.misses,
                'total_requests': total_requests,
                'hit_rate': round(hit_rate, 2),
                'miss_rate': round(miss_rate, 2),
                'cache_size': cache_size,
                'max_cache_size': self.max_cache_size,
                'cache_ttl': self.cache_ttl,
                'memory_used': memory_used,
                'memory_peak': memory_peak
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas del cache: {e}")
            return {
                'hits': self.hits,
                'misses': self.misses,
                'total_requests': self.hits + self.misses,
                'hit_rate': 0,
                'miss_rate': 0,
                'cache_size': 0,
                'max_cache_size': self.max_cache_size,
                'cache_ttl': self.cache_ttl,
                'memory_used': 'N/A',
                'memory_peak': 'N/A'
            }
    
    def clear_cache(self):
        """Limpiar todo el cache"""
        if not self.redis_client:
            logger.warning("No hay conexión a Redis para limpiar cache")
            return
            
        try:
            self.redis_client.flushdb()
            self.hits = 0
            self.misses = 0
            logger.info("Cache limpiado completamente")
        except Exception as e:
            logger.error(f"Error limpiando cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas detalladas del cache"""
        try:
            # Calcular métricas adicionales
            total_ops = self.cache_stats['total_operations']
            hits = self.cache_stats['hits']
            misses = self.cache_stats['misses']
            
            hit_rate = (hits / total_ops * 100) if total_ops > 0 else 0
            miss_rate = (misses / total_ops * 100) if total_ops > 0 else 0
            
            # Obtener info actual de Redis
            current_size = 0
            memory_usage = 0
            if self.redis_client:
                try:
                    current_size = self.redis_client.dbsize()
                    info = self.redis_client.info('memory')
                    memory_usage = info.get('used_memory', 0)
                except:
                    pass
            
            runtime = datetime.now() - self.cache_stats['start_time']
            
            return {
                'policy_type': self.cache_stats['policy_type'],
                'runtime_seconds': runtime.total_seconds(),
                'total_operations': total_ops,
                'hits': hits,
                'misses': misses,
                'sets': self.cache_stats['sets'],
                'evictions': self.cache_stats['evictions'],
                'hit_rate_percent': round(hit_rate, 2),
                'miss_rate_percent': round(miss_rate, 2),
                'current_cache_size': current_size,
                'max_cache_size': self.max_cache_size,
                'memory_usage_bytes': memory_usage,
                'cache_efficiency': round(hits / (hits + misses + self.cache_stats['evictions']) * 100, 2) if (hits + misses + self.cache_stats['evictions']) > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error calculando estadísticas: {e}")
            return {}
    
    def reset_stats(self):
        """Reiniciar estadísticas del cache"""
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'sets': 0,
            'total_operations': 0,
            'policy_type': 'TTL-LRU',
            'start_time': datetime.now()
        }
        self.hits = 0
        self.misses = 0
        logger.info("Estadísticas del cache reiniciadas")

if __name__ == "__main__":
    # Probar el sistema de cache
    cache = CacheManager()
    
    # Ejemplo de uso
    test_data = {
        'llm_answer': 'Esta es una respuesta de prueba',
        'quality_score': 0.85,
        'access_count': 1
    }
    
    # Almacenar en cache
    cache.set("¿Qué es Python?", "Explica qué es Python", test_data)
    
    # Buscar en cache
    result = cache.get("¿Qué es Python?", "Explica qué es Python")
    print("Resultado del cache:", result)
    
    # Ver estadísticas
    stats = cache.get_cache_stats()
    print("Estadísticas del cache:", stats)
