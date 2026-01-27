#!/usr/bin/env python
import requests
import json

params = {'query': 'es un bus para 50 pasajeros', 'conversation_history': []}
try:
    resp = requests.post('http://localhost:8000/api/classify', json=params, timeout=30)
    print(f'Status: {resp.status_code}')
    print(f'Response length: {len(resp.content)} bytes')
    
    if resp.status_code == 200:
        data = resp.json()
        print(f'Top code: {data["top_candidates"][0]["code"]}')
        print(f'Confidence: {data["top_candidates"][0]["confidence"]:.1%}')
        print(f'Missing fields: {len(data["missing_fields"])}')
        for field in data["missing_fields"]:
            print(f'  - {field}')
    else:
        print(f'Response: {resp.text[:500]}')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
