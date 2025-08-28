#!/usr/bin/env python3
"""
Verificador del estado de la aplicación y métodos actualizados
"""

import os
import sys
import importlib.util
import inspect

def check_s3_storage_methods():
    """Verifica que los métodos transfer_temp_files y delete_temp_files existan"""
    try:
        # Importar el módulo S3FileStorage
        sys.path.append('.')
        from app.utils.s3_storage import S3FileStorage
        
        print("✅ S3FileStorage importado correctamente")
        
        # Verificar métodos
        methods = dir(S3FileStorage)
        
        if 'transfer_temp_files' in methods:
            print("✅ Método transfer_temp_files encontrado")
            
            # Obtener el código del método
            transfer_method = getattr(S3FileStorage, 'transfer_temp_files')
            source = inspect.getsource(transfer_method)
            if 'copy_object' in source and 'Metadata' in source:
                print("✅ Método transfer_temp_files tiene implementación completa")
            else:
                print("❌ Método transfer_temp_files no tiene implementación completa")
        else:
            print("❌ Método transfer_temp_files NO encontrado")
            
        if 'delete_temp_files' in methods:
            print("✅ Método delete_temp_files encontrado")
        else:
            print("❌ Método delete_temp_files NO encontrado")
            
    except ImportError as e:
        print(f"❌ Error importando S3FileStorage: {e}")
    except Exception as e:
        print(f"❌ Error verificando métodos: {e}")

def check_routes_implementation():
    """Verifica que las rutas tengan la implementación actualizada"""
    try:
        from app.main.routes import bp
        print("✅ Rutas importadas correctamente")
        
        # Buscar en el archivo de rutas
        routes_file = 'app/main/routes.py'
        with open(routes_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'transfer_temp_files' in content:
            print("✅ transfer_temp_files está en routes.py")
        else:
            print("❌ transfer_temp_files NO está en routes.py")
            
        if 'temp_solution_id' in content:
            print("✅ temp_solution_id está en routes.py")
        else:
            print("❌ temp_solution_id NO está en routes.py")
            
    except Exception as e:
        print(f"❌ Error verificando rutas: {e}")

def check_running_processes():
    """Verifica procesos Python corriendo"""
    import subprocess
    try:
        # Buscar procesos Python
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], 
                              capture_output=True, text=True, shell=True)
        
        print("\n🔍 PROCESOS PYTHON ACTIVOS:")
        print(result.stdout)
        
        # Buscar específicamente Flask/Gunicorn
        result2 = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe', '/V'], 
                               capture_output=True, text=True, shell=True)
        
        lines = result2.stdout.split('\n')
        flask_processes = [line for line in lines if 'python' in line.lower()]
        
        if flask_processes:
            print("\n📋 PROCESOS RELACIONADOS CON PYTHON:")
            for process in flask_processes[:5]:  # Mostrar solo los primeros 5
                print(process)
        
    except Exception as e:
        print(f"❌ Error verificando procesos: {e}")

def main():
    print("🔍 VERIFICACIÓN DEL ESTADO DE LA APLICACIÓN\n")
    print("=" * 60)
    
    print("\n1️⃣ VERIFICANDO MÉTODOS S3:")
    check_s3_storage_methods()
    
    print("\n2️⃣ VERIFICANDO RUTAS:")
    check_routes_implementation()
    
    print("\n3️⃣ VERIFICANDO PROCESOS:")
    check_running_processes()
    
    print("\n" + "=" * 60)
    print("🎯 RECOMENDACIONES:")
    print("- Si falta transfer_temp_files: El código no se cargó correctamente")
    print("- Si hay múltiples procesos Python: Puede que la app anterior siga corriendo")
    print("- Solución: Reiniciar completamente todos los procesos Python")

if __name__ == "__main__":
    main()
