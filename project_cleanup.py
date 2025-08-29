#!/usr/bin/env python3
"""
Limpieza completa del proyecto: archivos no utilizados, base de datos y S3
"""

import os
import sys
import shutil
from pathlib import Path
import boto3
from dotenv import load_dotenv
import psycopg2

# Cargar variables de entorno
load_dotenv()

def clean_unused_files():
    """Eliminar archivos no utilizados del proyecto"""
    print("🧹 LIMPIANDO ARCHIVOS NO UTILIZADOS DEL PROYECTO")
    print("=" * 60)
    
    # Archivos de scripts de debugging/testing que ya no necesitamos
    files_to_remove = [
        'check_and_clean_solutions.py',
        'check_config.py',
        'check_database_users.py', 
        'check_local_users.py',
        'check_ori1_s3.py',
        'check_solutions_db.py',
        'check_solutions_ori1.py',
        'check_solutions.py',
        'check_storage_config.py',
        'cleanup_complete.py',  # El viejo
        'cleanup_database.py',
        'cleanup_local_uploads.py',
        'cleanup_s3.py',
        'cleanup_solutions.py',
        'debug_config.py',
        'debug_deletion.py',
        'debug_differences.py',
        'debug_ori1_issue.py',
        'debug_sequence_state.py',
        'debug_storage_config.py',
        'debug_token.py',
        'final_database_reset.py',
        'final_system_check.py',
        'fix_solution_ids.py',
        'fix_upload_process.py',
        'generate_tables.py',
        'init_database.py',
        'reset_database_ids.py',
        'test_admin_functions.py',
        'test_admin_issues.py',
        'test_admin_setup.py',
        'test_api_endpoint.py',
        'test_apply_solution.py',
        'test_compatibility_advanced.py',
        'test_compatibility.py',
        'test_db_connection.py',
        'test_delete_functionality.py',
        'test_differences_storage.py',
        'test_file_upload.py',
        'test_files_comparison.py',
        'test_ori1_flow.py',
        'test_ori1_permanent_storage.py',
        'test_password_reset.py',
        'test_post_restart.py',
        'test_reset_token.py',
        'test_s3_upload.py',
        'test_simple_ori1_logic.py',
        'test_transfer_fix.py',
        'verify_app_status.py',
        'verify_ori1_storage.py',
        # Excel files
        'Dropdowninfo.xlsx',
        'SolutionManager_Documentacion.docx'
    ]
    
    # Directorios temporales que pueden existir
    dirs_to_remove = [
        'scripts_backup',
        'tests',
        '__pycache__',
        'app/__pycache__',
        'app/auth/__pycache__',
        'app/database/__pycache__',
        'app/main/__pycache__',
        'app/utils/__pycache__'
    ]
    
    removed_files = 0
    removed_dirs = 0
    
    print("📁 ELIMINANDO ARCHIVOS NO UTILIZADOS:")
    for file_name in files_to_remove:
        file_path = Path(file_name)
        if file_path.exists():
            try:
                file_path.unlink()
                print(f"   ✅ Eliminado: {file_name}")
                removed_files += 1
            except Exception as e:
                print(f"   ❌ Error eliminando {file_name}: {e}")
        else:
            print(f"   ⚪ No existe: {file_name}")
    
    print(f"\n📂 ELIMINANDO DIRECTORIOS TEMPORALES:")
    for dir_name in dirs_to_remove:
        dir_path = Path(dir_name)
        if dir_path.exists():
            try:
                shutil.rmtree(dir_path)
                print(f"   ✅ Eliminado directorio: {dir_name}")
                removed_dirs += 1
            except Exception as e:
                print(f"   ❌ Error eliminando directorio {dir_name}: {e}")
        else:
            print(f"   ⚪ No existe: {dir_name}")
    
    print(f"\n📊 RESUMEN ARCHIVOS:")
    print(f"   🗑️ Archivos eliminados: {removed_files}")
    print(f"   📂 Directorios eliminados: {removed_dirs}")
    
    return removed_files, removed_dirs

def clean_database():
    """Limpiar completamente la base de datos"""
    print("\n🗃️ LIMPIANDO BASE DE DATOS COMPLETAMENTE")
    print("=" * 60)
    
    db_config = {
        'host': os.getenv('DB_HOST'),
        'database': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'port': os.getenv('DB_PORT', 5432)
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        
        # Obtener conteo antes de limpiar
        tables = ['solutions', 'vehicle_info', 'file_metadata', 'differences_metadata']
        before_counts = {}
        
        print("📊 CONTEO ANTES DE LIMPIAR:")
        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                before_counts[table] = count
                print(f"   📋 {table}: {count} registros")
            except Exception as e:
                print(f"   ❌ Error contando {table}: {e}")
                before_counts[table] = 0
        
        # Limpiar todas las tablas
        print(f"\n🧽 LIMPIANDO TABLAS:")
        for table in tables:
            try:
                cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
                print(f"   ✅ {table} limpiada")
            except Exception as e:
                print(f"   ❌ Error limpiando {table}: {e}")
        
        # Resetear secuencias
        sequences = ['solutions_id_seq', 'vehicle_info_id_seq', 'file_metadata_id_seq']
        print(f"\n🔄 RESETEANDO SECUENCIAS:")
        for seq in sequences:
            try:
                cur.execute(f"ALTER SEQUENCE {seq} RESTART WITH 1")
                print(f"   ✅ {seq} reseteada a 1")
            except Exception as e:
                print(f"   ❌ Error reseteando {seq}: {e}")
        
        conn.commit()
        
        # Verificar limpieza
        print(f"\n✅ VERIFICACIÓN POST-LIMPIEZA:")
        total_records_removed = 0
        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                removed = before_counts.get(table, 0)
                total_records_removed += removed
                print(f"   📋 {table}: {count} registros (eliminados: {removed})")
            except Exception as e:
                print(f"   ❌ Error verificando {table}: {e}")
        
        cur.close()
        conn.close()
        
        print(f"\n📊 RESUMEN BASE DE DATOS:")
        print(f"   🗑️ Total registros eliminados: {total_records_removed}")
        print(f"   🔄 Secuencias reseteadas: {len(sequences)}")
        
        return total_records_removed
        
    except Exception as e:
        print(f"❌ Error limpiando base de datos: {e}")
        return 0

def clean_s3():
    """Limpiar completamente el bucket S3"""
    print("\n☁️ LIMPIANDO BUCKET S3 COMPLETAMENTE")
    print("=" * 60)
    
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_S3_REGION')
        )
        bucket_name = os.getenv('AWS_S3_BUCKET')
        
        # Listar todos los objetos
        print("📋 INVENTARIO DEL BUCKET:")
        response = s3_client.list_objects_v2(Bucket=bucket_name)
        
        if 'Contents' not in response:
            print("   ✅ Bucket ya está vacío")
            return 0
        
        total_objects = len(response['Contents'])
        total_size = sum(obj['Size'] for obj in response['Contents'])
        
        print(f"   📁 Objetos encontrados: {total_objects}")
        print(f"   💾 Tamaño total: {total_size / (1024*1024):.2f} MB")
        
        # Mostrar algunos ejemplos
        print(f"\n📄 EJEMPLOS DE ARCHIVOS:")
        for obj in response['Contents'][:10]:
            size_mb = obj['Size'] / (1024*1024)
            print(f"   📄 {obj['Key']} ({size_mb:.2f} MB)")
        
        if total_objects > 10:
            print(f"   ... y {total_objects - 10} archivos más")
        
        # Eliminar todos los objetos
        print(f"\n🗑️ ELIMINANDO OBJETOS:")
        
        # Para buckets con muchos objetos, eliminar en lotes
        objects_to_delete = []
        for obj in response['Contents']:
            objects_to_delete.append({'Key': obj['Key']})
        
        # Eliminar en lotes de 1000 (límite de AWS)
        deleted_count = 0
        for i in range(0, len(objects_to_delete), 1000):
            batch = objects_to_delete[i:i+1000]
            
            delete_response = s3_client.delete_objects(
                Bucket=bucket_name,
                Delete={'Objects': batch}
            )
            
            if 'Deleted' in delete_response:
                batch_deleted = len(delete_response['Deleted'])
                deleted_count += batch_deleted
                print(f"   ✅ Lote eliminado: {batch_deleted} objetos")
            
            if 'Errors' in delete_response:
                for error in delete_response['Errors']:
                    print(f"   ❌ Error: {error['Key']} - {error['Message']}")
        
        # Verificar que el bucket está vacío
        verification = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
        if 'Contents' not in verification:
            print(f"   ✅ Bucket completamente vacío")
        else:
            remaining = verification['KeyCount']
            print(f"   ⚠️ Aún quedan {remaining} objetos")
        
        print(f"\n📊 RESUMEN S3:")
        print(f"   🗑️ Objetos eliminados: {deleted_count}")
        print(f"   💾 Espacio liberado: {total_size / (1024*1024):.2f} MB")
        
        return deleted_count
        
    except Exception as e:
        print(f"❌ Error limpiando S3: {e}")
        import traceback
        traceback.print_exc()
        return 0

def create_gitignore():
    """Crear/actualizar .gitignore para archivos de desarrollo"""
    print("\n📝 ACTUALIZANDO .GITIGNORE")
    print("=" * 60)
    
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Environment
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# Testing and debugging files
test_*.py
debug_*.py
check_*.py
verify_*.py
cleanup_*.py

# Temporary files
*.tmp
*.temp
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Local development
uploads/
temp/
cache/

# Scripts backup
scripts_backup/

# Documentation files that are temporary
*.xlsx
*.docx
"""
    
    try:
        with open('.gitignore', 'w', encoding='utf-8') as f:
            f.write(gitignore_content)
        print("   ✅ .gitignore actualizado")
        return True
    except Exception as e:
        print(f"   ❌ Error actualizando .gitignore: {e}")
        return False

def main():
    """Ejecutar limpieza completa"""
    print("🧹 LIMPIEZA COMPLETA DEL PROYECTO")
    print("=" * 80)
    print("Esta operación eliminará:")
    print("• Archivos de desarrollo y testing no utilizados")
    print("• Todos los datos de la base de datos")
    print("• Todos los archivos del bucket S3")
    print("• Documentación temporal y archivos Excel")
    print("=" * 80)
    
    confirmation = input("\n¿Estás seguro de continuar? (escriba 'LIMPIAR TODO'): ")
    if confirmation != 'LIMPIAR TODO':
        print("❌ Operación cancelada")
        return
    
    # Ejecutar limpieza
    print(f"\n🚀 INICIANDO LIMPIEZA COMPLETA...")
    
    # 1. Limpiar archivos del proyecto
    removed_files, removed_dirs = clean_unused_files()
    
    # 2. Limpiar base de datos
    db_records_removed = clean_database()
    
    # 3. Limpiar S3
    s3_objects_removed = clean_s3()
    
    # 4. Actualizar .gitignore
    gitignore_updated = create_gitignore()
    
    # Resumen final
    print(f"\n🎯 RESUMEN FINAL DE LIMPIEZA")
    print("=" * 60)
    print(f"📁 Archivos eliminados: {removed_files}")
    print(f"📂 Directorios eliminados: {removed_dirs}")
    print(f"🗃️ Registros BD eliminados: {db_records_removed}")
    print(f"☁️ Objetos S3 eliminados: {s3_objects_removed}")
    print(f"📝 .gitignore: {'✅ Actualizado' if gitignore_updated else '❌ Error'}")
    
    print(f"\n✅ PROYECTO COMPLETAMENTE LIMPIO")
    print("🚀 Listo para producción con:")
    print("   • Base de datos vacía (secuencias en 1)")
    print("   • S3 bucket vacío")
    print("   • Solo archivos esenciales del proyecto")
    print("   • .gitignore actualizado")
    print("   • Sin archivos de debugging/testing")

if __name__ == "__main__":
    main()
