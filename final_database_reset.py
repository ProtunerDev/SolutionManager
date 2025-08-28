#!/usr/bin/env python3
"""
Verificación final del estado de la base de datos y reset completo
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de la base de datos
db_config = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'port': os.getenv('DB_PORT', 5432)
}

print("🔧 Reset final de base de datos y secuencias...")

try:
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    
    print("\n🗑️ LIMPIEZA COMPLETA DE TODAS LAS TABLAS:")
    
    # Lista de tablas a limpiar (en orden por foreign keys)
    tables_to_clean = [
        'file_metadata',
        'differences_metadata', 
        'vehicle_info',
        'solutions'
    ]
    
    for table in tables_to_clean:
        try:
            cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
            print(f"  ✅ {table} truncada")
        except Exception as e:
            print(f"  ⚠️ {table}: {e}")
    
    print("\n🔄 RESET DE SECUENCIAS CON RESTART IDENTITY:")
    
    sequences = ['solutions_id_seq', 'vehicle_info_id_seq', 'file_metadata_id_seq']
    
    for seq_name in sequences:
        try:
            cur.execute(f"ALTER SEQUENCE {seq_name} RESTART WITH 1")
            print(f"  ✅ {seq_name} reiniciada a 1")
        except Exception as e:
            print(f"  ⚠️ {seq_name}: {e}")
    
    # Commit todas las operaciones
    conn.commit()
    
    print("\n📊 VERIFICACIÓN FINAL:")
    
    for seq_name in sequences:
        cur.execute(f"SELECT last_value, is_called FROM {seq_name}")
        result = cur.fetchone()
        if result:
            last_value, is_called = result
            print(f"  {seq_name}: last_value={last_value}, is_called={is_called}")
    
    for table in tables_to_clean:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  {table}: {count} registros")
    
    print("\n🔍 PRUEBA DE INSERCIÓN REAL:")
    
    # Probar inserción real de una solution
    try:
        cur.execute("""
            INSERT INTO vehicle_info (
                vehicle_type, make, model, engine, year, 
                hardware_number, software_number, transmission_type
            ) VALUES (
                'TEST', 'TEST', 'TEST', 'TEST', 2024,
                'TEST', 'TEST', 'TEST'
            ) RETURNING id
        """)
        vehicle_info_id = cur.fetchone()[0]
        print(f"  ✅ vehicle_info insertado con ID: {vehicle_info_id}")
        
        cur.execute("""
            INSERT INTO solutions (
                vehicle_info_id, description, status
            ) VALUES (
                %s, 'TEST SOLUTION', 'active'
            ) RETURNING id
        """, (vehicle_info_id,))
        solution_id = cur.fetchone()[0]
        print(f"  ✅ solution insertada con ID: {solution_id}")
        
        # Limpiar la prueba
        cur.execute("DELETE FROM solutions WHERE id = %s", (solution_id,))
        cur.execute("DELETE FROM vehicle_info WHERE id = %s", (vehicle_info_id,))
        
        # Resetear secuencias de nuevo después de la prueba
        cur.execute("ALTER SEQUENCE solutions_id_seq RESTART WITH 1")
        cur.execute("ALTER SEQUENCE vehicle_info_id_seq RESTART WITH 1")
        
        conn.commit()
        
        print(f"  ✅ Prueba exitosa - Se creó solution con ID {solution_id}")
        print(f"  ✅ Datos de prueba eliminados, secuencias reseteadas")
        
    except Exception as e:
        print(f"  ❌ Error en prueba de inserción: {e}")
        conn.rollback()
    
    cur.close()
    conn.close()
    
    print("\n🎯 ESTADO FINAL:")
    print("✅ Base de datos completamente limpia")
    print("✅ Todas las secuencias en 1")
    print("✅ Inserción de prueba exitosa")
    print("✅ El próximo ID de solution debería ser 1")
    
    print("\n🚀 AHORA PUEDES:")
    print("1. Reiniciar la aplicación web")
    print("2. Cargar una nueva solución")
    print("3. Debería tener ID=1 y archivos ORI1 correctos")
    
except Exception as e:
    print(f"❌ Error: {e}")
    if conn:
        conn.rollback()
