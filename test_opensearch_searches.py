import requests
import json

# Test diferentes tipos de búsquedas para "vehículo"
print("=" * 80)
print("TESTING DIFFERENT SEARCHES FOR 'VEHÍCULO'")
print("=" * 80)

base_url = 'http://localhost:9200/tariff_fragments_2025_v2/_search'

# 1. Simple match
print("\n1. SIMPLE MATCH 'vehículo':")
search_body = {
    "query": {"match": {"text": "vehículo"}},
    "size": 10
}
response = requests.post(base_url, json=search_body)
if response.status_code == 200:
    results = response.json()
    total = results['hits']['total']['value']
    print(f"   Found: {total} results")
    for i, hit in enumerate(results['hits']['hits'][:3], 1):
        source = hit['_source']
        code = source.get('code', 'N/A')
        chapter = source.get('chapter', 'N/A')
        text = source.get('text', '')[:80]
        print(f"   {i}. Code: {code}, Chapter: {chapter}, Text: {text}...")

# 2. Match with wildcard
print("\n2. WILDCARD 'vehicul*':")
search_body = {
    "query": {"wildcard": {"text": "*vehicul*"}},
    "size": 10
}
response = requests.post(base_url, json=search_body)
if response.status_code == 200:
    results = response.json()
    total = results['hits']['total']['value']
    print(f"   Found: {total} results")
    for i, hit in enumerate(results['hits']['hits'][:3], 1):
        source = hit['_source']
        code = source.get('code', 'N/A')
        text = source.get('text', '')[:80]
        print(f"   {i}. Code: {code}, Text: {text}...")

# 3. Search in chapter 87 (vehicles)
print("\n3. CHAPTER 87 (vehículos):")
search_body = {
    "query": {"term": {"chapter": "87"}},
    "size": 5
}
response = requests.post(base_url, json=search_body)
if response.status_code == 200:
    results = response.json()
    total = results['hits']['total']['value']
    print(f"   Found: {total} results")
    for i, hit in enumerate(results['hits']['hits'][:3], 1):
        source = hit['_source']
        code = source.get('code', source.get('heading', 'N/A'))
        desc = source.get('description', source.get('text', ''))[:80]
        print(f"   {i}. Code: {code}, Desc: {desc}...")

# 4. Multi-match
print("\n4. MULTI-MATCH 'vehículo' in multiple fields:")
search_body = {
    "query": {
        "multi_match": {
            "query": "vehículo",
            "fields": ["text", "description", "heading"],
            "type": "best_fields"
        }
    },
    "size": 10
}
response = requests.post(base_url, json=search_body)
if response.status_code == 200:
    results = response.json()
    total = results['hits']['total']['value']
    print(f"   Found: {total} results")
    for i, hit in enumerate(results['hits']['hits'][:3], 1):
        source = hit['_source']
        code = source.get('code', source.get('heading', 'N/A'))
        text = source.get('text', source.get('description', ''))[:80]
        print(f"   {i}. Code: {code}, Text: {text}...")

# Check document structure
print("\n" + "=" * 80)
print("DOCUMENT STRUCTURE SAMPLE")
print("=" * 80)

search_body = {
    "query": {"match_all": {}},
    "size": 1
}
response = requests.post(base_url, json=search_body)
if response.status_code == 200:
    results = response.json()
    if results['hits']['hits']:
        doc = results['hits']['hits'][0]['_source']
        print(f"Available fields in documents:")
        for key in doc.keys():
            print(f"  - {key}")
