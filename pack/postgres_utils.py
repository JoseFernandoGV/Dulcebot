#====postgres_utils.py====
import psycopg2
from psycopg2.extras import execute_values
import numpy as np
import traceback

class PostgresUtils:
    def __init__(self, pg_params):
        self.pg_params = pg_params

    def connect(self):
        conn = psycopg2.connect(**self.pg_params)
        return conn

    def insert_user(self, name, encoding):
        """
        Inserta un nuevo usuario con su encoding facial en la base de datos.
        """
        conn = self.connect()
        cur = conn.cursor()
        query = "INSERT INTO face_encodings (name, encoding) VALUES (%s, %s)"
        cur.execute(query, (name, encoding.tolist()))
        conn.commit()
        cur.close()
        conn.close()
        print(f"Usuario '{name}' insertado correctamente.")

    def insert_embedding_faq(self, faq_id, embedding):
        """
        Inserta o actualiza el vector embedding en la tabla preguntas_frecuentes.
        """
        conn = self.connect()
        cur = conn.cursor()

        # Asegúrate que sea una lista de float (PostgreSQL vector(384))
        vector_str = "[" + ",".join([str(round(float(x), 6)) for x in embedding]) + "]"

        query = """
        UPDATE preguntas_frecuentes
        SET embedding = %s
        WHERE id = %s
        """
        cur.execute(query, (vector_str, faq_id))
        conn.commit()
        cur.close()
        conn.close()

    def get_most_similar_faq(self, embedding, top_k=1, threshold=0.7):
        """
        Devuelve la pregunta más similar al embedding dado.
        Usa distancia euclidiana con el operador <=>.
        """
        conn = self.connect()
        cur = conn.cursor()

        vector_str = "[" + ",".join([str(round(float(x), 6)) for x in embedding]) + "]"

        query = f"""
        SELECT id, pregunta, respuesta, intencion, frecuencia,
               1 - (embedding <=> %s) AS similarity
        FROM preguntas_frecuentes
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s
        LIMIT {top_k};
        """

        cur.execute(query, (vector_str, vector_str))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        # Retornar solo si pasa el umbral de similaridad
        if rows and rows[0][-1] >= threshold:
            return rows[0]  # devuelve la fila más parecida
        return None
    
    def consultar_y_sumar_frecuencia(self, pregunta_usuario, model, threshold=0.7):
        """
        Vectoriza la pregunta, encuentra la FAQ más cercana, incrementa la frecuencia
        y devuelve un dict con respuesta + metadatos.  Si no hay coincidencia → None.
        """
        embedding = model.encode(pregunta_usuario)
        res = self.get_most_similar_faq(embedding, threshold=threshold)

        if not res:
            return None

        faq_id, pregunta_faq, respuesta, intencion, _, score = res

        # Sumar frecuencia
        conn = self.connect()
        with conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE preguntas_frecuentes SET frecuencia = frecuencia + 1 WHERE id=%s",
                (faq_id,),
            )

        return {
            "respuesta": respuesta,
            "id_faq": faq_id,
            "intencion": intencion,
            "score": score,
        }

    def aumentar_frecuencia(self, faq_id):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("UPDATE preguntas_frecuentes SET frecuencia = frecuencia + 1 WHERE id = %s", (faq_id,))
        conn.commit()
        cur.close()
        conn.close()


    def insert_log_interaction(
        self,
        pregunta_usuario: str,
        *,
        intencion_detectada: str | None = None,
        id_pregunta_frecuente: int | None = None,
        id_producto: int | None = None,
        respuesta_generada: str | None = None,
        fuente_respuesta: str | None = None,
        canal: str | None = None,
    ):
        """
        Crea un registro en la tabla logs_interacciones.
        """
        conn = self.connect()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO logs_interacciones
            (pregunta_usuario,intencion_detectada,id_pregunta_frecuente,
            id_producto,respuesta_generada,fuente_respuesta,canal)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                pregunta_usuario,
                intencion_detectada,
                id_pregunta_frecuente,
                id_producto,
                respuesta_generada,
                fuente_respuesta,
                canal,
            ),
        )
        conn.commit()
        cur.close()
        conn.close()

    def registrar_error(self, descripcion: str):
        """
        Registra un error en la tabla logs_errores con la fecha actual.
        """
        try:
            conn = self.connect()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO logs_errores (descripcion)
                VALUES (%s)
                """,
                (descripcion,)
            )
            conn.commit()
            cur.close()
            conn.close()
        except Exception as err:
            print(f"❌ Error al registrar en logs_errores: {err}")
