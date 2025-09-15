#!/usr/bin/env python3
"""
Script para cargar datos CSV en la base de datos PostgreSQL dockerizada
"""

import pandas as pd
import psycopg2
from sqlalchemy import create_engine
import sys
import os

def main():
    print("=== CARGANDO DATOS EN BASE DE DATOS DOCKERIZADA ===")
    
    # Configuración de base de datos
    DATABASE_CONFIG = {
        'host': 'localhost',
        'port': 5432,
        'database': 'yahoo_answers',
        'user': 'postgres',
        'password': 'postgres123'
    }
    
    # Archivo CSV
    csv_file = 'train.csv'
    
    if not os.path.exists(csv_file):
        print(f"❌ Error: No se encuentra el archivo {csv_file}")
        return
    
    try:
        print(f"📂 Leyendo archivo CSV: {csv_file}")
        # El CSV no tiene headers, definimos los nombres de columnas
        column_names = ['original_class', 'question_title', 'question_content', 'original_answer']
        df = pd.read_csv(csv_file, names=column_names, header=None)
        print(f"✅ Archivo leído: {len(df)} registros")
        
        # Mostrar información del dataset
        print(f"📋 Columnas: {list(df.columns)}")
        print(f"📋 Ejemplo de datos:")
        print(df.head(2).to_string())
        
        # Crear conexión
        connection_string = f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"
        engine = create_engine(connection_string)
        
        print("🔌 Conectando a PostgreSQL...")
        
        # Limpiar datos nulos
        df = df.fillna('')
        
        # Limitar a un subconjunto para testing (puedes cambiar este número)
        # Para pruebas iniciales, usemos solo 10,000 registros
        if len(df) > 10000:
            print(f"🔄 Limitando a 10,000 registros para prueba inicial (total disponible: {len(df)})")
            df = df.head(10000)
        
        print(f"💾 Insertando {len(df)} registros en la base de datos...")
        
        # Insertar en lotes para mejor rendimiento
        batch_size = 1000
        total_inserted = 0
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            batch.to_sql('questions', engine, if_exists='append', index=False, method='multi')
            total_inserted += len(batch)
            print(f"📈 Progreso: {total_inserted}/{len(df)} registros insertados")
        
        print(f"✅ ¡Datos cargados exitosamente! Total: {total_inserted} registros")
        
        # Verificar inserción
        with engine.connect() as conn:
            result = conn.execute("SELECT COUNT(*) FROM questions")
            count = result.fetchone()[0]
            print(f"🔍 Verificación: {count} registros en la tabla questions")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return
    
    print("✅ ¡Proceso completado!")

if __name__ == "__main__":
    main()
