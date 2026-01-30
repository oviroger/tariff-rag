#!/usr/bin/env python3
import requests
import json
import uuid

url = "http://localhost:8000/classify"
conv_id = str(uuid.uuid4())

query = "es lavadora carga frontal, 8kg, con secado"
resp = requests.post(url, json={"conversation_id": conv_id, "query": query})

print(f"Status: {resp.status_code}")
print(f"Response: {json.dumps(resp.json(), indent=2)}")
