#!/usr/bin/env python3
"""
Script para cargar una muestra pequeña de datos para prueba rápida
"""

import pandas as pd
import psycopg2
from sqlalchemy import create_engine
import sys

def main():
    print("=== CARGA RÁPIDA DE PRUEBA ===")
    
    # Configuración de base de datos
    DATABASE_CONFIG = {
        'host': 'localhost',
        'port': 5432,
        'database': 'yahoo_answers',
        'user': 'postgres',
        'password': 'postgres123'
    }
    
    try:
        print("📂 Leyendo 100 registros del CSV...")
        # Leer solo 100 registros para prueba
        column_names = ['original_class', 'question_title', 'question_content', 'original_answer']
        df = pd.read_csv('train.csv', names=column_names, header=None, nrows=100)
        print(f"✅ Leídos: {len(df)} registros")
        
        # Crear conexión
        connection_string = f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"
        engine = create_engine(connection_string)
        
        print("🔌 Conectando a PostgreSQL...")
        
        # Limpiar datos nulos
        df = df.fillna('')
        
        print(f"💾 Insertando {len(df)} registros...")
        
        # Insertar todos los registros
        df.to_sql('questions', engine, if_exists='append', index=False, method='multi')
        
        print(f"✅ ¡Datos cargados exitosamente! Total: {len(df)} registros")
        
        # Verificar inserción
        with engine.connect() as conn:
            result = conn.execute("SELECT COUNT(*) FROM questions")
            count = result.fetchone()[0]
            print(f"🔍 Verificación: {count} registros en la tabla questions")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    print("✅ ¡Proceso completado!")

if __name__ == "__main__":
    main()