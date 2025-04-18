import requests

url = "http://localhost:8000/preguntar"

# Lista de preguntas simuladas por Fernando
preguntas = [
    "Hola, soy Fernando. ¿Tienen opción sin azúcar o sin lactosa?",
    "Hola, me llamo Fernando. ¿Puedo programar un pedido para una hora específica?",
]

for pregunta in preguntas:
    print(f"\n🔹 Enviando pregunta: {pregunta}")
    response = requests.post(url, json={"pregunta": pregunta})

    if response.ok:
        data = response.json()
        print("✅ Respuesta:")
        print(f"→ {data['respuesta']}")
        print(f"   (tipo: {data['tipo']}, fuente: {data['fuente']})")
    else:
        print("❌ Error:", response.status_code)
        print(response.text)
