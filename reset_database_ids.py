#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reiniciar completamente los contadores de ID en PostgreSQL
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure Flask environment
os.environ['FLASK_ENV'] = 'production'

from config import Config
from app.database.db_manager import DatabaseManager

def reset_database_sequences():
    """Reiniciar todos los contadores de ID en la base de datos"""
    print("🔢 REINICIANDO CONTADORES DE IDs DE LA BASE DE DATOS")
    print("=" * 60)
    
    try:
        # Initialize database manager
        config = Config()
        db_params = {
            "host": config.DB_HOST,
            "port": config.DB_PORT,
            "database": config.DB_NAME,
            "user": config.DB_USER,
            "password": config.DB_PASSWORD
        }
        db_manager = DatabaseManager(db_params)
        
        # Connect manually since we're outside Flask context
        if not db_manager.connect():
            raise Exception("Failed to connect to database")
        
        cursor = db_manager.cursor
        
        # Check current state of all tables
        tables_to_check = ['solutions', 'vehicle_info', 'file_metadata']
        
        print("📊 ESTADO ACTUAL:")
        for table in tables_to_check:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   🗂️ {table}: {count} registros")
        
        # Check for any remaining data
        cursor.execute("SELECT COUNT(*) FROM solutions")
        solution_count = cursor.fetchone()[0]
        
        if solution_count > 0:
            print(f"\n⚠️ ADVERTENCIA: Aún hay {solution_count} soluciones en la base de datos")
            cursor.execute("SELECT id, description FROM solutions ORDER BY id")
            solutions = cursor.fetchall()
            print("\n🗂️ SOLUCIONES EXISTENTES:")
            for sol in solutions:
                desc = sol[1] or "Sin descripción"
                print(f"   🗄️ ID: {sol[0]} - {desc[:50]}...")
            
            confirmation = input("\n¿Eliminar TODAS las soluciones y reiniciar contadores? (escriba 'RESETEAR'): ")
            if confirmation != 'RESETEAR':
                print("❌ Operación cancelada")
                db_manager.close()
                return
            
            # Delete all data in correct order (respecting foreign keys)
            print("\n🗑️ Eliminando datos...")
            cursor.execute("DELETE FROM file_metadata")
            print("   ✅ file_metadata limpiada")
            
            cursor.execute("DELETE FROM solutions")
            print("   ✅ solutions limpiada")
            
            cursor.execute("DELETE FROM vehicle_info")
            print("   ✅ vehicle_info limpiada")
        
        # Get sequences to reset
        sequences = [
            'solutions_id_seq',
            'vehicle_info_id_seq', 
            'file_metadata_id_seq'
        ]
        
        print(f"\n🔄 REINICIANDO SECUENCIAS:")
        for seq in sequences:
            try:
                # Get current value
                cursor.execute(f"SELECT last_value FROM {seq}")
                current_val = cursor.fetchone()[0]
                
                # Reset sequence
                cursor.execute(f"ALTER SEQUENCE {seq} RESTART WITH 1")
                
                # Verify reset
                cursor.execute(f"SELECT last_value FROM {seq}")
                new_val = cursor.fetchone()[0]
                
                print(f"   🔢 {seq}: {current_val} → {new_val}")
                
            except Exception as e:
                print(f"   ⚠️ Error con {seq}: {e}")
        
        # Commit all changes
        db_manager.conn.commit()
        
        # Final verification
        print(f"\n✅ CONTADORES REINICIADOS EXITOSAMENTE")
        print("=" * 60)
        print("📋 RESULTADO:")
        for table in tables_to_check:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   🗂️ {table}: {count} registros")
        
        print(f"\n🚀 PRÓXIMOS IDs:")
        print(f"   🆔 Solutions: 1")
        print(f"   🆔 Vehicle_info: 1") 
        print(f"   🆔 File_metadata: 1")
        print(f"\n💡 La próxima solución creada tendrá ID: 1")
        
        db_manager.close()
        
    except Exception as e:
        print(f"❌ Error al reiniciar contadores: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    reset_database_sequences()
