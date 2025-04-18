#==== pack/tools_dulcetentacion.py ====

from sentence_transformers import SentenceTransformer
from langchain_core.tools import tool
from pack.postgres_utils import PostgresUtils
from datetime import datetime 
import os

# Configuración
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

pg_params = {
    'host': os.getenv('PG_HOST'),
    'port': os.getenv('PG_PORT'),
    'dbname': os.getenv('PG_DB'),
    'user': os.getenv('PG_USER'),
    'password': os.getenv('PG_PASSWORD')
}

db = PostgresUtils(pg_params)

# ──────────────────────────────────────────────
# 2.  Tools
# ──────────────────────────────────────────────
@tool
def consultar_faq(pregunta: str) -> dict:
    """
    Busca la FAQ más parecida.
    ▸ Si la encuentra → {"tipo":"faq","ok":True,"respuesta":…}
    ▸ Si no → {"tipo":"faq","ok":False,"mensaje":…}
    """
    texto = db.consultar_y_sumar_frecuencia(pregunta, model)
    if texto:
        return {"tipo": "faq", "ok": True, "respuesta": texto}
    return {
        "tipo": "faq",
        "ok": False,
        "mensaje": "❌ No encontré una pregunta similar. Puedes preguntarme de otra forma.",
    }

@tool
def consultar_stock_producto(nombre: str) -> dict:
    """
    Devuelve disponibilidad y precio de un producto.  
    ▸ Si existe y hay stock → ok=True  
    ▸ Si existe pero está agotado → ok=False + mensaje  
    ▸ Si no existe → ok=False + mensaje
    """
    conn = db.connect()
    cur  = conn.cursor()
    cur.execute(
        """
        SELECT nombre, precio, stock
        FROM productos
        WHERE LOWER(nombre) LIKE LOWER(%s)
        LIMIT 1
        """,
        (f"%{nombre}%",),
    )
    row = cur.fetchone()
    cur.close(); conn.close()

    if not row:
        return {
            "tipo": "stock",
            "ok":   False,
            "mensaje": "❌ Producto no encontrado.",
        }

    prod, precio, stock = row
    if stock > 0:

        db.insert_log_interaction(
        pregunta_usuario=f"Disponibilidad {prod}",
        intencion_detectada="consulta_stock",
        id_producto=None,          # si tienes PK pásala aquí
        respuesta_generada=f"Stock {stock}",
        fuente_respuesta="Producto",
        canal="Web",
    )
        return {
            "tipo": "stock",
            "ok":   True,
            "nombre": prod,
            "precio": precio,
            "stock":  stock,
        }

    return {
        "tipo": "stock",
        "ok":   False,
        "mensaje": f"⚠️ El producto '{prod}' está agotado en este momento.",
    }


@tool
def listar_productos() -> dict:
    """
    Devuelve un catálogo resumido (máx. 20).  
    Siempre: {"tipo":"catálogo","productos":[…]}
    """
    conn = db.connect()
    cur  = conn.cursor()
    cur.execute(
        """
        SELECT nombre, precio, stock
        FROM productos
        WHERE stock > 0
        ORDER BY nombre
        LIMIT 20
        """
    )
    filas = cur.fetchall()
    cur.close(); conn.close()

    return {
        "tipo": "catálogo",
        "productos": [
            {"nombre": n, "precio": p, "stock": s} for n, p, s in filas
        ],
    }


@tool
def describir_producto(nombre: str) -> dict:
    """
    Devuelve el detalle de un producto.  
    Si no existe: {"tipo":"detalle_producto","encontrado":False,"mensaje":…}
    """
    conn = db.connect()
    cur  = conn.cursor()
    cur.execute(
        """
        SELECT nombre, descripcion, precio, stock
        FROM productos
        WHERE LOWER(nombre) LIKE LOWER(%s)
        LIMIT 1
        """,
        (f"%{nombre}%",),
    )
    row = cur.fetchone()
    cur.close(); conn.close()

    if not row:
        return {
            "tipo": "detalle_producto",
            "encontrado": False,
            "mensaje": "❌ Producto no encontrado.",
        }

    n, d, p, s = row
    return {
        "tipo": "detalle_producto",
        "encontrado": True,
        "producto": {"nombre": n, "descripcion": d, "precio": p, "stock": s},
    }



def evaluar_y_sumar_frecuencia_si_corresponde(pregunta: str, threshold_bajo=0.5, threshold_alto=0.75) -> str | None:
    """
    Evalúa si la pregunta se parece a una FAQ:
    - Si es muy parecida, retorna la respuesta y suma frecuencia.
    - Si es medianamente parecida, solo suma frecuencia.
    """
    embedding = model.encode(pregunta)
    resultado = db.get_most_similar_faq(embedding, threshold=threshold_bajo)

    if resultado:
        faq_id, pregunta_faq, respuesta, intencion, frecuencia, score = resultado
        if score >= threshold_bajo:
            db.aumentar_frecuencia(faq_id)
        if score >= threshold_alto:
            return respuesta
    return None

