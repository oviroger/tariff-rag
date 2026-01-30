#!/usr/bin/env python3
"""
PASO 1: Inspeccionar datos en MySQL para reindexación
"""

import mysql.connector
import json

# Conectar a MySQL
conn = mysql.connector.connect(
    host="localhost",
    user="appuser",
    password="apppass",
    database="corpusdb"
)

cursor = conn.cursor(dictionary=True)

print("=" * 100)
print("📊 INSPECCIÓN DE DATOS EN MYSQL")
print("=" * 100)

# 1. Ver tablas disponibles
print("\n1️⃣  TABLAS DISPONIBLES:")
cursor.execute("SHOW TABLES;")
tables = cursor.fetchall()
for table in tables:
    table_name = table[list(table.keys())[0]]
    cursor.execute(f"SELECT COUNT(*) as count FROM {table_name};")
    count = cursor.fetchone()['count']
    print(f"   ✅ {table_name}: {count} registros")

# 2. Ver estructura de tabla principal (si existe partidas, asgard, etc)
print("\n2️⃣  ESTRUCTURA DE TABLAS:")

important_tables = ['partidas', 'asgard', 'aranceles', 'tariff', 'products', 'classifications']

for table_name in important_tables:
    try:
        cursor.execute(f"DESCRIBE {table_name};")
        columns = cursor.fetchall()
        if columns:
            print(f"\n   ✅ Tabla: {table_name}")
            print(f"      Columnas:")
            for col in columns:
                col_name = col['Field']
                col_type = col['Type']
                print(f"        - {col_name}: {col_type}")
    except:
        pass

# 3. Sample data de tabla principal
print("\n3️⃣  DATOS DE EJEMPLO:")

for table_name in important_tables:
    try:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 2;")
        rows = cursor.fetchall()
        if rows:
            print(f"\n   ✅ {table_name}:")
            for i, row in enumerate(rows, 1):
                print(f"\n      Registro {i}:")
                for key, value in row.items():
                    val_str = str(value)[:60] if value else "NULL"
                    print(f"        {key}: {val_str}")
    except Exception as e:
        pass

# 4. Búsqueda específica: ¿Hay datos sobre electrodomésticos?
print("\n4️⃣  BÚSQUEDA: ELECTRODOMÉSTICOS Y CÓDIGOS HS:")

search_terms = ['microondas', '8516', 'electrodomestico', 'washing', 'refrigerator']

for table_name in important_tables:
    try:
        for term in search_terms:
            cursor.execute(f"""
                SELECT * FROM {table_name} 
                WHERE (
                    LOWER(CAST(* AS CHAR)) LIKE %s
                ) LIMIT 1;
            """, (f"%{term}%",))
            
            # Esto podría fallar en MariaDB, intentar otra forma
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1;")
            sample = cursor.fetchone()
            
            if sample:
                # Convertir a string y buscar
                sample_str = json.dumps(sample, default=str).lower()
                if term.lower() in sample_str:
                    print(f"\n   ✅ '{term}' encontrado en {table_name}")
                    break
    except:
        pass

# 5. Información sobre índices y años
print("\n5️⃣  INFORMACIÓN SOBRE AÑOS Y VERSIONES:")

for table_name in important_tables:
    try:
        cursor.execute(f"SELECT DISTINCT YEAR(created_at) as year FROM {table_name} LIMIT 5;")
        years = cursor.fetchall()
        if years:
            print(f"   ✅ {table_name}: Años encontrados")
    except:
        try:
            cursor.execute(f"SELECT DISTINCT year FROM {table_name} LIMIT 5;")
            years = cursor.fetchall()
            if years:
                print(f"   ✅ {table_name}: {[y.get('year', 'N/A') for y in years]}")
        except:
            pass

cursor.close()
conn.close()

print("\n" + "=" * 100)
print("✅ INSPECCIÓN COMPLETADA")
print("=" * 100)
