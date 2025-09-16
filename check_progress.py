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

# Verificar columnas
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'questions' ORDER BY ordinal_position")
columns = [row[0] for row in cur.fetchall()]
print(f"Columnas disponibles: {columns}")

# Verificar total de registros
cur.execute("SELECT COUNT(*) FROM questions")
total = cur.fetchone()[0]
print(f"Total registros: {total}")

# Verificar registros con algún campo de respuesta
cur.execute("SELECT COUNT(*) FROM questions WHERE llm_answer IS NOT NULL")
processed = cur.fetchone()[0]
print(f"Registros procesados: {processed}")

# Ver últimos procesamientos
cur.execute("SELECT id, question_title, llm_answer, quality_score FROM questions WHERE llm_answer IS NOT NULL ORDER BY id DESC LIMIT 5")
recent = cur.fetchall()
print("\nÚltimos procesamientos:")
for row in recent:
    print(f"ID {row[0]}: {row[1][:30]}... | LLM: {str(row[2])[:20]}... | Score: {row[3]}")

conn.close()