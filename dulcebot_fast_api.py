from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pack.postgres_utils import PostgresUtils
from sentence_transformers import SentenceTransformer
from langchain_google_genai import ChatGoogleGenerativeAI
import os

# Configuración
os.environ["GOOGLE_API_KEY"] = "AIzaSyCasCTKEAwgPOLGmB0fR0O6MEOMs5-E4gQ"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
pg_params = {
    'host': 'localhost',
    'port': '5433',
    'dbname': 'postgres',
    'user': 'postgres',
    'password': 'test123'
}

db = PostgresUtils(pg_params)
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# FastAPI app
app = FastAPI()

class PreguntaRequest(BaseModel):
    pregunta: str

@app.post("/preguntar")
def preguntar(data: PreguntaRequest):
    try:
        embedding = model.encode(data.pregunta)
        resultado = db.get_most_similar_faq(embedding, threshold=0.5)

        if resultado:
            faq_id, pregunta_faq, respuesta, intencion, _, score = resultado
            if score >= 0.75:
                db.aumentar_frecuencia(faq_id)

                # Uso de LLM
                llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
                r = llm.invoke([
                                f"""
                                Eres DulceBot, un asistente virtual que responde en nombre de DulceTentación S.A.S.
                                Tu tarea es responder de forma directa, amigable y clara a preguntas de clientes reales.

                                Responde **solo una vez**, sin dar múltiples opciones, y sin actuar como una guía.
                                Usa un tono cálido, profesional y enfocado en ayudar al cliente. Puedes usar Markdown si es útil.

                                Información base: «{respuesta}»
                                Pregunta del cliente: «{data.pregunta}»

                                Tu respuesta:
                                """
                                ])
                db.insert_log_interaction(
                    pregunta_usuario=data.pregunta,
                    intencion_detectada=intencion,
                    id_pregunta_frecuente=faq_id,
                    respuesta_generada=r.content,
                    fuente_respuesta="FAQ + LLM",
                    canal="API"
                )

                return {
                    "respuesta": r.content,
                    "intencion": intencion,
                    "tipo": "faq",
                    "fuente": "semántico + generativo"
                }

        # Si no hay FAQ similar, solo usa el LLM
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
        r = llm.invoke([f"Pregunta: {data.pregunta}"])
        db.insert_log_interaction(
            pregunta_usuario=data.pregunta,
            respuesta_generada=r.content,
            fuente_respuesta="LLM puro",
            canal="API"
        )

        return {
            "respuesta": r.content,
            "tipo": "generativo",
            "fuente": "LLM puro"
        }

    except Exception as e:
        db.registrar_error(str(e))
        raise HTTPException(status_code=500, detail="Ocurrió un error procesando tu solicitud.")
