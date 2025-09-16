#!/usr/bin/env python3
import psycopg2

conn = psycopg2.connect(
    host='localhost', 
    port=5432, 
    database='yahoo_answers', 
    user='postgres', 
    password='postgres123'
)

cur = conn.cursor()

# Prueba de actualización manual
cur.execute("UPDATE questions SET quality_score = 2.0, llm_answer = 'Prueba manual' WHERE id = 4487")
affected = cur.rowcount
conn.commit()
print(f"Filas afectadas: {affected}")

# Verificar resultado
cur.execute("SELECT id, quality_score, llm_answer FROM questions WHERE id = 4487")
row = cur.fetchone()
print(f"Verificación: ID {row[0]}, Score: {row[1]}, Answer: {row[2]}")

# Resetear el valor
cur.execute("UPDATE questions SET quality_score = 0.0, llm_answer = NULL WHERE id = 4487")
conn.commit()
print("Valor reseteado para permitir reprocesamiento")

conn.close()