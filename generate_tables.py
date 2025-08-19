#!/usr/bin/env python3

"""
Script para generar las tablas SQL que se deben ejecutar en la base de datos
"""

import os
from pathlib import Path

def generate_sql_commands():
    """Generar comandos SQL para crear las tablas"""
    
    # Leer el archivo schema.sql
    schema_path = Path("app/database/schema.sql")
    
    if not schema_path.exists():
        print("❌ No se encontró el archivo schema.sql")
        return False
    
    print("📋 COMANDOS SQL PARA GENERAR TODAS LAS TABLAS")
    print("=" * 60)
    print()
    print("Ejecuta estos comandos en tu cliente de PostgreSQL:")
    print()
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    print(sql_content)
    
    print()
    print("=" * 60)
    print("✅ Comandos SQL generados")
    print()
    print("💡 INSTRUCCIONES:")
    print("1. Copia el contenido SQL de arriba")
    print("2. Conéctate a tu base de datos PostgreSQL usando:")
    print("   - pgAdmin")
    print("   - psql command line")
    print("   - DBeaver")
    print("   - O cualquier otro cliente SQL")
    print("3. Ejecuta todo el script SQL")
    print("4. Las tablas se crearán automáticamente")
    
    return True

def show_connection_info():
    """Mostrar información de conexión"""
    print()
    print("🔧 INFORMACIÓN DE CONEXIÓN ACTUAL:")
    print("=" * 60)
    
    # Leer variables del .env
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path, 'r') as f:
            env_content = f.read()
        
        for line in env_content.split('\n'):
            if line.startswith('DB_'):
                print(f"   {line}")
    
    print()
    print("💡 Para conectarte manualmente, usa estos parámetros:")
    print("   Host: shuttle.proxy.rlwy.net")
    print("   Puerto: 50835")
    print("   Base de datos: railway")
    print("   Usuario: postgresql")
    print("   Contraseña: [la que está en DB_PASSWORD]")

def main():
    """Función principal"""
    print("🚀 GENERADOR DE TABLAS PARA SOLUTIONMANAGER")
    print()
    
    # Generar comandos SQL
    if generate_sql_commands():
        show_connection_info()
    
    print()
    print("📄 El archivo schema.sql también está disponible en:")
    print("   app/database/schema.sql")

if __name__ == "__main__":
    main()
