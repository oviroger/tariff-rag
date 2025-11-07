"""
Evaluación de retrieval para formato con anotaciones individuales por documento.

CSV esperado:
  query_id, query, doc_id, rank, score, relevance, snippet

Donde relevance es 0 (no relevante) o 1 (relevante).

Calcula:
  - recall@k (para k=1,3,5)
  - nDCG@k (para k=1,3,5)
  - precision@k
  - MAP (Mean Average Precision)

Uso:
  python evaluation/eval_retrieval_annotated.py --csv evaluation/templates/eval_retrieval_asgard.csv
"""

import csv
import argparse
import json
import numpy as np
from collections import defaultdict
from typing import Dict, List, Tuple


def load_annotations(csv_path: str) -> Dict[int, List[Tuple[str, int, int]]]:
    """
    Carga anotaciones y retorna dict: query_id -> [(doc_id, rank, relevance), ...]
    """
    queries = defaultdict(list)
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            query_id = int(row['query_id'])
            doc_id = row['doc_id']
            rank = int(row['rank'])
            rel_str = row.get('relevance', '').strip()
            
            # Skip si no está anotado
            if rel_str not in ('0', '1'):
                continue
            
            relevance = int(rel_str)
            queries[query_id].append((doc_id, rank, relevance))
    
    # Ordenar por rank
    for qid in queries:
        queries[qid].sort(key=lambda x: x[1])
    
    return queries


def recall_at_k(relevances: List[int], k: int) -> float:
    """
    Recall@k: ¿hay al menos un documento relevante en top-k?
    """
    if not relevances:
        return 0.0
    total_relevant = sum(relevances)
    if total_relevant == 0:
        return 0.0
    relevant_in_k = sum(relevances[:k])
    return 1.0 if relevant_in_k > 0 else 0.0


def precision_at_k(relevances: List[int], k: int) -> float:
    """
    Precision@k: proporción de docs relevantes en top-k
    """
    if not relevances or k == 0:
        return 0.0
    return sum(relevances[:k]) / min(k, len(relevances))


def ndcg_at_k(relevances: List[int], k: int) -> float:
    """
    nDCG@k con relevancia binaria (0 o 1)
    """
    if not relevances:
        return 0.0
    
    gains = relevances[:k]
    if sum(gains) == 0:
        return 0.0
    
    # DCG
    dcg = sum(g / np.log2(i + 2) for i, g in enumerate(gains))
    
    # IDCG (ideal: todos los relevantes primero)
    ideal = sorted(gains, reverse=True)
    idcg = sum(g / np.log2(i + 2) for i, g in enumerate(ideal))
    
    return dcg / idcg if idcg > 0 else 0.0


def average_precision(relevances: List[int]) -> float:
    """
    Average Precision para una query
    """
    if not relevances:
        return 0.0
    
    total_relevant = sum(relevances)
    if total_relevant == 0:
        return 0.0
    
    precisions = []
    relevant_count = 0
    
    for i, rel in enumerate(relevances):
        if rel == 1:
            relevant_count += 1
            precisions.append(relevant_count / (i + 1))
    
    return sum(precisions) / total_relevant if precisions else 0.0


def compute_metrics(queries: Dict[int, List[Tuple[str, int, int]]]) -> Dict[str, float]:
    """
    Calcula todas las métricas agregadas
    """
    if not queries:
        return {
            'recall@1': 0.0,
            'recall@3': 0.0,
            'recall@5': 0.0,
            'precision@1': 0.0,
            'precision@3': 0.0,
            'precision@5': 0.0,
            'ndcg@1': 0.0,
            'ndcg@3': 0.0,
            'ndcg@5': 0.0,
            'map': 0.0,
            'num_queries': 0,
            'num_annotated': 0
        }
    
    recalls_1, recalls_3, recalls_5 = [], [], []
    precisions_1, precisions_3, precisions_5 = [], [], []
    ndcgs_1, ndcgs_3, ndcgs_5 = [], [], []
    aps = []
    
    for qid, docs in queries.items():
        # Extraer solo relevances en orden de rank
        relevances = [rel for _, _, rel in docs]
        
        recalls_1.append(recall_at_k(relevances, 1))
        recalls_3.append(recall_at_k(relevances, 3))
        recalls_5.append(recall_at_k(relevances, 5))
        
        precisions_1.append(precision_at_k(relevances, 1))
        precisions_3.append(precision_at_k(relevances, 3))
        precisions_5.append(precision_at_k(relevances, 5))
        
        ndcgs_1.append(ndcg_at_k(relevances, 1))
        ndcgs_3.append(ndcg_at_k(relevances, 3))
        ndcgs_5.append(ndcg_at_k(relevances, 5))
        
        aps.append(average_precision(relevances))
    
    return {
        'recall@1': float(np.mean(recalls_1)),
        'recall@3': float(np.mean(recalls_3)),
        'recall@5': float(np.mean(recalls_5)),
        'precision@1': float(np.mean(precisions_1)),
        'precision@3': float(np.mean(precisions_3)),
        'precision@5': float(np.mean(precisions_5)),
        'ndcg@1': float(np.mean(ndcgs_1)),
        'ndcg@3': float(np.mean(ndcgs_3)),
        'ndcg@5': float(np.mean(ndcgs_5)),
        'map': float(np.mean(aps)),
        'num_queries': len(queries),
        'num_annotated': sum(sum(1 for _, _, rel in docs if rel in (0, 1)) for docs in queries.values())
    }


def check_annotation_status(csv_path: str) -> Dict[str, int]:
    """
    Verifica estado de anotación
    """
    total = 0
    annotated = 0
    relevant = 0
    not_relevant = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            rel = row.get('relevance', '').strip()
            if rel in ('0', '1'):
                annotated += 1
                if rel == '1':
                    relevant += 1
                else:
                    not_relevant += 1
    
    return {
        'total': total,
        'annotated': annotated,
        'relevant': relevant,
        'not_relevant': not_relevant,
        'pending': total - annotated,
        'completion_pct': (annotated / total * 100) if total > 0 else 0
    }


def main(csv_path: str, verbose: bool = False):
    """
    Evalúa retrieval desde CSV con anotaciones
    """
    # Verificar estado de anotación
    status = check_annotation_status(csv_path)
    
    if verbose:
        print(f"\n{'='*80}")
        print("ESTADO DE ANOTACIÓN")
        print(f"{'='*80}")
        print(f"Total de registros:     {status['total']}")
        print(f"Anotados:               {status['annotated']} ({status['completion_pct']:.1f}%)")
        print(f"  - Relevantes:         {status['relevant']}")
        print(f"  - No relevantes:      {status['not_relevant']}")
        print(f"Pendientes:             {status['pending']}")
        print(f"{'='*80}\n")
    
    if status['annotated'] == 0:
        print("❌ Error: No hay anotaciones en el CSV. Ejecuta primero:")
        print("   python evaluation/tools/annotate_retrieval.py --csv", csv_path)
        return
    
    # Cargar anotaciones
    queries = load_annotations(csv_path)
    
    if not queries:
        print("❌ Error: No se pudieron cargar queries anotadas")
        return
    
    # Calcular métricas
    metrics = compute_metrics(queries)
    
    # Imprimir resultados
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evalúa retrieval con anotaciones individuales')
    parser.add_argument('--csv', required=True, help='Ruta al CSV con anotaciones')
    parser.add_argument('--verbose', action='store_true', help='Mostrar detalles de anotación')
    args = parser.parse_args()
    
    main(args.csv, args.verbose)
