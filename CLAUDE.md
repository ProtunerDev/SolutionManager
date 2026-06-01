# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

**SolutionManager** is a Flask web application for automotive ECU (Engine Control Unit) solution management. It allows technical professionals to upload, compare, and manage ECU binary firmware files with version control, modification tracking, and role-based access.

## Commands

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server (debug mode, port 5000)
python run.py

# Run production server with Waitress
python run_production.py
```

### Database Setup
```bash
# Initialize PostgreSQL schema
psql -U postgres -d SolutionManager -f app/database/schema.sql
```

### Internationalization (i18n)
```bash
# Extract translatable strings
pybabel extract -F babel.cfg -o app/translations/messages.pot .

# Update existing translation catalogs
pybabel update -i app/translations/messages.pot -d app/translations

# Compile translations
pybabel compile -d app/translations
```

### Testing
```bash
pytest
pytest tests/test_specific.py  # single test file
pytest --cov=app tests/        # with coverage
```

## Environment Configuration

The app loads `.env` for development and `.env.production` for production (controlled by `FLASK_ENV`). Required variables:

```env
SECRET_KEY=
APP_URL=http://localhost:5000

# PostgreSQL
DB_HOST=localhost
DB_NAME=SolutionManager
DB_USER=postgres
DB_PASSWORD=
DB_PORT=5432

# Supabase (authentication)
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# Storage: 'local' for dev, 's3' for production
STORAGE_TYPE=local
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_BUCKET=
AWS_S3_REGION=us-east-1
```

## Architecture

### Application Factory
`app/__init__.py` creates the Flask app using the factory pattern (`create_app()`). It initializes Flask-Login, Flask-WTF CSRF protection, Flask-Babel (i18n), Supabase auth client, and registers blueprints.

### Blueprints
- **`app/main/`** — All core business logic: home dashboard, ECU file upload, binary file comparison, solution CRUD, and file download routes. The `routes.py` here is the largest file.
- **`app/auth/`** — Authentication via Supabase: login/logout, password reset, user invitation, profile management. Mounted at `/auth`.

### Authentication Model
Authentication is delegated entirely to **Supabase**. `app/auth/supabase_client.py` wraps the Supabase SDK. `app/auth/models.py` defines `SupabaseUser` which implements Flask-Login's `UserMixin`. There is no local user table for auth — Supabase manages credentials and sessions.

### Storage Strategy (Factory Pattern)
`app/utils/storage_factory.py` → `get_file_storage()` returns either:
- `S3FileStorage` (`app/utils/s3_storage.py`) when `STORAGE_TYPE=s3`
- `PostgreSQLFileStorage` (`app/utils/file_storage.py`) when `STORAGE_TYPE=local`

Both implement the same interface. Always use `get_file_storage()` when reading/writing ECU files — never instantiate storage directly.

### Database Layer
`app/database/db_manager.py` — `DatabaseManager` class manages all PostgreSQL interactions via `psycopg2` (no ORM). Uses parameterized queries throughout. The schema is in `app/database/schema.sql`.

Key tables: `vehicle_info`, `solutions`, `solution_types`, `file_metadata`, `differences_metadata`, `field_dependencies`, `field_values`.

### Binary Comparison
`app/utils/binary_handler.py` — `BinaryHandler` performs byte-level diff between ECU binary files (ORI vs MOD). Differences are stored in `differences_metadata`.

### Internationalization
`app/i18n.py` wraps Flask-Babel. Use `_()` and `_n()` for translations in Python code. Templates receive these functions via context processor. Translations live in `app/translations/es/LC_MESSAGES/`.

### Allowed File Types
ECU binary uploads are restricted to: `.bin`, `.ori`, `.mod`, `.dtf`

## Deployment

- **Heroku / Procfile**: `web: waitress-serve --port=$PORT run:app`
- **nixpacks (Railway/Render)**: `cmd = "gunicorn run:app"` — see `nixpacks.toml`
- Python 3.12+ required
