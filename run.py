#!/usr/bin/env python3
"""
Script Principal - Sistema de Análisis LLM
==========================================

Punto de entrada para el sistema de análisis de Yahoo Answers usando APIs remotas de LLM.
"""

import asyncio
import logging
import sys
import os
from analyzer import main

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('analysis.log')
    ]
)

logger = logging.getLogger(__name__)

def main_entry():
    """Punto de entrada principal"""
    logger.info("=== INICIANDO SISTEMA DE ANÁLISIS LLM ===")
    logger.info("Usando APIs remotas para máxima velocidad")
    
    try:
        # Verificar variables de entorno para Docker
        if os.getenv('POSTGRES_HOST'):
            logger.info("Ejecutando en modo Docker")
        else:
            logger.info("Ejecutando en modo local")
        
        # Ejecutar análisis
        asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("Análisis interrumpido por usuario")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error crítico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main_entry()
