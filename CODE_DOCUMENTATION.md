# 📚 Documentación de Código

## Estructura Principal

```
SolutionManager/
├── app/
│   ├── __init__.py           # Inicialización de la app Flask y Babel
│   ├── i18n.py               # Lógica de internacionalización
│   ├── models.py             # Modelos de datos principales
│   ├── api/                  # Endpoints REST y lógica de API
│   ├── auth/                 # Autenticación y gestión de usuarios
│   ├── database/             # Conexión y gestión de base de datos
│   ├── main/                 # Rutas y lógica principal de la app
│   ├── static/               # Archivos estáticos (CSS, JS, imágenes)
│   ├── templates/            # Templates Jinja2 para la UI
│   ├── translations/         # Archivos de traducción (Flask-Babel)
│   └── utils/                # Utilidades y helpers
├── config.py                 # Configuración global
├── requirements.txt          # Dependencias Python
├── run.py                    # Script de arranque en desarrollo
├── run_production.py         # Script de arranque en producción
├── Procfile, nixpacks.toml   # Configuración de despliegue
├── README.md, CHANGELOG.md   # Documentación principal
```

## Principales Componentes

- **app/__init__.py**: Inicializa Flask, Babel y configura el contexto global.
- **app/i18n.py**: Detecta y gestiona el idioma del usuario.
- **app/models.py**: Define los modelos de datos (Soluciones, Usuarios, Archivos).
- **app/api/routes.py**: Endpoints para integración externa y API REST.
- **app/auth/routes.py**: Lógica de login, registro, recuperación de contraseña.
- **app/database/db_manager.py**: Conexión y operaciones con la base de datos.
- **app/main/routes.py**: Rutas principales, lógica de negocio y renderizado de templates.
- **app/templates/**: Templates Jinja2 para cada página (home, add_solution, modify_file, etc).
- **app/static/**: Archivos estáticos para la UI (CSS, JS, imágenes).
- **app/translations/**: Archivos .po/.mo para internacionalización.
- **config.py**: Configuración de Flask, Babel, base de datos y almacenamiento.

## Convenciones de Código
- Uso de Blueprints para modularidad.
- Variables y funciones en inglés, textos de UI traducibles con `{{ _('texto') }}`.
- Manejo de errores y mensajes con Flask flash y traducción.
- Separación clara entre lógica de negocio, presentación y almacenamiento.
- Pruebas unitarias y de integración recomendadas en `tests/` (si se habilita).

## Ejemplo de Flujo Principal
1. Usuario accede a la app y selecciona idioma.
2. Se autentica y navega por las soluciones.
3. Puede cargar, comparar y modificar archivos ECU.
4. Todos los textos y mensajes se muestran en el idioma seleccionado.
5. Los cambios y acciones se registran en la base de datos y almacenamiento seguro.
