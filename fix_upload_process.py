#!/usr/bin/env python3
"""
Fix para el proceso de upload - agregar transferencia de archivos temporales a solución final
"""

import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath('.'))

# Leer el archivo routes.py
routes_file = 'app/main/routes.py'

print("🔧 Analizando el problema en routes.py...")

# Leer el contenido actual
with open(routes_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar la sección donde se guarda la solución
print("📍 Encontrando la sección add_solution donde se guarda la solución...")

# Encontrar la línea donde se crea la solución
solution_creation_line = "solution_id = db.add_solution(vehicle_info, solution_types)"

if solution_creation_line in content:
    print(f"✅ Encontrada línea de creación de solución")
    
    # Buscar qué hay después de la creación de la solución
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        if solution_creation_line.strip() in line.strip():
            print(f"📝 Línea {i+1}: {line.strip()}")
            
            # Mostrar las siguientes 20 líneas para ver el contexto
            print("\n🔍 Contexto después de la creación de solución:")
            for j in range(i+1, min(i+21, len(lines))):
                print(f"  {j+1:3d}: {lines[j]}")
            break
    
else:
    print("❌ No se encontró la línea de creación de solución")
    
print("\n🎯 PROBLEMA IDENTIFICADO:")
print("- Los archivos se suben con temp_solution_id")
print("- La solución se crea con solution_id real") 
print("- Los archivos NO se transfieren del temp_solution_id al solution_id real")
print("- Por eso el archivo ORI1 no está disponible para la solución final")

print("\n💡 SOLUCIÓN NECESARIA:")
print("- Después de crear la solución, transferir archivos de temp_solution_id a solution_id")
print("- Actualizar file_metadata con el solution_id correcto")
print("- Limpiar archivos temporales")
