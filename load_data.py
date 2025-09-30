#!/usr/bin/env python3
"""
Script para cargar datos CSV en la base de datos PostgreSQL
Ejecuta automáticamente en Docker
"""

import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text
import sys
import os
import time

def wait_for_postgres(max_retries=30):
    """Esperar a que PostgreSQL esté disponible"""
    config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': 5432,
        'database': os.getenv('POSTGRES_DB', 'yahoo_answers'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', 'postgres123')
    }
    
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(**config)
            conn.close()
            print(f"PostgreSQL está disponible")
            return True
        except psycopg2.OperationalError:
            print(f"Esperando PostgreSQL... intento {attempt + 1}/{max_retries}")
            time.sleep(2)
    
    return False

def main():
    print("=== CARGADOR DE DATOS AUTOMATICO ===")
    
    if not wait_for_postgres():
        print("Error: No se pudo conectar a PostgreSQL")
        sys.exit(1)
    
    # Configuración de base de datos
    DATABASE_CONFIG = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': 5432,
        'database': os.getenv('POSTGRES_DB', 'yahoo_answers'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', 'postgres123')
    }
    
    # Parámetros de conexión para psycopg2
    conn_params = {
        'host': DATABASE_CONFIG['host'],
        'port': DATABASE_CONFIG['port'],
        'database': DATABASE_CONFIG['database'],
        'user': DATABASE_CONFIG['user'],
        'password': DATABASE_CONFIG['password']
    }
    
    csv_file = 'train.csv'
    
    if not os.path.exists(csv_file):
        print(f"Error: No se encuentra el archivo {csv_file}")
        sys.exit(1)
    
    try:
        print(f"Leyendo archivo CSV: {csv_file}")
        column_names = ['original_class', 'question_title', 'question_content', 'original_answer']
        df = pd.read_csv(csv_file, names=column_names, header=None)
        print(f"Archivo leído: {len(df)} registros")
        
        # Crear conexión
        connection_string = f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"
        engine = create_engine(connection_string)
        
        print("Conectando a PostgreSQL...")
        
        # Crear conexión directa para verificación inicial
        try:
            # Verificar con psycopg2 directamente
            with psycopg2.connect(**conn_params) as pg_conn:
                with pg_conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM questions")
                    existing_count = cursor.fetchone()[0]
                    print(f"Registros existentes en la base de datos: {existing_count}")
        
        except Exception as e:
            print(f"Error al verificar la base de datos: {str(e)}")
            sys.exit(1)
            
        if existing_count > 0:
            print(f"La base de datos ya contiene {existing_count} registros")
            print("Saltando carga de datos")
            return
        
        # Limpiar datos nulos
        df = df.fillna('')
        
        # Limitar para pruebas del sistema de cache
        if len(df) > 5000:
            print(f"Limitando a 5,000 registros para análisis de cache (total disponible: {len(df)})")
            df = df.head(5000)
        
        print(f"Insertando {len(df)} registros en la base de datos...")
        
        # Insertar en lotes
        batch_size = 1000
        total_inserted = 0
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            batch.to_sql('questions', engine, if_exists='append', index=False, method='multi')
            total_inserted += len(batch)
            print(f"Progreso: {total_inserted}/{len(df)} registros insertados")
        
        print(f"Datos cargados exitosamente: {total_inserted} registros")
        
        # Verificar inserción
        with psycopg2.connect(**conn_params) as pg_conn:
            with pg_conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM questions")
                count = cursor.fetchone()[0]
                print(f"Verificación: {count} registros en la tabla questions")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    
    print("Proceso de carga completado")

if __name__ == "__main__":
    main()
