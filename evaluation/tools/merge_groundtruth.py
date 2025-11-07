"""
Fusiona el CSV generado con las predicciones con el CSV de ground truth.
Agrega los códigos HS verdaderos automáticamente.
"""
import csv
import sys
from pathlib import Path

def merge_groundtruth(predictions_csv: str, groundtruth_csv: str, output_csv: str):
    """Fusiona predicciones con ground truth por query_id"""
    
    # Leer ground truth
    print(f"📖 Leyendo {groundtruth_csv}...")
    truth_dict = {}
    with open(groundtruth_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            query_id = int(row['query_id'])
            true_hs6 = row['true_hs6']
            truth_dict[query_id] = true_hs6
    
    print(f"   {len(truth_dict)} códigos HS cargados")
    
    # Leer predicciones y agregar true_hs6
    print(f"📖 Leyendo {predictions_csv}...")
    rows = []
    missing_count = 0
    with open(predictions_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        for row in reader:
            query_id = int(row['query_id'])
            # Buscar el código HS verdadero
            true_hs6 = truth_dict.get(query_id, '')
            if not true_hs6:
                missing_count += 1
            row['true_hs6'] = true_hs6
            rows.append(row)
    
    # Guardar con true_hs6 actualizado
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✅ Guardado: {output_csv}")
    print(f"   Total: {len(rows)} queries")
    print(f"   Con ground truth: {len(rows) - missing_count}")
    if missing_count > 0:
        print(f"   ⚠️  Sin ground truth: {missing_count}")
    print()
    
    # Mostrar muestra
    print("📊 Muestra de registros:")
    print(f"{'QID':<5} {'True HS6':<10} {'Pred Top1':<10}")
    print("-" * 30)
    for row in rows[:10]:
        qid = row['query_id']
        true_hs6 = row['true_hs6']
        pred_top1 = row.get('pred_top1', '')
        print(f"{qid:<5} {true_hs6:<10} {pred_top1:<10}")

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Uso: python merge_groundtruth.py <predictions_csv> <groundtruth_csv> <output_csv>")
        sys.exit(1)
    
    merge_groundtruth(sys.argv[1], sys.argv[2], sys.argv[3])
