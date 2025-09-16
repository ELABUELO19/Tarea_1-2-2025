"""
Analizador LLM Remoto
====================
Analizador principal usando APIs remotas de LLM con fallback automático.
"""

import asyncio
import logging
import time
import pandas as pd
from typing import Dict, List, Optional

from database import PostgreSQLManager, Question
from cache_manager import CacheManager
from remote_llm_service import MultipleLLMService

logger = logging.getLogger(__name__)

class LLMAnalyzer:
    """Analizador principal con APIs remotas de LLM"""
    
    def __init__(self, dataset_path: str = 'train.csv'):
        self.dataset_path = dataset_path
        self.db = PostgreSQLManager()
        self.cache = CacheManager()
        self.llm_service = MultipleLLMService()
        
        # Estadísticas
        self.stats = {
            "total_processed": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "cache_hits": 0,
            "start_time": None,
            "end_time": None
        }
        
        logger.info("LLM Analyzer inicializado")
    
    async def analyze_question_quality(self, question_title: str, question_content: str) -> Dict:
        """Analizar calidad de una pregunta usando LLM remoto"""
        # Crear clave de cache
        content_for_cache = f"{question_title}_{question_content}"
        cache_key = f"llm_quality:{hash(content_for_cache)}"
        
        # Verificar cache
        cached_result = self.cache.get(cache_key)
        if cached_result:
            self.stats["cache_hits"] += 1
            return {"quality": cached_result, "provider": "cache", "cached": True}
        
        # Analizar con LLM
        try:
            result = await self.llm_service.analyze_with_fallbacks(question_title, question_content)
            
            if result.get("quality"):
                # Guardar en cache usando los parámetros correctos
                self.cache.set(
                    question_title, 
                    question_content, 
                    result
                )
                self.stats["successful_analyses"] += 1
                return result
            else:
                self.stats["failed_analyses"] += 1
                return {"error": "No se pudo analizar la calidad"}
                
        except Exception as e:
            logger.error(f"Error en análisis LLM: {e}")
            self.stats["failed_analyses"] += 1
            return {"error": str(e)}
    
    async def process_batch(self, questions: List[Question], semaphore: asyncio.Semaphore):
        """Procesar un lote de preguntas"""
        tasks = []
        
        for question in questions:
            task = self._process_single_question(question, semaphore)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    async def _process_single_question(self, question: Question, semaphore: asyncio.Semaphore):
        """Procesar una pregunta individual"""
        async with semaphore:
            try:
                # Analizar calidad
                result = await self.analyze_question_quality(
                    question.question_title, 
                    question.question_content or ""
                )
                
                if result.get("quality"):
                    # Convertir calidad a score numérico
                    quality_map = {"ALTA": 3.0, "MEDIA": 2.0, "BAJA": 1.0}
                    quality_score = quality_map.get(result["quality"], 1.0)
                    
                    # Actualizar en base de datos
                    session = self.db.get_session()
                    try:
                        # CORREGIDO: Merge el objeto question a la nueva sesión
                        merged_question = session.merge(question)
                        merged_question.quality_score = quality_score
                        merged_question.llm_answer = f"Calidad: {result['quality']} (Provider: {result.get('provider', 'unknown')})"
                        session.commit()
                        
                        self.stats["total_processed"] += 1
                        logger.info(f"Procesado ID {merged_question.id}: {result['quality']}")
                        
                    except Exception as e:
                        session.rollback()
                        logger.error(f"Error guardando ID {merged_question.id}: {e}")
                    finally:
                        session.close()
                
                return {"id": question.id, "status": "success", "quality": result.get("quality")}
                
            except Exception as e:
                logger.error(f"Error procesando ID {question.id}: {e}")
                return {"id": question.id, "status": "error", "error": str(e)}
    
    async def run_analysis(self, max_questions: int = 12000, batch_size: int = 50, max_concurrent: int = 10):
        """Ejecutar análisis completo"""
        logger.info("=== INICIANDO ANÁLISIS LLM REMOTO ===")
        logger.info(f"Objetivo: {max_questions:,} consultas máximo")
        
        self.stats["start_time"] = time.time()
        
        # Obtener preguntas sin procesar
        session = self.db.get_session()
        try:
            unprocessed = session.query(Question).filter(
                Question.quality_score == 0.0
            ).limit(max_questions).all()
            
            total_to_process = len(unprocessed)
            logger.info(f"Encontradas {total_to_process:,} preguntas para procesar")
            
            if total_to_process == 0:
                logger.info("No hay preguntas pendientes para procesar")
                return
            
            # Procesar en lotes
            semaphore = asyncio.Semaphore(max_concurrent)
            processed = 0
            
            for i in range(0, total_to_process, batch_size):
                batch = unprocessed[i:i + batch_size]
                
                logger.info(f"Procesando lote {i//batch_size + 1}: preguntas {i+1}-{min(i+batch_size, total_to_process)}")
                
                # Procesar lote
                batch_results = await self.process_batch(batch, semaphore)
                
                # Reportar progreso
                processed += len(batch)
                elapsed = time.time() - self.stats["start_time"]
                rate = processed / elapsed if elapsed > 0 else 0
                
                logger.info(f"Progreso: {processed}/{total_to_process} ({processed/total_to_process*100:.1f}%) - {rate:.2f} q/s")
                
                # Pequeña pausa entre lotes
                await asyncio.sleep(0.1)
        
        finally:
            session.close()
        
        self.stats["end_time"] = time.time()
        self._report_final_stats()
    
    def _report_final_stats(self):
        """Generar reporte final de estadísticas"""
        duration = self.stats["end_time"] - self.stats["start_time"]
        
        logger.info("=" * 50)
        logger.info("=== REPORTE FINAL ===")
        logger.info("=" * 50)
        logger.info(f"Tiempo total: {duration:.2f} segundos")
        logger.info(f"Preguntas procesadas: {self.stats['total_processed']:,}")
        logger.info(f"Análisis exitosos: {self.stats['successful_analyses']:,}")
        logger.info(f"Análisis fallidos: {self.stats['failed_analyses']:,}")
        logger.info(f"Cache hits: {self.stats['cache_hits']:,}")
        
        if duration > 0:
            rate = self.stats['total_processed'] / duration
            logger.info(f"Velocidad promedio: {rate:.2f} preguntas/segundo")
        
        # Estadísticas de proveedores LLM
        if hasattr(self.llm_service, 'primary_llm'):
            llm_stats = self.llm_service.primary_llm.get_stats()
            logger.info("\n--- ESTADÍSTICAS LLM ---")
            for provider, data in llm_stats.items():
                logger.info(f"{provider}: {data['requests']} requests, {data['success_rate']:.1f}% éxito")
        
        logger.info("=" * 50)
        logger.info("=== ANÁLISIS COMPLETADO ===")

async def main():
    """Función principal"""
    analyzer = LLMAnalyzer('train.csv')
    
    try:
        await analyzer.run_analysis(
            max_questions=12000,
            batch_size=50,
            max_concurrent=10
        )
    except KeyboardInterrupt:
        logger.info("Análisis interrumpido por usuario")
    except Exception as e:
        logger.error(f"Error durante análisis: {e}")
        raise

if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('llm_analysis.log')
        ]
    )
    
    asyncio.run(main())
