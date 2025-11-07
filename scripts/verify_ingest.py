import os
import json
from typing import Any, Dict

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.os_index import get_os_client
from app.config import get_settings


def main():
    s = get_settings()
    index = os.environ.get("TARGET_INDEX") or os.environ.get("OPENSEARCH_INDEX") or s.opensearch_index
    client = get_os_client()

    print(f"\n🔎 Verificando índice: {index}")
    exists = client.indices.exists(index)
    print(f"  Existe: {exists}")
    if not exists:
        return

    try:
        count_all = client.count(index=index)["count"]
    except Exception as e:
        print(f"  Error al contar documentos: {e}")
        return
    print(f"  Total de documentos: {count_all}")

    # Conteo filtrado por fuente ASGARD_DB
    count_asgard = None
    try:
        # Prioriza campo keyword si existe
        count_asgard = client.count(index=index, body={
            "query": {"term": {"source.keyword": "ASGARD_DB"}}
        })["count"]
    except Exception:
        try:
            count_asgard = client.count(index=index, body={
                "query": {"term": {"source": "ASGARD_DB"}}
            })["count"]
        except Exception as e:
            print(f"  Aviso: 'source' (term) no disponible o error ({e}); probando alternativas...")
            # Fallback: buscar por metadata.source o match sobre 'source'
            for q in (
                {"term": {"metadata.source.keyword": "ASGARD_DB"}},
                {"term": {"metadata.source": "ASGARD_DB"}},
                {"match": {"source": "ASGARD_DB"}},
            ):
                try:
                    count_asgard = client.count(index=index, body={"query": q})["count"]
                    break
                except Exception:
                    continue
    print(f"  Documentos ASGARD_DB: {count_asgard}")

    # Obtener un ejemplo de documento de ASGARD
    try:
        sample = client.search(index=index, body={
            "size": 1,
            "query": {"bool": {"should": [
                {"term": {"source": "ASGARD_DB"}},
                {"term": {"metadata.source": "ASGARD_DB"}},
                {"match": {"source": "ASGARD_DB"}}
            ], "minimum_should_match": 1}}
        })
        hits = sample.get("hits", {}).get("hits", [])
        if hits:
            doc = hits[0]["_source"]
            print("\n📝 Ejemplo de documento ASGARD:")
            preview = {k: doc.get(k) for k in ["fragment_id", "doc_id", "codigo_producto", "partida", "hs6", "bucket"]}
            print(json.dumps(preview, ensure_ascii=False, indent=2))
            print("\nTexto (primeros 240 chars):")
            print((doc.get("text") or "")[:240] + "...")
        else:
            print("\n(No se encontraron documentos con source=ASGARD_DB)")
    except Exception as e:
        print(f"  Error al buscar ejemplo: {e}")

    # Top 10 hs6 por frecuencia (si los hay)
    try:
        agg = client.search(index=index, body={
            "size": 0,
            "query": {"bool": {"should": [
                {"term": {"source.keyword": "ASGARD_DB"}},
                {"term": {"metadata.source.keyword": "ASGARD_DB"}},
                {"match": {"source": "ASGARD_DB"}}
            ], "minimum_should_match": 1}},
            "aggs": {"hs6_top": {"terms": {"field": "hs6.keyword", "size": 10}}}
        })
        buckets = agg.get("aggregations", {}).get("hs6_top", {}).get("buckets", [])
        if buckets:
            print("\n🏷️  Top 10 hs6:")
            for b in buckets:
                print(f"  {b['key']}: {b['doc_count']}")
    except Exception as e:
        print(f"  Error en agregación hs6: {e}")


if __name__ == "__main__":
    main()
