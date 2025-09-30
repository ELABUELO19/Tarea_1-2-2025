#!/usr/bin/env python3
"""
Servicio LLM Simulado (Dummy) para Testing y Desarrollo
Genera respuestas simuladas basadas en el contenido de las preguntas sin APIs externas.
"""

import asyncio
import logging
import random
import time
import hashlib
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class DummyLLMService:
    """
    Servicio LLM simulado que genera respuestas realistas sin APIs externas.
    
    Características:
    - Respuestas basadas en keywords del contenido de la pregunta
    - Simulación de múltiples modelos con diferentes características
    - Tiempos de respuesta realistas
    - Scores de calidad variables y realistas
    - Sin dependencias externas ni tokens API
    """
    
    # Configuración de modelos simulados
    DUMMY_MODELS = {
        "gpt-4o": {
            "id": "gpt-4o",
            "provider": "OpenAI",
            "context_length": 128000,
            "cost_tier": "premium",
            "strengths": ["reasoning", "coding", "analysis", "multimodal"],
            "avg_response_time": 0.05,  # ULTRA-RÁPIDO: 50ms
            "quality_range": (2.3, 3.0),  # rango de scores de calidad
            "response_style": "detailed"
        },
        "gpt-4o-mini": {
            "id": "gpt-4o-mini", 
            "provider": "OpenAI",
            "context_length": 128000,
            "cost_tier": "economy",
            "strengths": ["general", "cost-effective", "speed"],
            "avg_response_time": 0.02,  # ULTRA-RÁPIDO: 20ms
            "quality_range": (2.0, 2.8),
            "response_style": "concise"
        },
        "mistral-nemo": {
            "id": "mistral-nemo",
            "provider": "Mistral",
            "context_length": 128000,
            "cost_tier": "standard",
            "strengths": ["multilingual", "reasoning", "cost-effective"],
            "avg_response_time": 0.03,  # ULTRA-RÁPIDO: 30ms
            "quality_range": (2.1, 2.9),
            "response_style": "balanced"
        }
    }
    
    # Templates de respuestas por categoría de pregunta
    RESPONSE_TEMPLATES = {
        "technology": [
            "Basándome en {topic}, puedo explicar que {explanation}. Es importante considerar {considerations}.",
            "La tecnología {topic} funciona mediante {mechanism}. Sus principales ventajas incluyen {benefits}.",
            "Para entender {topic}, es crucial conocer {fundamentals}. Esto se aplica especialmente en {applications}."
        ],
        "science": [
            "Desde una perspectiva científica, {topic} se basa en {principles}. Los estudios muestran que {findings}.",
            "El fenómeno de {topic} ocurre debido a {causes}. Las investigaciones indican {evidence}.",
            "En el campo científico, {topic} es fundamental porque {importance}. Esto se manifiesta en {examples}."
        ],
        "general": [
            "Respecto a {topic}, es importante mencionar que {key_point}. Además, {additional_info}.",
            "La pregunta sobre {topic} tiene varios aspectos relevantes: {aspects}. En particular, {specific_detail}.",
            "Para abordar {topic}, debemos considerar {factors}. Esto nos lleva a {conclusion}."
        ],
        "how_to": [
            "Para {action}, el proceso general incluye: {steps}. Es recomendable {recommendations}.",
            "La mejor manera de {action} es {method}. Ten en cuenta que {considerations}.",
            "Si quieres {action}, sigue estos pasos: {procedure}. Recuerda {tips}."
        ],
        "definition": [
            "{term} se define como {definition}. Sus características principales son {characteristics}.",
            "El concepto de {term} se refiere a {meaning}. Esto implica {implications}.",
            "Podemos entender {term} como {explanation}. Su importancia radica en {significance}."
        ]
    }
    
    def __init__(self, selected_models: Optional[List[str]] = None):
        """
        Inicializa el servicio LLM simulado.
        
        Args:
            selected_models: Lista de modelos a simular. Si None, usa todos los disponibles.
        """
        self.available_models = list(self.DUMMY_MODELS.keys())
        
        if selected_models is None:
            selected_models = self.available_models
        
        # Filtrar solo modelos disponibles
        self.selected_models = [m for m in selected_models if m in self.DUMMY_MODELS]
        
        if not self.selected_models:
            logger.warning("Ningún modelo válido seleccionado. Usando todos los disponibles.")
            self.selected_models = self.available_models
        
        self.initialized = True
        logger.info(f"DummyLLM inicializado con modelos: {', '.join(self.selected_models)}")
    
    def _categorize_question(self, question_title: str, question_content: str = "") -> str:
        """
        Categoriza la pregunta basándose en palabras clave para generar respuestas más apropiadas.
        """
        full_text = f"{question_title} {question_content}".lower()
        
        # Palabras clave por categoría
        tech_keywords = ["software", "computer", "programming", "code", "app", "website", "internet", "digital", "technology", "tech"]
        science_keywords = ["science", "biology", "chemistry", "physics", "research", "study", "experiment", "theory", "scientific"]
        how_to_keywords = ["how to", "how do", "how can", "steps", "tutorial", "guide", "instruction", "method"]
        definition_keywords = ["what is", "what are", "define", "definition", "meaning", "explain", "concept"]
        
        if any(keyword in full_text for keyword in how_to_keywords):
            return "how_to"
        elif any(keyword in full_text for keyword in definition_keywords):
            return "definition"
        elif any(keyword in full_text for keyword in tech_keywords):
            return "technology"
        elif any(keyword in full_text for keyword in science_keywords):
            return "science"
        else:
            return "general"
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extrae palabras clave relevantes del texto de la pregunta.
        """
        # Palabras comunes a filtrar
        stop_words = {"the", "is", "at", "which", "on", "a", "an", "and", "or", "but", "in", "with", "to", "for", "of", "as", "by"}
        
        words = text.lower().split()
        keywords = [word.strip(".,?!:;") for word in words if len(word) > 3 and word not in stop_words]
        
        # Retornar las 3-5 palabras más relevantes
        return keywords[:5]
    
    def _generate_realistic_content(self, question_title: str, question_content: str, model_name: str) -> str:
        """
        Genera contenido de respuesta realista OPTIMIZADO - versión ultra-rápida.
        """
        # Extracción simple de keywords (primera palabra significativa)
        words = question_title.lower().split()
        topic = next((w for w in words if len(w) > 3), "tema")
        
        # Templates ultra-simples por modelo
        model_info = self.DUMMY_MODELS[model_name]
        
        if model_info["response_style"] == "detailed":
            response = f"Respecto a {topic}, es importante considerar varios aspectos fundamentales. Esta pregunta involucra elementos técnicos específicos que requieren análisis detallado y consideración de múltiples variables para una comprensión completa."
        elif model_info["response_style"] == "concise":
            response = f"En relación con {topic}, la respuesta implica factores específicos que deben evaluarse según el contexto y los objetivos planteados."
        else:  # balanced
            response = f"Sobre {topic}, podemos explicar que involucra varios conceptos importantes que se interrelacionan de manera específica según las circunstancias."
        
        return response
    
    def _calculate_deterministic_score(self, question_title: str, model_name: str) -> float:
        """
        Calcula score ULTRA-RÁPIDO usando hash simple.
        """
        # Hash ultra-simple y rápido
        hash_val = hash(f"{question_title}{model_name}") % 1000
        
        # Ranges simplificados por modelo
        ranges = {
            "gpt-4o": (2.3, 3.0),
            "gpt-4o-mini": (2.0, 2.8),
            "mistral-nemo": (2.1, 2.9)
        }
        
        min_score, max_score = ranges.get(model_name, (2.0, 2.8))
        score = min_score + ((hash_val / 1000.0) * (max_score - min_score))
        
        return round(score, 2)
    
    async def generate_answer_with_model(self, question_title: str, model_name: str,
                                       question_content: str = "") -> Optional[Tuple[str, Dict]]:
        """
        Genera una respuesta simulada usando un modelo específico.
        
        Args:
            question_title: Título de la pregunta
            model_name: Nombre del modelo a simular
            question_content: Contenido adicional de la pregunta
            
        Returns:
            Tuple de (respuesta, metadata) o None si hay error
        """
        if model_name not in self.DUMMY_MODELS:
            logger.error(f"Modelo {model_name} no disponible en DummyLLM")
            return None
        
        model_info = self.DUMMY_MODELS[model_name]
        
        try:
            start_time = time.time()
            
            # Simular tiempo de respuesta realista del modelo
            base_time = model_info["avg_response_time"]
            variation = random.uniform(0.8, 1.2)  # Variación del ±20%
            simulated_time = base_time * variation
            await asyncio.sleep(0.001)  # ULTRA-RÁPIDO: solo 1ms para simular procesamiento
            
            # Generar respuesta basada en contenido
            answer = self._generate_realistic_content(question_title, question_content, model_name)
            
            elapsed_time = time.time() - start_time
            
            # Score determinista basado en la pregunta y modelo
            quality_score = self._calculate_deterministic_score(question_title, model_name)
            
            # Metadata realista
            metadata = {
                "model": model_name,
                "provider": model_info["provider"],
                "response_time": elapsed_time,
                "token_count": len(answer.split()),
                "cost_tier": model_info["cost_tier"],
                "simulated": True
            }
            
            logger.debug(f"DummyLLM {model_name}: {len(answer)} chars, score={quality_score}, time={elapsed_time:.2f}s")
            return answer, metadata
            
        except Exception as e:
            logger.error(f"Error en DummyLLM {model_name}: {e}")
            return None
    
    async def generate_multi_model_answers(self, question_title: str, 
                                         question_content: str = "") -> Dict[str, Tuple[str, Dict]]:
        """
        Genera respuestas simuladas usando todos los modelos seleccionados.
        
        Args:
            question_title: Título de la pregunta
            question_content: Contenido adicional de la pregunta
            
        Returns:
            Diccionario con respuestas de cada modelo
        """
        results = {}
        
        # Generar respuestas secuencialmente (simula rate limiting)
        for model_name in self.selected_models:
            try:
                result = await self.generate_answer_with_model(question_title, model_name, question_content)
                if result:
                    results[model_name] = result
                
                # SIN DELAY para máxima velocidad
                # await asyncio.sleep(0.2)  # ELIMINADO para optimización
                
            except Exception as e:
                logger.error(f"Error con modelo simulado {model_name}: {e}")
                continue
        
        return results
    
    async def evaluate_model_comparison(self, question: str, answers: Dict[str, str]) -> Dict[str, float]:
        """
        Evalúa y compara la calidad de respuestas simuladas de múltiples modelos.
        Usa algoritmo determinista basado en características de los modelos.
        
        Args:
            question: Pregunta original
            answers: Diccionario de respuestas por modelo
            
        Returns:
            Diccionario de scores por modelo
        """
        scores = {}
        
        for model_name, answer in answers.items():
            if model_name in self.DUMMY_MODELS:
                # Score determinista basado en pregunta + modelo
                score = self._calculate_deterministic_score(question, model_name)
                scores[model_name] = score
            else:
                scores[model_name] = 2.0  # Default score
        
        return scores
    
    async def process_question_multi_model(self, question_title: str, question_content: str) -> Dict:
        """
        Procesa una pregunta con múltiples modelos simulados y proporciona análisis comparativo.
        
        Args:
            question_title: Título de la pregunta
            question_content: Contenido de la pregunta
            
        Returns:
            Diccionario completo con respuestas, metadata y evaluaciones
        """
        # Generar respuestas con todos los modelos
        model_results = await self.generate_multi_model_answers(question_title, question_content)
        
        if not model_results:
            return {}
        
        # Extraer respuestas para evaluación
        answers = {model: result[0] for model, result in model_results.items()}
        
        # Evaluar calidad comparativa
        quality_scores = await self.evaluate_model_comparison(
            f"{question_title}\n{question_content or ''}",
            answers
        )
        
        # Compilar resultado completo
        final_results = {}
        for model, (answer, metadata) in model_results.items():
            final_results[model] = {
                "answer": answer,
                "metadata": metadata,
                "quality_score": quality_scores.get(model, 2.0),
                "provider": metadata["provider"],
                "cost_tier": metadata["cost_tier"]
            }
        
        return final_results
    
    def get_model_info(self, model_name: str) -> Dict:
        """Obtiene información detallada de un modelo simulado."""
        return self.DUMMY_MODELS.get(model_name, {})
    
    def list_available_models(self) -> List[Dict]:
        """Lista todos los modelos simulados disponibles con su información."""
        return [
            {
                "name": name,
                **info,
                "simulated": True
            }
            for name, info in self.DUMMY_MODELS.items()
        ]
    
    def is_available(self) -> bool:
        """Verifica si el servicio DummyLLM está disponible (siempre True)."""
        logger.info(f"✅ DummyLLM Service verificado ({len(self.selected_models)} modelos simulados)")
        return True


# Función para crear instancia con modelos personalizados
def create_dummy_llm_service(model_names: List[str] = None) -> DummyLLMService:
    """
    Crea una instancia del servicio LLM simulado con modelos específicos.
    
    Args:
        model_names: Lista de nombres de modelos a simular
        
    Returns:
        Instancia configurada del servicio simulado
    """
    return DummyLLMService(selected_models=model_names)


# Instancia por defecto con modelos balanceados
dummy_llm_service = DummyLLMService()