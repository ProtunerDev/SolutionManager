#!/usr/bin/env python3

"""
Script para inicializar todas las tablas de la base de datos SolutionManager
"""

import os
import sys
from app import create_app
from app.database.db_manager import DatabaseManager

def init_database():
    """Inicializar la base de datos con todas las tablas"""
    print("🚀 Inicializando base de datos SolutionManager...")
    
    app = create_app()
    
    with app.app_context():
        try:
            with DatabaseManager() as db:
                success = db.initialize_database()
                
                if success:
                    print("✅ Base de datos inicializada correctamente!")
                    print("📋 Tablas creadas:")
                    print("   - users")
                    print("   - vehicle_info")
                    print("   - field_dependencies")
                    print("   - field_values")
                    print("   - solutions")
                    print("   - solution_types")
                    print("   - file_metadata")
                    print("   - differences_metadata")
                    print("")
                    print("🔧 Funciones y triggers configurados")
                    print("📊 Datos iniciales insertados")
                    
                    # Verificar algunas tablas clave
                    print("\n🔍 Verificando estructura de la base de datos...")
                    
                    # Verificar conteo de tablas
                    db.cursor.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_type = 'BASE TABLE'
                        ORDER BY table_name
                    """)
                    tables = db.cursor.fetchall()
                    
                    print(f"   Tablas encontradas: {len(tables)}")
                    for table in tables:
                        print(f"   - {table[0]}")
                    
                    # Verificar datos iniciales
                    db.cursor.execute("SELECT COUNT(*) FROM field_values")
                    field_values_count = db.cursor.fetchone()[0]
                    print(f"   Valores de campo iniciales: {field_values_count}")
                    
                    db.cursor.execute("SELECT COUNT(*) FROM field_dependencies")
                    dependencies_count = db.cursor.fetchone()[0]
                    print(f"   Dependencias de campo: {dependencies_count}")
                    
                    print("\n🎉 ¡Inicialización completada exitosamente!")
                    
                else:
                    print("❌ Error durante la inicialización de la base de datos")
                    return False
                    
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False
    
    return True

def check_database_connection():
    """Verificar conexión a la base de datos"""
    print("🔍 Verificando conexión a la base de datos...")
    
    app = create_app()
    
    with app.app_context():
        try:
            with DatabaseManager() as db:
                db.cursor.execute("SELECT version()")
                version = db.cursor.fetchone()[0]
                print(f"✅ Conectado a PostgreSQL: {version}")
                return True
        except Exception as e:
            print(f"❌ Error de conexión: {str(e)}")
            return False

def main():
    """Función principal"""
    print("=" * 60)
    print("  INICIALIZACIÓN DE BASE DE DATOS SOLUTIONMANAGER")
    print("=" * 60)
    
    # Verificar conexión primero
    if not check_database_connection():
        print("\n❌ No se puede conectar a la base de datos. Verifica la configuración en .env")
        sys.exit(1)
    
    print()
    
    # Confirmar antes de proceder
    confirm = input("¿Deseas proceder con la inicialización? Esto recreará todas las tablas (y/n): ")
    if confirm.lower() not in ['y', 'yes', 's', 'si']:
        print("❌ Operación cancelada")
        sys.exit(0)
    
    print()
    
    # Inicializar base de datos
    if init_database():
        print("\n🎯 La base de datos está lista para usar!")
        print("💡 Puedes ahora ejecutar la aplicación con: python run.py")
    else:
        print("\n❌ Falló la inicialización")
        sys.exit(1)

if __name__ == "__main__":
    main()
