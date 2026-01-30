import requests
import json

API_URL = 'http://localhost:8000'

print('='*80)
print('PRUEBA COMPLETA DEL CHATBOT - microondas')
print('='*80)
print()

# Step 1: Classify
print('[PASO 1] Clasificando "microondas"...')
print('-' * 80)
classify_resp = requests.post(f'{API_URL}/classify', json={'user_query': 'microondas'})

if classify_resp.status_code == 200:
    classify_data = classify_resp.json()
    conv_id = classify_data.get('conversation_id')
    top_candidates = classify_data.get('top_candidates', [])
    evidence = classify_data.get('evidence', [])
    
    print('[OK] Clasificacion exitosa!')
    print(f'  Conversation ID: {conv_id}')
    print()
    
    if top_candidates:
        print('Top Candidatos:')
        for i, cand in enumerate(top_candidates[:3], 1):
            print(f'  {i}. Codigo HS: {cand.get("code")}')
            print(f'     Descripcion: {cand.get("description")}')
            print(f'     Confianza: {cand.get("confidence")}')
            print(f'     Anos: {cand.get("years")}')
            print()
    
    print('Evidencia utilizada:')
    for i, ev in enumerate(evidence[:5], 1):
        print(f'  {i}. Score: {ev.get("score", 0):.6f}')
        print(f'     Unit: {ev.get("unit")} | Year: {ev.get("year")} | Bucket: {ev.get("bucket")}')
        print(f'     Text: {ev.get("text", "")[:100]}...')
        print()
    
    print('='*80)
    print('VERIFICACIONES CLAVE:')
    print('='*80)
    
    # Check 1: HS Code encontrado
    has_hs = len(top_candidates) > 0
    print(f'[{"OK" if has_hs else "FAIL"}] HS Code encontrado: {top_candidates[0]["code"] if has_hs else "N/A"}')
    
    # Check 2: Confianza > 0
    confidence = top_candidates[0].get("confidence", 0) if top_candidates else 0
    print(f'[{"OK" if confidence > 0 else "FAIL"}] Confianza: {confidence}')
    
    # Check 3: Fuentes incluyen tabla
    has_table = any(e.get('unit') == 'table' for e in evidence)
    print(f'[{"OK" if has_table else "FAIL"}] Incluye datos de TABLA (fix aplicado!)')
    
    # Check 4: Ambos años
    years = top_candidates[0].get("years", []) if top_candidates else []
    has_both_years = 2025 in years and 2026 in years
    print(f'[{"OK" if has_both_years else "WARN"}] Disponible en ambos anos: {years}')
    
    # Check 5: Evidencia de v2
    table_evidence = [e for e in evidence if e.get('unit') == 'table']
    if table_evidence:
        print(f'[OK] Evidencia de tabla encontrada:')
        for te in table_evidence[:1]:
            print(f'     Fragment ID: {te.get("fragment_id")}')
            print(f'     Bucket: {te.get("bucket")}')
            print(f'     Year: {te.get("year")}')
    
    print()
    print('='*80)
    print('RESUMEN:')
    print('='*80)
    checks = [has_hs, confidence > 0, has_table, has_both_years]
    passed = sum(checks)
    print(f'Verificaciones: {passed}/4 pasadas')
    
    if has_table and has_hs and confidence > 0:
        print('[EXITO COMPLETO] El fix de microondas funciona correctamente!')
        print('  - Se extraen datos de tablas')
        print('  - Se clasifican con confianza > 0')
        print('  - Indices v2 estan operativos')
    else:
        print('[ATENCION] Revisar configuracion')
    
else:
    print(f'[ERROR] Clasificacion fallo: {classify_resp.status_code}')
    print(classify_resp.text)

print('='*80)
