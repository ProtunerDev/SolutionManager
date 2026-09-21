#!/usr/bin/env python3
"""
SolutionManager – Importador en lote
======================================
Vigila las subcarpetas de marca dentro de inbox/ e importa soluciones
automáticamente cada 2 minutos.

CONTROL ON/OFF
--------------
  Para PAUSAR:   crea el archivo  inbox/PAUSA   (puede estar vacío)
  Para REANUDAR: elimina el archivo inbox/PAUSA

ESTRUCTURA DE CARPETAS
-----------------------
  inbox/
    PAUSA                    ←  (opcional) pausar el watcher
    HINO/                    ←  carpeta de marca
      Hino300_SW0001/        ←  una subcarpeta = una solución
        original.ori
        modificado.mod
        info.txt
      Hino500_SW0002/
        ...
    TOYOTA/                  ←  próxima marca (cuando toque)
      ...

  processed/                 ←  importadas OK (misma estructura de marca)
    HINO/
      Hino300_SW0001/
  errors/                    ←  con error (para revisar)
    HINO/
      ...

  batch_import.log           ←  log completo

USO
----
  # Modo vigilancia continua (default 2 min)
  python batch_importer.py --inbox ./inbox

  # Contra producción (usa .env.production)
  python batch_importer.py --inbox ./inbox --env production

  # Procesar lo que hay y salir sin vigilancia
  python batch_importer.py --inbox ./inbox --once
"""

import os
import sys
import time
import shutil
import logging
import argparse
import configparser
from pathlib import Path

# ─── Configuración ───────────────────────────────────────────────────────────

POLL_INTERVAL_SECONDS = 120   # revisar cada 2 minutos
PAUSE_FILENAME        = 'PAUSA'

SOLUTION_TYPES_KEYS = [
    'stage_1', 'stage_2', 'pop_and_bangs', 'vmax', 'dtc_off',
    'full_decat', 'immo_off', 'evap_off', 'tva', 'egr_off',
    'dpf_off', 'egr_dpf_off', 'adblue_off', 'egr_dpf_adblue_off',
]

# ─── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('batch_import.log', encoding='utf-8'),
    ],
)
logger = logging.getLogger('batch_importer')


# ─── Parseo de info.txt ───────────────────────────────────────────────────────

def parse_info_txt(info_path: Path):
    cfg = configparser.ConfigParser()
    cfg.read(str(info_path), encoding='utf-8')

    if 'vehiculo' not in cfg:
        raise ValueError("info.txt no contiene sección [vehiculo]")

    v = cfg['vehiculo']
    year_raw = v.get('year', '').strip()
    vehicle_info = {
        'vehicle_type':           v.get('vehicle_type', '').strip(),
        'make':                   v.get('make', '').strip(),
        'model':                  v.get('model', '').strip(),
        'engine':                 v.get('engine', '').strip(),
        'year':                   year_raw if year_raw else '0',
        'hardware_number':        v.get('hardware_number', '').strip() or 'N/A',
        'software_number':        v.get('software_number', '').strip() or 'N/A',
        'software_update_number': v.get('software_update_number', '').strip(),
        'ecu_type':               v.get('ecu_type', '').strip(),
        'transmission_type':      v.get('transmission_type', '').strip() or 'Unknown',
    }

    solution_types = {k: False for k in SOLUTION_TYPES_KEYS}
    solution_types['description'] = ''

    if 'servicios' in cfg:
        s = cfg['servicios']
        for key in SOLUTION_TYPES_KEYS:
            raw = s.get(key, 'false').strip().lower()
            solution_types[key] = raw in ('true', '1', 'yes', 'si', 'sí')
        solution_types['description'] = s.get('description', '').strip()

    return vehicle_info, solution_types


# ─── Detección de archivos ────────────────────────────────────────────────────

def find_solution_files(folder: Path):
    """Encuentra ORI1, MOD1 e info.txt dentro de una carpeta de solución."""
    ori1 = mod1 = info = None
    bins = []

    for f in sorted(folder.iterdir()):
        if not f.is_file():
            continue
        name = f.name.lower()
        ext  = f.suffix.lower()

        if ext == '.txt':
            info = info or f
        elif ext == '.ori':
            ori1 = ori1 or f
        elif ext == '.mod':
            mod1 = mod1 or f
        elif ext == '.bin':
            bins.append(f)
        elif ext == '.dtf':
            if ori1 is None:
                ori1 = f
            elif mod1 is None:
                mod1 = f

    # Fallback: dos .bin ordenados alfabéticamente
    if ori1 is None and len(bins) >= 1:
        ori1 = bins[0]
    if mod1 is None and len(bins) >= 2:
        mod1 = bins[1]

    return ori1, mod1, info


def is_complete(folder: Path) -> bool:
    ori1, mod1, info = find_solution_files(folder)
    return bool(ori1 and mod1 and info)


# ─── Importación de una solución ─────────────────────────────────────────────

def import_solution(folder: Path, brand: str, app, user_id=None) -> bool:
    logger.info(f"  ▶  [{brand}] {folder.name}")

    ori1_path, mod1_path, info_path = find_solution_files(folder)

    for label, path in [("ORI1", ori1_path), ("MOD1", mod1_path), ("info.txt", info_path)]:
        if not path:
            logger.error(f"     ✗ No se encontró {label}")
            return False

    try:
        vehicle_info, solution_types = parse_info_txt(info_path)
    except ValueError as e:
        logger.error(f"     ✗ Error en info.txt: {e}")
        return False

    logger.info(
        f"     Vehículo: {vehicle_info['make']} {vehicle_info['model']} "
        f"{vehicle_info['year']} | HW={vehicle_info['hardware_number']}"
    )

    # Comparación binaria (no necesita contexto Flask)
    try:
        from app.utils.binary_handler import BinaryHandler
        bh = BinaryHandler()
        bh.set_read_size(8)
        differences_raw = bh.compare_files(str(ori1_path), str(mod1_path))
    except Exception as e:
        logger.error(f"     ✗ Comparación binaria fallida: {e}")
        return False

    logger.info(f"     Diferencias: {len(differences_raw)}")

    # Contexto Flask: BD + storage
    with app.app_context():
        from app.database.db_manager import DatabaseManager
        from app.utils.storage_factory import get_file_storage

        try:
            with DatabaseManager() as db:
                solution_id = db.add_solution(vehicle_info, solution_types, created_by=user_id)
        except Exception as e:
            logger.error(f"     ✗ Error en BD: {e}")
            return False

        if not solution_id:
            logger.error(f"     ✗ BD no retornó ID")
            return False

        logger.info(f"     ✓ BD → ID={solution_id}")

        try:
            storage = get_file_storage()
            with open(ori1_path, 'rb') as f:
                ori1_data = f.read()
            with open(mod1_path, 'rb') as f:
                mod1_data = f.read()

            if not storage.store_file(solution_id, 'ori1', ori1_path.name, ori1_data):
                logger.error(f"     ✗ Falló subida ORI1")
                return False
            if not storage.store_file(solution_id, 'mod1', mod1_path.name, mod1_data):
                logger.error(f"     ✗ Falló subida MOD1")
                return False
        except Exception as e:
            logger.error(f"     ✗ Error subiendo archivos: {e}")
            return False

        logger.info(f"     ✓ Archivos subidos")

        try:
            diffs = [
                {'memory_address': a, 'ori1_value': v1, 'mod1_value': v2, 'bit_size': 8}
                for a, v1, v2 in differences_raw
            ]
            if not storage.store_differences(solution_id, diffs):
                logger.error(f"     ✗ Falló guardado de diferencias")
                return False
        except Exception as e:
            logger.error(f"     ✗ Error guardando diferencias: {e}")
            return False

        logger.info(f"     ✓ Diferencias guardadas")
        logger.info(f"     ✅ Importada correctamente → ID={solution_id}")
        return True


# ─── Escaneo de una ronda ────────────────────────────────────────────────────

def scan_inbox(inbox: Path, processed: Path, errors: Path, app, seen: set):
    """
    Recorre inbox/MARCA/SOLUCION/.
    Procesa carpetas completas que no hayan sido vistas antes.
    Retorna (importadas, errores) de esta ronda.
    """
    ok = err = 0

    # Iterar sobre carpetas de marca (HINO, TOYOTA, etc.)
    for brand_dir in sorted(inbox.iterdir()):
        if not brand_dir.is_dir():
            continue
        brand = brand_dir.name.upper()

        # Iterar sobre subcarpetas de solución
        for sol_dir in sorted(brand_dir.iterdir()):
            if not sol_dir.is_dir():
                continue

            key = f"{brand}/{sol_dir.name}"
            if key in seen:
                continue
            if not is_complete(sol_dir):
                continue

            # Pequeña espera para asegurar que la escritura terminó
            time.sleep(1)

            success = import_solution(sol_dir, brand, app)
            seen.add(key)

            # Mover a processed/ o errors/ manteniendo la subcarpeta de marca
            dest_base = (processed if success else errors) / brand
            dest_base.mkdir(parents=True, exist_ok=True)
            dest = dest_base / sol_dir.name
            if dest.exists():
                dest = dest_base / f"{sol_dir.name}_{int(time.time())}"
            shutil.move(str(sol_dir), str(dest))

            if success:
                ok += 1
            else:
                err += 1

    return ok, err


# ─── Watcher ─────────────────────────────────────────────────────────────────

def run_watcher(inbox: Path, processed: Path, errors: Path, app):
    pause_file = inbox / PAUSE_FILENAME
    seen: set  = set()
    was_paused = False

    logger.info("=" * 62)
    logger.info("  SolutionManager – Importador en lote  |  Vigilancia activa")
    logger.info("=" * 62)
    logger.info(f"  Inbox:     {inbox}")
    logger.info(f"  Intervalo: {POLL_INTERVAL_SECONDS // 60} min")
    logger.info(f"  PAUSAR:    crea el archivo  {pause_file}")
    logger.info(f"  REANUDAR:  elimina el archivo {pause_file}")
    logger.info(f"  DETENER:   Ctrl+C")
    logger.info("=" * 62 + "\n")

    while True:
        try:
            # ── Control ON/OFF ──────────────────────────────────────────
            if pause_file.exists():
                if not was_paused:
                    logger.info("⏸  PAUSADO  (elimina inbox/PAUSA para reanudar)")
                    was_paused = True
                time.sleep(10)   # revisión rápida mientras pausado
                continue

            if was_paused:
                logger.info("▶  REANUDADO")
                was_paused = False

            # ── Escaneo ─────────────────────────────────────────────────
            ok, err = scan_inbox(inbox, processed, errors, app, seen)

            if ok or err:
                logger.info(f"─── Ronda: {ok} importadas | {err} con error ───\n")

            logger.info(
                f"💤  Próxima revisión en {POLL_INTERVAL_SECONDS // 60} min  "
                f"(Ctrl+C para detener | crea inbox/PAUSA para pausar)"
            )

        except KeyboardInterrupt:
            logger.info("\n  Watcher detenido por el usuario.")
            break
        except Exception as e:
            logger.error(f"  Error inesperado en el watcher: {e}")

        time.sleep(POLL_INTERVAL_SECONDS)


# ─── One-shot ────────────────────────────────────────────────────────────────

def run_once(inbox: Path, processed: Path, errors: Path, app):
    logger.info("  Modo one-shot: procesando inbox y saliendo...")
    seen: set = set()
    ok, err = scan_inbox(inbox, processed, errors, app, seen)
    logger.info("=" * 62)
    logger.info(f"  Resultado: {ok} importadas | {err} con error")
    logger.info("=" * 62)


# ─── Entrypoint ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='SolutionManager – Importador en lote de soluciones ECU'
    )
    parser.add_argument('--inbox', required=True, help='Ruta a la carpeta inbox')
    parser.add_argument(
        '--env', default='development',
        choices=['development', 'production'],
        help='Entorno (default: development)'
    )
    parser.add_argument(
        '--once', action='store_true',
        help='Procesar inbox actual y salir sin vigilancia'
    )
    args = parser.parse_args()

    os.environ['FLASK_ENV'] = args.env

    project_root = Path(__file__).parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from app import create_app
    from config import config as config_map
    app = create_app(config_map[args.env])

    inbox     = Path(args.inbox).resolve()
    processed = inbox.parent / 'processed'
    errors    = inbox.parent / 'errors'

    for d in (inbox, processed, errors):
        d.mkdir(parents=True, exist_ok=True)

    if args.once:
        run_once(inbox, processed, errors, app)
    else:
        run_watcher(inbox, processed, errors, app)


if __name__ == '__main__':
    main()
