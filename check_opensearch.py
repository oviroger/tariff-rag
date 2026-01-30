import requests
import json

# Verificar si OpenSearch está disponible
print("=" * 80)
print("CHECKING OPENSEARCH STATUS")
print("=" * 80)

try:
    response = requests.get('http://localhost:9200/_cluster/health')
    health = response.json()
    print(f"✓ OpenSearch Health: {health['status']}")
    print(f"  - Active shards: {health['active_shards']}")
except Exception as e:
    print(f"✗ Error connecting to OpenSearch: {e}")
    exit(1)

# Listar índices
print("\n" + "=" * 80)
print("AVAILABLE INDICES")
print("=" * 80)

try:
    response = requests.get('http://localhost:9200/_cat/indices?format=json')
    indices = response.json()
    
    if not indices:
        print("✗ No indices found!")
    else:
        for idx in indices:
            count = int(idx['docs.count'])
            status = "✓" if count > 0 else "✗"
            print(f"{status} {idx['index']}: {count} documents")
except Exception as e:
    print(f"✗ Error listing indices: {e}")
    exit(1)

# Verificar índices específicos de tariff
print("\n" + "=" * 80)
print("SEARCHING FOR TARIFF DATA")
print("=" * 80)

tariff_indices = ['tariff_fragments_2025_v2', 'tariff_fragments_2026_v2']
for idx_name in tariff_indices:
    try:
        response = requests.get(f'http://localhost:9200/{idx_name}/_count')
        if response.status_code == 200:
            count = response.json()['count']
            print(f"✓ {idx_name}: {count} documents")
        else:
            print(f"✗ {idx_name}: Not found (Status {response.status_code})")
    except Exception as e:
        print(f"✗ {idx_name}: Error - {e}")

# Test a sample search for "vehículo"
print("\n" + "=" * 80)
print("TEST SEARCH: 'vehículo'")
print("=" * 80)

try:
    search_body = {
        "query": {
            "multi_match": {
                "query": "vehículo",
                "fields": ["text", "description"]
            }
        },
        "size": 3
    }
    
    response = requests.post('http://localhost:9200/tariff_fragments_2025_v2/_search', 
                            json=search_body)
    
    if response.status_code == 200:
        results = response.json()
        hits = results['hits']['total']['value']
        print(f"✓ Found {hits} results for 'vehículo'")
        
        if results['hits']['hits']:
            print("\n  Sample results:")
            for hit in results['hits']['hits'][:2]:
                code = hit['_source'].get('code', 'N/A')
                text = hit['_source'].get('text', '')[:100]
                print(f"    - Code: {code}, Text: {text}...")
        else:
            print("✗ No results returned in hits")
    else:
        print(f"✗ Search error: Status {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        
except Exception as e:
    print(f"✗ Search error: {e}")
