from sentence_transformers import SentenceTransformer
from pack.postgres_utils import PostgresUtils
import os, time, psycopg2

pg_params = {
    "host":     os.getenv("PG_HOST"),
    "port":     os.getenv("PG_PORT"),
    "dbname":   os.getenv("PG_DB"),
    "user":     os.getenv("PG_USER"),
    "password": os.getenv("PG_PASSWORD"),
}

db = PostgresUtils(pg_params)
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

def vectorizar_todas_las_preguntas():
    conn = db.connect()
    cur  = conn.cursor()
    cur.execute("SELECT id, pregunta FROM preguntas_frecuentes")
    rows = cur.fetchall()

    for faq_id, pregunta in rows:
        embedding = model.encode(pregunta)
        db.insert_embedding_faq(faq_id, embedding)
        print(f"✅ Vector insertado para FAQ ID {faq_id}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    # Retry en caso de que la tabla tarde en crearse
    for intento in range(5):
        try:
            vectorizar_todas_las_preguntas()
            break
        except psycopg2.errors.UndefinedTable:
            print(f"⏳ Tabla no disponible, reintentando {intento+1}/5 en 3s…")
            time.sleep(3)
