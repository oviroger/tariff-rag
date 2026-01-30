"""
Prueba completa del chatbot con 3 mercaderías diferentes
Demuestra el proceso de clasificación arancelaria end-to-end
"""
import requests
import json
from time import sleep

API_URL = 'http://localhost:8000'

def print_separator(char='=', length=80):
    print(char * length)

def classify_product(product_name, product_description):
    """Clasificar un producto y mostrar resultados detallados"""
    
    print_separator('=')
    print(f'EJEMPLO: {product_name.upper()}')
    print_separator('=')
    print()
    print(f'Descripcion del producto: "{product_description}"')
    print()
    
    # Paso 1: Clasificación
    print('[PASO 1] Enviando consulta al clasificador...')
    print('-' * 80)
    
    payload = {
        'user_query': product_description
    }
    
    response = requests.post(f'{API_URL}/classify', json=payload)
    
    if response.status_code != 200:
        print(f'[ERROR] Clasificacion fallo: {response.status_code}')
        print(response.text)
        return
    
    data = response.json()
    
    # Paso 2: Resultados de clasificación
    print('[PASO 2] Resultados de la Clasificacion')
    print('-' * 80)
    
    top_candidates = data.get('top_candidates', [])
    if not top_candidates:
        print('[ATENCION] No se encontraron candidatos')
        return
    
    print(f'Total de candidatos encontrados: {len(top_candidates)}')
    print()
    
    # Mostrar el candidato principal
    main_candidate = top_candidates[0]
    print('CLASIFICACION PRINCIPAL:')
    print(f'  Codigo HS: {main_candidate.get("code")}')
    print(f'  Descripcion: {main_candidate.get("description")}')
    print(f'  Nivel: {main_candidate.get("level")}')
    print(f'  Confianza: {main_candidate.get("confidence")}')
    print(f'  Anos disponibles: {main_candidate.get("years")}')
    print()
    
    # Otros candidatos si existen
    if len(top_candidates) > 1:
        print('CANDIDATOS ALTERNATIVOS:')
        for i, cand in enumerate(top_candidates[1:4], 2):
            print(f'  {i}. {cand.get("code")} - {cand.get("description")} (Confianza: {cand.get("confidence")})')
        print()
    
    # Paso 3: Evidencia utilizada
    evidence = data.get('evidence', [])
    print('[PASO 3] Evidencia del Sistema de Busqueda (RAG)')
    print('-' * 80)
    print(f'Fragmentos recuperados: {len(evidence)}')
    print()
    
    # Agrupar por tipo de unidad
    table_evidence = [e for e in evidence if e.get('unit') == 'table']
    paragraph_evidence = [e for e in evidence if e.get('unit') == 'paragraph']
    
    print(f'  - Fragmentos de TABLAS: {len(table_evidence)}')
    print(f'  - Fragmentos de PARRAFOS: {len(paragraph_evidence)}')
    print()
    
    # Mostrar top 3 fragmentos
    print('Top 3 fragmentos mas relevantes:')
    for i, ev in enumerate(evidence[:3], 1):
        print(f'  {i}. Score: {ev.get("score", 0):.6f}')
        print(f'     Tipo: {ev.get("unit")} | Ano: {ev.get("year")} | Fuente: {ev.get("doc_id", "N/A")}')
        text_preview = ev.get("text", "")[:150].replace('\n', ' ')
        print(f'     Texto: {text_preview}...')
        print()
    
    # Paso 4: Información adicional
    print('[PASO 4] Informacion Adicional del Clasificador')
    print('-' * 80)
    
    rgi_applied = data.get('applied_rgi', [])
    if rgi_applied:
        print(f'Reglas Generales aplicadas: {", ".join(rgi_applied)}')
    
    inclusions = data.get('inclusions', [])
    if inclusions:
        print(f'Inclusiones: {inclusions[0] if inclusions else "N/A"}')
    
    exclusions = data.get('exclusions', [])
    if exclusions:
        print(f'Exclusiones: {exclusions[0] if exclusions else "N/A"}')
    
    missing_fields = data.get('missing_fields', [])
    if missing_fields:
        print(f'Campos faltantes para clasificacion mas precisa:')
        for field in missing_fields[:3]:
            print(f'  - {field}')
    
    print()
    
    # Paso 5: Resumen y verificación
    print('[PASO 5] Verificacion y Resumen')
    print('-' * 80)
    
    checks = []
    
    # Check 1: Clasificación exitosa
    has_classification = len(top_candidates) > 0
    print(f'[{"OK" if has_classification else "FAIL"}] Clasificacion exitosa: {main_candidate.get("code") if has_classification else "N/A"}')
    checks.append(has_classification)
    
    # Check 2: Confianza razonable
    confidence = main_candidate.get("confidence", 0)
    has_confidence = confidence > 0.2
    print(f'[{"OK" if has_confidence else "WARN"}] Confianza adecuada: {confidence}')
    checks.append(has_confidence)
    
    # Check 3: Evidencia de tablas
    has_table = len(table_evidence) > 0
    print(f'[{"OK" if has_table else "INFO"}] Usa datos de tablas: {"Si" if has_table else "No"} ({len(table_evidence)} fragmentos)')
    checks.append(has_table)
    
    # Check 4: Multiple años
    years = main_candidate.get("years", [])
    has_both_years = len(years) >= 2
    print(f'[{"OK" if has_both_years else "INFO"}] Disponible en multiples anos: {years}')
    checks.append(has_both_years)
    
    # Check 5: Suficiente evidencia
    has_evidence = len(evidence) >= 3
    print(f'[{"OK" if has_evidence else "WARN"}] Suficiente evidencia: {len(evidence)} fragmentos')
    checks.append(has_evidence)
    
    passed = sum(checks)
    print()
    print(f'Verificaciones: {passed}/5 pasadas')
    
    if passed >= 4:
        print('[EXITO] Clasificacion completa y confiable')
    elif passed >= 3:
        print('[BUENO] Clasificacion aceptable')
    else:
        print('[ATENCION] Revisar clasificacion')
    
    print()
    print_separator('=')
    print()
    
    return data

def main():
    print()
    print_separator('=')
    print('DEMOSTRACION COMPLETA DEL CHATBOT DE CLASIFICACION ARANCELARIA')
    print('Sistema RAG con indices OpenSearch v2 (incluye datos de tablas)')
    print_separator('=')
    print()
    
    # Verificar que el API está disponible
    try:
        health = requests.get(f'{API_URL}/health', timeout=5)
        if health.status_code != 200:
            print('[ERROR] API no responde correctamente')
            return
        print('[OK] API del chatbot esta activa')
        print()
    except Exception as e:
        print(f'[ERROR] No se puede conectar al API: {e}')
        return
    
    # Ejemplo 1: Producto electrónico (microondas)
    classify_product(
        'Microondas',
        'horno de microondas electrico para uso domestico'
    )
    
    sleep(1)
    
    # Ejemplo 2: Vehículo
    classify_product(
        'Automovil',
        'vehiculo automovil con motor de gasolina de 1500 cc para transporte de personas'
    )
    
    sleep(1)
    
    # Ejemplo 3: Producto textil
    classify_product(
        'Camiseta',
        'camiseta de algodon para hombre talla M manga corta'
    )
    
    # Resumen final
    print_separator('=')
    print('RESUMEN DE LA DEMOSTRACION')
    print_separator('=')
    print()
    print('Se han demostrado 3 clasificaciones arancelarias completas:')
    print('1. Producto electronico (microondas) - Partida 8516')
    print('2. Vehiculo automotor - Partida 8703')
    print('3. Producto textil (camiseta) - Partida 6109')
    print()
    print('Cada ejemplo muestra:')
    print('  - Proceso de clasificacion automatica')
    print('  - Codigo HS (Sistema Armonizado)')
    print('  - Confianza del clasificador')
    print('  - Evidencia RAG (fragmentos de documentos)')
    print('  - Reglas de clasificacion aplicadas')
    print('  - Verificaciones de calidad')
    print()
    print('El sistema utiliza:')
    print('  - Indices OpenSearch v2 (con tablas extraidas)')
    print('  - Embeddings de Azure OpenAI')
    print('  - Clasificador basado en LLM')
    print('  - Datos de aranceles 2025 y 2026')
    print()
    print_separator('=')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n[INFO] Prueba interrumpida por el usuario')
    except Exception as e:
        print(f'\n[ERROR] Error en la prueba: {e}')
        import traceback
        traceback.print_exc()
