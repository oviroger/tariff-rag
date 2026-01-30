import requests
import json

API_URL = 'http://localhost:8000'

print('='*70)
print('PRUEBA COMPLETA DEL CHATBOT - microondas')
print('='*70)
print()

# Step 1: Classify
print('[STEP 1] Clasificando microondas...')
classify_resp = requests.post(f'{API_URL}/classify', json={'user_query': 'microondas'})
if classify_resp.status_code == 200:
    classify_data = classify_resp.json()
    conv_id = classify_data.get('conversation_id')
    print(f'OK - Conversation ID: {conv_id}')
    print(f'  - Categoria: {classify_data.get("category", "N/A")}')
    print(f'  - HS Code: {classify_data.get("hs_code", "N/A")}')
    print(f'  - Confianza: {classify_data.get("confidence", "N/A")}')
    print()
    
    # Step 2: Chat
    print('[STEP 2] Consultando arancel...')
    payload = {
        'question': 'cual es el arancel?',
        'previous_result': classify_data,
        'conversation_id': conv_id
    }
    chat_resp = requests.post(f'{API_URL}/chat', json=payload)
    if chat_resp.status_code == 200:
        chat_data = chat_resp.json()
        print(f'OK - Respuesta:')
        print(chat_data.get('answer', 'N/A')[:500])
        print()
        print(f'Metadata:')
        meta = chat_data.get('metadata', {})
        print(f'  - HS Code: {meta.get("hs_code", "N/A")}')
        print(f'  - Confianza: {meta.get("confidence", "N/A")}')
        print()
        sources = chat_data.get('sources', [])
        print(f'Fuentes: {len(sources)}')
        for i, src in enumerate(sources[:3], 1):
            print(f'  {i}. Score: {src.get("score", 0):.4f} | Unit: {src.get("unit", "N/A")} | Year: {src.get("year", "N/A")}')
        print()
        print('='*70)
        print('VERIFICACIONES:')
        print('='*70)
        has_table = any(s.get('unit') == 'table' for s in sources)
        print(f'[{"OK" if chat_data.get("answer") else "FAIL"}] Respuesta generada')
        print(f'[{"OK" if has_table else "WARN"}] Fuentes incluyen datos de tablas')
        print(f'[{"OK" if meta.get("confidence", 0) > 0 else "FAIL"}] Confianza > 0')
        print(f'[{"OK" if meta.get("hs_code") else "WARN"}] HS Code detectado')
    else:
        print(f'ERROR - Chat failed: {chat_resp.status_code}')
        print(chat_resp.text)
else:
    print(f'ERROR - Classify failed: {classify_resp.status_code}')
    print(classify_resp.text)
