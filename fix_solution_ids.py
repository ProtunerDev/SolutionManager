#!/usr/bin/env python3
"""
Script para corregir las inconsistencias de IDs entre vehicle_info y solutions

Este script:
1. Verifica el estado actual de las tablas
2. Asegura que cada vehicle_info tenga una entrada correspondiente en solutions
3. Migra cualquier referencia que use vehicle_info.id a solutions.id
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import Flask app to create context
from app import create_app
from app.database.db_manager import DatabaseManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_data_inconsistencies():
    """Analiza las inconsistencias en los datos actuales."""
    with DatabaseManager() as db:
        print("=== ANÁLISIS DE DATOS ACTUALES ===\n")
        
        # Contar registros en vehicle_info
        db.cursor.execute("SELECT COUNT(*) FROM vehicle_info")
        vehicle_info_count = db.cursor.fetchone()[0]
        print(f"Registros en vehicle_info: {vehicle_info_count}")
        
        # Contar registros en solutions
        db.cursor.execute("SELECT COUNT(*) FROM solutions")
        solutions_count = db.cursor.fetchone()[0]
        print(f"Registros en solutions: {solutions_count}")
        
        # Verificar vehicle_info sin solutions correspondientes
        db.cursor.execute("""
            SELECT v.id, v.make, v.model, v.hardware_number, v.software_number
            FROM vehicle_info v
            LEFT JOIN solutions s ON v.id = s.vehicle_info_id
            WHERE s.id IS NULL
        """)
        orphaned_vehicle_info = db.cursor.fetchall()
        print(f"\nVehicle_info sin solutions correspondientes: {len(orphaned_vehicle_info)}")
        for vi in orphaned_vehicle_info:
            print(f"  - ID {vi[0]}: {vi[1]} {vi[2]} (HW: {vi[3]}, SW: {vi[4]})")
        
        # Verificar solutions con vehicle_info_id inexistente
        db.cursor.execute("""
            SELECT s.id, s.vehicle_info_id
            FROM solutions s
            LEFT JOIN vehicle_info v ON s.vehicle_info_id = v.id
            WHERE v.id IS NULL
        """)
        orphaned_solutions = db.cursor.fetchall()
        print(f"\nSolutions con vehicle_info_id inexistente: {len(orphaned_solutions)}")
        for sol in orphaned_solutions:
            print(f"  - Solution ID {sol[0]} apunta a vehicle_info_id {sol[1]} (no existe)")
        
        # Mostrar mapeo actual
        db.cursor.execute("""
            SELECT s.id as solution_id, s.vehicle_info_id, v.make, v.model
            FROM solutions s
            JOIN vehicle_info v ON s.vehicle_info_id = v.id
            ORDER BY s.id
        """)
        mappings = db.cursor.fetchall()
        print(f"\nMapeo actual solutions -> vehicle_info:")
        for mapping in mappings:
            print(f"  - Solution ID {mapping[0]} -> Vehicle_info ID {mapping[1]} ({mapping[2]} {mapping[3]})")

def create_missing_solutions():
    """Crea registros en solutions para cualquier vehicle_info que no tenga uno."""
    with DatabaseManager() as db:
        print("\n=== CREANDO SOLUTIONS FALTANTES ===\n")
        
        # Encontrar vehicle_info sin solutions
        db.cursor.execute("""
            SELECT v.id, v.make, v.model
            FROM vehicle_info v
            LEFT JOIN solutions s ON v.id = s.vehicle_info_id
            WHERE s.id IS NULL
        """)
        orphaned_vehicle_info = db.cursor.fetchall()
        
        if not orphaned_vehicle_info:
            print("✅ Todos los vehicle_info tienen solutions correspondientes")
            return
        
        print(f"Creando {len(orphaned_vehicle_info)} registros en solutions...")
        
        for vi_id, make, model in orphaned_vehicle_info:
            db.cursor.execute("""
                INSERT INTO solutions (vehicle_info_id, description, status)
                VALUES (%s, %s, 'active')
            """, (vi_id, f"Solution for {make} {model}"))
            print(f"  ✅ Creado solution para vehicle_info ID {vi_id} ({make} {model})")
        
        db.conn.commit()
        print(f"\n✅ Se crearon {len(orphaned_vehicle_info)} registros en solutions")

def verify_file_metadata_references():
    """Verifica que las referencias en file_metadata sean correctas."""
    with DatabaseManager() as db:
        print("\n=== VERIFICANDO REFERENCIAS EN FILE_METADATA ===\n")
        
        # Verificar file_metadata con solution_id inexistente
        db.cursor.execute("""
            SELECT fm.id, fm.solution_id, fm.file_type, fm.file_name
            FROM file_metadata fm
            LEFT JOIN solutions s ON fm.solution_id = s.id
            WHERE s.id IS NULL
        """)
        orphaned_files = db.cursor.fetchall()
        
        if orphaned_files:
            print(f"⚠️ Encontrados {len(orphaned_files)} archivos con solution_id inexistente:")
            for file_record in orphaned_files:
                print(f"  - File ID {file_record[0]}: solution_id {file_record[1]} ({file_record[2]}) - {file_record[3]}")
        else:
            print("✅ Todas las referencias en file_metadata son válidas")

def main():
    """Función principal del script de migración."""
    print("🔧 SCRIPT DE CORRECCIÓN DE IDs DE SOLUTIONS\n")
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            # Paso 1: Analizar el estado actual
            analyze_data_inconsistencies()
            
            # Paso 2: Crear solutions faltantes
            create_missing_solutions()
            
            # Paso 3: Verificar referencias de archivos
            verify_file_metadata_references()
            
            # Paso 4: Análisis final
            print("\n=== ANÁLISIS FINAL ===")
            analyze_data_inconsistencies()
            
            print("\n✅ Script completado exitosamente")
            print("\nNOTA: Después de ejecutar este script, todas las vistas deberían mostrar")
            print("los mismos IDs para las mismas soluciones.")
            
        except Exception as e:
            logger.error(f"Error durante la migración: {e}")
            print(f"\n❌ Error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
