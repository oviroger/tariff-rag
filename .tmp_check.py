import requests, json
API = "http://localhost:8000/classify"
conversation_history = []

def call(query):
    payload = {"user_query": query, "top_k": 5, "conversation_history": conversation_history}
    r = requests.post(API, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    subset = {k: data.get(k) for k in ["top_candidates", "missing_fields", "warnings"]}
    print("\n---")
    print("Query:", query)
    print(json.dumps(subset, ensure_ascii=False, indent=2))
    conversation_history.append({"user": query, "assistant": "resp"})

call("¿Cuál es la partida arancelaria de los vehículos?")
call("es una motocicleta")
call("es electrica")
