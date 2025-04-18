"""
dulcebot.py  –  Chainlit + LangGraph + Gemini
Ordenado, comentado y sin imports redundantes.
No se ha tocado el prompt original ni la lógica principal.
"""

# ═════════════════════════════════════════════════════════════════════════════
# 1.  Imports y entorno
# ═════════════════════════════════════════════════════════════════════════════
import os
import re
import json
from typing import Annotated, Literal

import chainlit as cl
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.schema.runnable.config import RunnableConfig

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from pack import*
import os

# claves (en prod, usa variables de entorno seguras)
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
os.environ["LANGCHAIN_TRACING_V2"] = "false"

# ═════════════════════════════════════════════════════════════════════════════
# 2.  Tools y modelo LLM
# ═════════════════════════════════════════════════════════════════════════════
TOOLS = [
    consultar_faq,
    consultar_stock_producto,
    listar_productos,
    describir_producto,
]

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0.4,
    top_p=0.9,
).bind_tools(TOOLS)  # se mantiene bind_tools para no alterar comportamiento

final_llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0.4,
    top_p=0.95,
)

tool_node = ToolNode(tools=TOOLS)

# ═════════════════════════════════════════════════════════════════════════════
# 3.  Prompt del sistema (sin cambios)
# ═════════════════════════════════════════════════════════════════════════════
SYSTEM_PROMPT = SystemMessage(content="""
Eres **DulceBot**, asistente virtual de **DulceTentación S.A.S.**
Tu personalidad: cercana, entusiasta, un punto juguetona — pero profesional. Siempre en español.

Guías operativas:
• Si la duda coincide con una FAQ → llama a consultar_faq (retorna una string).
• Si el usuario menciona un producto concreto → llama a consultar_stock_producto (retorna una string).
• Si pide catálogo, productos o sabores generales → llama a listar_productos (retorna un objeto JSON con {"tipo": "catálogo", "productos": [...]}).
• Si el usuario quiere detalles de un producto → llama a describir_producto (retorna un objeto JSON con {"tipo": "detalle_producto", "producto": {...}}).

Siempre debes:
• Analizar si debes llamar una herramienta.
• Usar los datos tal como vienen, sin inventar.
• Incorporar el resultado en la respuesta con Markdown si es útil.
• Cerrar con: «¿Te ayudo en algo más?»
• Si la herramienta devuelve un mensaje con ⚠️ o ❌, díselo al usuario de forma amable.
• Usa emojis moderados (🍰, 😊, ✅, ⚠️).
• Siempre trata de mostrar todo de manera decente, bonita y no en formato json.
""")

# ═════════════════════════════════════════════════════════════════════════════
# 4.  Estado y nodo agent
# ═════════════════════════════════════════════════════════════════════════════
class State(MessagesState):
    messages: Annotated[list, add_messages]

def call_model(state: State):
    """Nodo agent: llama a Gemini con historial + prompt del sistema."""
    history = state["messages"]
    ai_msg = llm.invoke([SYSTEM_PROMPT] + history)
    return {"messages": [ai_msg]}

# ═════════════════════════════════════════════════════════════════════════════
# 5.  Helpers de formato y cordialidad
# ═════════════════════════════════════════════════════════════════════════════
def _catalogo_a_tabla(productos: list[dict]) -> str:
    header = "| Producto | Precio |\n|----------|--------|\n"
    rows = "\n".join(f"| {p['nombre']} | ${p['precio']:,.0f} |" for p in productos)
    return header + rows

def _rewrite_as_cordial(msg: AIMessage):
    """Re‑escribe la respuesta anterior en tono cordial (último recurso)."""
    if not msg.content or not msg.content.strip():
        msg.content = (
            "⚠️ Lo siento, no pude generar una respuesta. "
            "¿Podrías reformular tu pregunta?"
        )
        return {"messages": [msg]}

    instr = (
        "Reescribe la respuesta anterior con un tono cordial y amable, "
        "usa Markdown si es útil y finaliza con «¿Te ayudo en algo más?». "
        "No inventes datos nuevos."
    )
    new_msg = final_llm.invoke([SYSTEM_PROMPT, msg, HumanMessage(content=instr)])
    new_msg.id = msg.id
    return {"messages": [new_msg]}

# ═════════════════════════════════════════════════════════════════════════════
# 6.  Nodo final: formatea la salida de las tools
# ═════════════════════════════════════════════════════════════════════════════
def call_final_model(state: State):
    last_ai: AIMessage = state["messages"][-1]

    # Si no viene de una tool, solo re‑escribimos si hace falta
    if not getattr(last_ai, "tool_calls", None):
        return _rewrite_as_cordial(last_ai)

    data = last_ai.additional_kwargs.get("tool_output") or {}
    if not data:
        try:
            data = json.loads(re.sub(r"```json|```", "", last_ai.content))
        except Exception:
            pass

    tipo = data.get("tipo")

    if tipo == "faq":
        respuesta = data.get("respuesta") or data.get("mensaje")
        last_ai.content = f"💬 {respuesta}\n\n¿Te ayudo en algo más?"
        return {"messages": [last_ai]}

    if tipo == "catálogo":
        prods = data.get("productos", [])
        last_ai.content = (
            "⚠️ Actualmente no hay productos disponibles."
            if not prods
            else (
                "¡Con gusto! Este es nuestro catálogo actual 🍰:\n\n"
                f"{_catalogo_a_tabla(prods)}\n\n¿Te ayudo en algo más?"
            )
        )
        return {"messages": [last_ai]}

    if tipo == "detalle_producto":
        if not data.get("encontrado", False):
            last_ai.content = data.get("mensaje", "❌ Producto no encontrado.")
        else:
            p = data["producto"]
            last_ai.content = (
                "🍰 **Detalles del producto**\n\n"
                f"**{p['nombre']}** — {p['descripcion']}\n"
                f"Precio: ${p['precio']:,.0f} COP\n"
                f"Stock: {p['stock']} unidades\n\n¿Te ayudo en algo más?"
            )
        return {"messages": [last_ai]}

    if tipo == "stock":
        texto = data.get("nombre") and (
            f"✅ El producto '{data['nombre']}' está disponible por "
            f"${data['precio']:,.0f} COP (stock {data['stock']} unidades)."
        ) or data.get("mensaje")
        last_ai.content = f"{texto}\n\n¿Te ayudo en algo más?"
        return {"messages": [last_ai]}

    return _rewrite_as_cordial(last_ai)

# ═════════════════════════════════════════════════════════════════════════════
# 7.  Lógica para decidir si pasar por tools
# ═════════════════════════════════════════════════════════════════════════════
KEYWORDS_STOCK = [
    "stock", "disponible", "productos", "catálogo", "precio", "precios",
    "sabores", "sabor", "descríbeme", "describe",
]
KEYWORDS_FAQ = [
    "formas de pago", "pago", "pagos", "horario", "envíos",
    "domicilio", "dónde están", "ubicados", "sin azúcar",
    "pedido", "cómo pido",
]

def should_continue(state: State) -> Literal["tools", "final"]:
    """Heurística sencilla para decidir si invocar herramientas."""
    last = state["messages"][-1]

    # Gemini solicitó tool
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tools"

    # Ya es ToolMessage
    if hasattr(last, "name") and getattr(last, "tool_call_id", None):
        return "tools"

    # Reglas por palabras clave
    if isinstance(last, HumanMessage):
        txt = last.content.lower()
        if re.search(r"\b(describe|descríbeme|descríbelo|descríbela)\b", txt):
            return "tools"
        if any(k in txt for k in KEYWORDS_STOCK + KEYWORDS_FAQ):
            return "tools"

    return "final"

# ═════════════════════════════════════════════════════════════════════════════
# 8.  Construcción del grafo
# ═════════════════════════════════════════════════════════════════════════════
builder = StateGraph(State)
builder.add_node("agent", call_model)
builder.add_node("tools", tool_node)
builder.add_node("final", call_final_model)

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", should_continue)
builder.add_edge("tools", "agent")  # mantiene flujo original
builder.add_edge("final", END)

graph = builder.compile(checkpointer=MemorySaver())

# ═════════════════════════════════════════════════════════════════════════════
# 9.  Chainlit
# ═════════════════════════════════════════════════════════════════════════════
@cl.on_chat_start
async def on_chat_start():
    await cl.Message(content="""
        ✨ Hola, soy **DulceBot**, tu asistente de **DulceTentación S.A.S.**

        Estoy aquí para ayudarte con preguntas sobre nuestros productos, formas de pago, tiempos de entrega o sabores disponibles.

        Puedes preguntarme cosas como:
        - ¿Qué sabores de cheesecake tienen hoy?
        - ¿Cuánto cuesta un brownie?
        - ¿Hacen entregas en Cali?
    """).send()

@cl.on_message
async def on_message(msg: cl.Message):
    cfg = {"configurable": {"thread_id": cl.context.session.id}}
    cb  = cl.LangchainCallbackHandler()
    out = cl.Message(content="")

    try:
        # 1️⃣  intento rápido con embeddings (FAQ)
        faq = evaluar_y_sumar_frecuencia_si_corresponde(msg.content)
        if faq:
            r = llm.invoke(
                [
                    SYSTEM_PROMPT,
                    HumanMessage(
                        content=(
                            f"Información base: «{faq}»\n"
                            f"Pregunta: «{msg.content}»\n\n"
                            "Responde con calidez sin inventar datos."
                        )
                    ),
                ]
            )
            await cl.Message(r.content).send()
            return
        
        # 2️⃣  Flujo LangGraph
        for resp, meta in graph.stream(
            {"messages": [HumanMessage(content=msg.content)]},
            stream_mode="messages",
            config=RunnableConfig(callbacks=[cb], **cfg),
        ):
            if (
                meta.get("langgraph_node") == "final"
                and resp.content
                and not isinstance(resp, HumanMessage)
            ):
                await out.stream_token(resp.content)
        await out.send()

    except Exception as err:
        error_msg = traceback.format_exc()
        db.registrar_error(error_msg)
        print("❌ Error:", err)
        await cl.Message(
            "❌ Lo siento, ocurrió un error. Intenta de nuevo o contacta soporte."
        ).send()
