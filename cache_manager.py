import json
import hashlib
import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CacheManager:
    """Sistema de cache con análisis de políticas LRU vs TTL"""
    
    def __init__(self, policy='TTL-LRU', cache_size=1000):
        self.redis_host = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', '6379'))
        self.policy = policy  # TTL-LRU, LRU, TTL
        self.max_cache_size = cache_size
        self.cache_ttl = int(os.getenv('CACHE_TTL', '3600'))
        
        # Métricas detalladas por política
        self.metrics = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'sets': 0,
            'total_operations': 0,
            'policy_type': policy,
            'cache_size_limit': cache_size,
            'start_time': datetime.now(),
            'hit_times': [],
            'miss_times': [],
            'eviction_reasons': []
        }
        
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=0,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            self.redis_client.ping()
            logger.info(f"Cache iniciado: Política={policy}, Tamaño={cache_size}")
        except Exception as e:
            logger.error(f"Error conectando Redis: {e}")
            self.redis_client = None
    
    def _generate_key(self, question_title: str, question_content: str = "") -> str:
        """Generar clave única para pregunta"""
        content = f"{question_title}|{question_content}".strip()
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def get(self, question_title: str, question_content: str = "") -> Optional[Dict[str, Any]]:
        """Buscar en cache con métricas detalladas"""
        start_time = datetime.now()
        self.metrics['total_operations'] += 1
        
        if not self.redis_client:
            self._record_miss(start_time)
            return None
            
        try:
            cache_key = self._generate_key(question_title, question_content)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                self._record_hit(start_time, cache_key)
                
                # Actualizar acceso para política LRU
                if 'LRU' in self.policy:
                    self.redis_client.expire(cache_key, self.cache_ttl)
                
                return json.loads(cached_data)
            else:
                self._record_miss(start_time)
                return None
                
        except Exception as e:
            logger.error(f"Error accediendo cache: {e}")
            self._record_miss(start_time)
            return None
    
    def set(self, question_title: str, question_content: str, data: Dict[str, Any]) -> bool:
        """Almacenar con gestión de políticas"""
        if not self.redis_client:
            return False
            
        try:
            cache_key = self._generate_key(question_title, question_content)
            data['cached_at'] = datetime.utcnow().isoformat()
            data['policy'] = self.policy
            
            # Aplicar política de remoción antes de insertar
            self._apply_eviction_policy()
            
            # Almacenar según política
            if self.policy == 'TTL':
                success = self.redis_client.setex(cache_key, self.cache_ttl, json.dumps(data))
            elif self.policy == 'LRU':
                success = self.redis_client.set(cache_key, json.dumps(data))
            else:  # TTL-LRU
                success = self.redis_client.setex(cache_key, self.cache_ttl, json.dumps(data))
            
            if success:
                self.metrics['sets'] += 1
                logger.debug(f"Cache SET: {question_title[:50]}...")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error almacenando cache: {e}")
            return False
    
    def _apply_eviction_policy(self):
        """Aplicar política de remoción según configuración"""
        try:
            current_size = self.redis_client.dbsize()
            
            if current_size >= self.max_cache_size:
                keys = self.redis_client.keys('*')
                
                if len(keys) >= self.max_cache_size:
                    evict_count = max(1, int(len(keys) * 0.1))  # Remover 10%
                    
                    if self.policy == 'LRU':
                        # Política LRU: remover claves menos accedidas recientemente
                        keys_with_access = []
                        for key in keys:
                            ttl = self.redis_client.ttl(key)
                            keys_with_access.append((key, ttl))
                        
                        # Ordenar por TTL ascendente (menos recientes)
                        keys_with_access.sort(key=lambda x: x[1])
                        keys_to_remove = [k[0] for k in keys_with_access[:evict_count]]
                        reason = 'LRU_POLICY'
                        
                    elif self.policy == 'TTL':
                        # Política TTL: remover claves que expiran primero
                        keys_with_ttl = []
                        for key in keys:
                            ttl = self.redis_client.ttl(key)
                            if ttl > 0:
                                keys_with_ttl.append((key, ttl))
                        
                        keys_with_ttl.sort(key=lambda x: x[1])
                        keys_to_remove = [k[0] for k in keys_with_ttl[:evict_count]]
                        reason = 'TTL_POLICY'
                        
                    else:  # TTL-LRU
                        # Política combinada: TTL + LRU
                        keys_with_score = []
                        for key in keys:
                            ttl = self.redis_client.ttl(key)
                            # Score combinado: menor TTL + factor aleatorio para LRU
                            score = ttl if ttl > 0 else 999999
                            keys_with_score.append((key, score))
                        
                        keys_with_score.sort(key=lambda x: x[1])
                        keys_to_remove = [k[0] for k in keys_with_score[:evict_count]]
                        reason = 'TTL_LRU_POLICY'
                    
                    # Ejecutar remoción
                    removed = 0
                    for key in keys_to_remove:
                        if self.redis_client.delete(key):
                            removed += 1
                    
                    self.metrics['evictions'] += removed
                    self.metrics['eviction_reasons'].append({
                        'timestamp': datetime.now().isoformat(),
                        'reason': reason,
                        'count': removed,
                        'cache_size_before': current_size
                    })
                    
                    logger.info(f"Evicción {reason}: {removed} claves removidas")
                    
        except Exception as e:
            logger.error(f"Error aplicando política de evicción: {e}")
    
    def _record_hit(self, start_time, cache_key):
        """Registrar cache hit con métricas"""
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        self.metrics['hits'] += 1
        self.metrics['hit_times'].append(response_time)
        logger.debug(f"CACHE HIT ({response_time:.2f}ms): {cache_key[:16]}...")
    
    def _record_miss(self, start_time):
        """Registrar cache miss con métricas"""
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        self.metrics['misses'] += 1
        self.metrics['miss_times'].append(response_time)
    
    def get_detailed_metrics(self) -> Dict[str, Any]:
        """Obtener métricas detalladas para análisis"""
        total_ops = self.metrics['total_operations']
        runtime = (datetime.now() - self.metrics['start_time']).total_seconds()
        
        # Calcular estadísticas de tiempo
        avg_hit_time = sum(self.metrics['hit_times']) / len(self.metrics['hit_times']) if self.metrics['hit_times'] else 0
        avg_miss_time = sum(self.metrics['miss_times']) / len(self.metrics['miss_times']) if self.metrics['miss_times'] else 0
        
        # Información actual del cache
        current_size = 0
        memory_usage = 0
        if self.redis_client:
            try:
                current_size = self.redis_client.dbsize()
                info = self.redis_client.info('memory')
                memory_usage = info.get('used_memory', 0)
            except:
                pass
        
        return {
            # Métricas básicas
            'policy_type': self.policy,
            'cache_size_limit': self.max_cache_size,
            'current_cache_size': current_size,
            'runtime_seconds': runtime,
            
            # Contadores
            'total_operations': total_ops,
            'hits': self.metrics['hits'],
            'misses': self.metrics['misses'],
            'sets': self.metrics['sets'],
            'evictions': self.metrics['evictions'],
            
            # Ratios
            'hit_rate_percent': (self.metrics['hits'] / total_ops * 100) if total_ops > 0 else 0,
            'miss_rate_percent': (self.metrics['misses'] / total_ops * 100) if total_ops > 0 else 0,
            'eviction_rate_percent': (self.metrics['evictions'] / total_ops * 100) if total_ops > 0 else 0,
            
            # Tiempos de respuesta
            'avg_hit_time_ms': round(avg_hit_time, 2),
            'avg_miss_time_ms': round(avg_miss_time, 2),
            
            # Eficiencia
            'cache_efficiency': (self.metrics['hits'] / (self.metrics['hits'] + self.metrics['misses']) * 100) if (self.metrics['hits'] + self.metrics['misses']) > 0 else 0,
            'memory_usage_bytes': memory_usage,
            
            # Detalles de evicción
            'eviction_history': self.metrics['eviction_reasons'][-10:] if self.metrics['eviction_reasons'] else []
        }
    
    def reset_metrics(self):
        """Reiniciar métricas manteniendo configuración"""
        policy = self.metrics['policy_type']
        cache_size = self.metrics['cache_size_limit']
        
        self.metrics = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'sets': 0,
            'total_operations': 0,
            'policy_type': policy,
            'cache_size_limit': cache_size,
            'start_time': datetime.now(),
            'hit_times': [],
            'miss_times': [],
            'eviction_reasons': []
        }
        logger.info(f"Métricas reiniciadas para política {policy}")
    
    def clear_cache(self):
        """Limpiar cache completamente"""
        if self.redis_client:
            try:
                self.redis_client.flushdb()
                self.reset_metrics()
                logger.info("Cache limpiado completamente")
            except Exception as e:
                logger.error(f"Error limpiando cache: {e}")


class CacheAnalyzer:
    """Analizador comparativo de políticas de cache"""
    
    def __init__(self):
        self.results = {}
        
    def compare_policies(self, cache_sizes=[500, 1000, 2000], policies=['LRU', 'TTL', 'TTL-LRU']):
        """Comparar diferentes políticas y tamaños de cache"""
        logger.info("Iniciando análisis comparativo de políticas de cache")
        
        for policy in policies:
            for size in cache_sizes:
                key = f"{policy}_{size}"
                cache = CacheManager(policy=policy, cache_size=size)
                
                # Simular carga de trabajo
                self._simulate_workload(cache, iterations=1000)
                
                # Obtener métricas
                metrics = cache.get_detailed_metrics()
                self.results[key] = metrics
                
                logger.info(f"Completado: {policy} con tamaño {size}")
                cache.clear_cache()
        
        return self.results
    
    def _simulate_workload(self, cache, iterations=1000):
        """Simular carga de trabajo con patrones de acceso realistas"""
        import random
        
        # Conjunto de preguntas simuladas
        questions = [
            f"¿Pregunta frecuente {i}?" for i in range(50)  # Preguntas frecuentes
        ] + [
            f"¿Pregunta rara {i}?" for i in range(200)  # Preguntas raras
        ]
        
        # Pesos para simular patrón 80/20 (Principio de Pareto)
        weights = [0.8/50] * 50 + [0.2/200] * 200
        
        for i in range(iterations):
            question = random.choices(questions, weights=weights)[0]
            
            # Buscar en cache
            result = cache.get(question, f"contenido {i % 100}")
            
            if result is None:
                # Cache miss: simular respuesta LLM
                fake_response = {
                    'llm_answer': f'Respuesta simulada para {question}',
                    'quality_score': random.uniform(0.5, 1.0),
                    'timestamp': datetime.now().isoformat()
                }
                cache.set(question, f"contenido {i % 100}", fake_response)
    
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
