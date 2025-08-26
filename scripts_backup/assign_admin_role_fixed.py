#!/usr/bin/env python3
"""
Script para asignar rol de administrador a un usuario específico
"""

import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar el directorio raíz al path para importar módulos de la app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Crear la app Flask para tener contexto
from app import create_app
app = create_app()

def assign_admin_role(email, role='admin'):
    """
    Asigna un rol específico a un usuario por email
    """
    with app.app_context():
        try:
            from app.auth.supabase_client import get_supabase_client
            
            print(f"🔍 Buscando usuario: {email}")
            
            # Obtener cliente admin
            admin_client = get_supabase_client()
            
            # Listar todos los usuarios para encontrar el ID
            response = admin_client.auth.admin.list_users()
            
            # Manejar diferentes formatos de respuesta
            if isinstance(response, list):
                users = response
            elif hasattr(response, 'users'):
                users = response.users
            elif hasattr(response, 'data'):
                users = response.data
            else:
                users = []
            
            # Buscar el usuario por email
            target_user = None
            for user in users:
                if user.email == email:
                    target_user = user
                    break
            
            if not target_user:
                print(f"❌ Usuario {email} no encontrado")
                return False
            
            print(f"✅ Usuario encontrado: {target_user.id}")
            print(f"📧 Email: {target_user.email}")
            print(f"📅 Creado: {target_user.created_at}")
            
            # Preparar los metadatos actualizados
            current_app_metadata = target_user.app_metadata or {}
            current_user_metadata = target_user.user_metadata or {}
            
            # Actualizar metadatos con el nuevo rol
            updated_app_metadata = {
                **current_app_metadata,
                'role': role
            }
            
            updated_user_metadata = {
                **current_user_metadata,
                'is_admin': role == 'admin'
            }
            
            print(f"🔄 Asignando rol: {role}")
            print(f"📋 App metadata: {updated_app_metadata}")
            print(f"📋 User metadata: {updated_user_metadata}")
            
            # Actualizar el usuario
            update_response = admin_client.auth.admin.update_user_by_id(
                target_user.id,
                {
                    'app_metadata': updated_app_metadata,
                    'user_metadata': updated_user_metadata
                }
            )
            
            print(f"✅ Usuario actualizado exitosamente")
            print(f"🆔 ID: {target_user.id}")
            print(f"📧 Email: {email}")
            print(f"👑 Nuevo rol: {role}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error asignando rol: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

def main():
    print("👑 ASIGNACIÓN DE ROL DE ADMINISTRADOR")
    print("=" * 50)
    
    # Email del usuario principal (ajustar según necesidad)
    admin_email = "jmadriz@protuner.cr"
    
    print(f"📧 Asignando rol de administrador a: {admin_email}")
    
    success = assign_admin_role(admin_email, 'admin')
    
    if success:
        print("\n✅ ROL ASIGNADO EXITOSAMENTE")
        print("🔄 Ejecuta check_admin_users.py para verificar los cambios")
    else:
        print("\n❌ ERROR EN LA ASIGNACIÓN")
        print("🔍 Revisa los logs para más detalles")

if __name__ == "__main__":
    main()
