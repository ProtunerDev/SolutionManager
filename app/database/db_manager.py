"""
Database Manager Module

This module handles all database operations for the Vehicle Binary Tool.
It provides a robust interface for:
- Database connection management with context support
- Schema initialization and updates
- Binary file data storage and retrieval
- Vehicle configuration management
- Solution tracking and validation

The module uses PostgreSQL for data storage and implements proper transaction
handling for data integrity.
"""

import psycopg2
from psycopg2 import sql
from psycopg2.extras import DictCursor
from pathlib import Path
import os
import logging
from typing import Optional, List, Dict, Any, Union, Tuple
from flask import current_app
import pandas as pd

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Manages database operations with transaction support.

    This class provides a complete interface for database operations including:
    - Connection management with context support
    - Schema initialization
    - Binary file storage and retrieval
    - Vehicle configuration management
    - Field dependency tracking

    Attributes:
        db_params (Dict): PostgreSQL connection parameters
        conn (Optional[psycopg2.connection]): Database connection
        cursor (Optional[psycopg2.cursor]): Database cursor
        _in_transaction (bool): Transaction state tracking
    """

    def __init__(self, db_params=None):
        """
        Initialize database manager for PostgreSQL only.
        """
        self.db_params = db_params or {
            "host": current_app.config.get('DB_HOST', 'localhost'),
            "port": current_app.config.get('DB_PORT', 5432),
            "database": current_app.config.get('DB_NAME', 'SolutionManager'),
            "user": current_app.config.get('DB_USER', 'postgres'),
            "password": current_app.config.get('DB_PASSWORD', 'Jmadriz63')
        }
        logger.debug(f"DatabaseManager initialized with connection to PostgreSQL database: {self.db_params['database']}")
        self.conn = None
        self.cursor = None
        self._in_transaction = False

    def connect(self) -> Optional['DatabaseManager']:
        """
        Establish database connection and initialize if needed.

        Returns:
            DatabaseManager instance if connection successful, None otherwise
        """
        try:
            if not self.conn:
                logger.debug(f"Connecting to PostgreSQL database: {self.db_params['database']}")
                self.conn = psycopg2.connect(**self.db_params)
                if not self.conn:
                    raise Exception("Failed to establish database connection")
                self.cursor = self.conn.cursor(cursor_factory=DictCursor)
                if not self.cursor:
                    self.conn.close()
                    self.conn = None
                    raise Exception("Failed to create database cursor")
                self.cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'solutions')")
                table_exists = self.cursor.fetchone()[0]
                if not table_exists:
                    logger.debug("Database tables not found, initializing schema")
                    if not self.initialize_database():
                        raise Exception("Failed to initialize database schema")
                logger.debug("Database connection established successfully")
            return self
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            if self.conn:
                try:
                    self.conn.close()
                except:
                    pass
                self.conn = None
            self.cursor = None
            return None

    def __enter__(self) -> Optional['DatabaseManager']:
        logger.debug("Entering database context")
        self._in_transaction = True
        db = self.connect()
        if not db or not db.conn or not db.cursor:
            raise Exception("Failed to establish database connection in context")
        return db

    def __exit__(self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Any) -> bool:
        if exc_type is None and self.conn and self._in_transaction:
            logger.debug("Committing database transaction")
            self.conn.commit()
        if exc_type:
            logger.error(f"Error in database context: {exc_val}")
            if self.conn and self._in_transaction:
                self.conn.rollback()
        self._in_transaction = False
        return False

    def close(self):
        """Close database connection and clean up resources."""
        if self.conn:
            logger.debug("Closing database connection")
            if self._in_transaction:
                self.conn.commit()
            self.conn.close()
            self.conn = None
            self.cursor = None
            self._in_transaction = False

    def initialize_database(self) -> bool:
        """
        Initialize database with schema and run migrations (PostgreSQL only).
        """
        if not self.conn or not self.cursor:
            logger.error("Cannot initialize database: No active connection")
            return False
        try:
            schema_path = Path(current_app.root_path) / 'database' / 'schema.sql'
            logger.debug(f"Reading schema from: {schema_path}")
            if not schema_path.exists():
                logger.error(f"Schema file not found: {schema_path}")
                return False
            with open(schema_path, 'r') as f:
                schema = f.read()
            self.cursor.execute('BEGIN')
            try:
                logger.debug("Executing schema")
                self.cursor.execute(schema)
                self.cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
                tables = {row[0] for row in self.cursor.fetchall()}
                required_tables = {
                    'vehicle_info', 'solutions', 'solution_types',
                    'field_dependencies', 'field_values', 'file_differences', 'users'
                }
                if not required_tables.issubset(tables):
                    missing = required_tables - tables
                    logger.error(f"Schema initialization failed. Missing tables: {missing}")
                    raise Exception(f"Failed to create tables: {missing}")
                migrations_dir = Path(current_app.root_path) / 'database' / 'migrations'
                if migrations_dir.exists():
                    for migration_file in sorted(migrations_dir.glob('*.sql')):
                        logger.debug(f"Running migration: {migration_file}")
                        with open(migration_file, 'r') as f:
                            migration_sql = f.read()
                            self.cursor.execute(migration_sql)
                self.conn.commit()
                logger.debug("Database initialized successfully")
                return True
            except Exception as e:
                self.conn.rollback()
                logger.error(f"Failed to initialize schema: {e}")
                raise
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            if self.conn:
                try:
                    self.conn.rollback()
                except:
                    pass
            return False

    def store_file_differences(self, solution_id: int, differences: List[Dict[str, Any]]) -> bool:
        """
        Store differences between ORI1 and MOD1 files.

        Args:
            solution_id: Associated solution ID
            differences: List of dictionaries containing:
                - memory_address: Address where difference was found
                - ori1_value: Original value from ORI1
                - mod1_value: Modified value from MOD1
                - bit_size: Size of the values (8, 16, or 32)

        Returns:
            bool: True if storage successful, False otherwise
        """
        if not self.conn or not self.cursor:
            logger.error("Cannot store file differences: No active connection")
            return False

        try:
            self.cursor.execute('''
                SELECT id FROM solutions WHERE id = %s
            ''', (solution_id,))
            if not self.cursor.fetchone():
                logger.error(f"Solution {solution_id} not found")
                return False

            self.cursor.execute('BEGIN')

            try:
                for diff in differences:
                    bit_size = diff['bit_size']
                    if bit_size not in [8, 16, 32]:
                        raise ValueError(f"Invalid bit size: {bit_size}")

                    bytes_per_value = bit_size // 8
                    try:
                        ori1_bytes = diff['ori1_value'].to_bytes(bytes_per_value, byteorder='little')
                        mod1_bytes = diff['mod1_value'].to_bytes(bytes_per_value, byteorder='little')
                    except (OverflowError, AttributeError) as e:
                        raise ValueError(f"Invalid value for {bit_size}-bit storage: {e}")

                    self.cursor.execute('''
                        INSERT INTO file_differences (
                            solution_id, memory_address, ori1_value, 
                            mod1_value, bit_size
                        ) VALUES (%s, %s, %s, %s, %s)
                    ''', (
                        solution_id, diff['memory_address'],
                        psycopg2.Binary(ori1_bytes), psycopg2.Binary(mod1_bytes), bit_size
                    ))

                self.conn.commit()
                logger.debug(f"Stored {len(differences)} differences for solution {solution_id}")
                return True

            except Exception as e:
                self.conn.rollback()
                logger.error(f"Failed to store differences: {e}")
                raise

        except Exception as e:
            logger.error(f"Error storing file differences: {e}")
            if self.conn:
                try:
                    self.conn.rollback()
                except:
                    pass
            return False

    def get_ori1_data(self, solution_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve Ori1 file data from the database.

        Args:
            solution_id: Solution ID to retrieve data for

        Returns:
            Optional[Dict]: Dictionary with 'data' and 'bit_size' if found
        """
        if not self.conn or not self.cursor:
            logger.error("Cannot retrieve Ori1 file: No active connection")
            return None

        try:
            self.cursor.execute('''
                SELECT file_data, read_size FROM ori1_files
                WHERE solution_id = %s
                ORDER BY created_at DESC LIMIT 1
            ''', (solution_id,))
            row = self.cursor.fetchone()
            if row:
                data_bytes, bit_size = row
                if bit_size == 8:
                    data = list(data_bytes)
                elif bit_size == 16:
                    data = [int.from_bytes(data_bytes[i:i+2], 'little')
                           for i in range(0, len(data_bytes), 2)]
                elif bit_size == 32:
                    data = [int.from_bytes(data_bytes[i:i+4], 'little')
                           for i in range(0, len(data_bytes), 4)]
                else:
                    raise ValueError(f"Unsupported bit size: {bit_size}")

                return {
                    'data': data,
                    'bit_size': bit_size
                }
            return None
        except Exception as e:
            logger.error(f"Error retrieving Ori1 file: {e}")
            if self.conn:
                try:
                    self.conn.rollback()
                except:
                    pass
            return None

    def add_solution(self, vehicle_info: Dict[str, Any], solution_types: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """
        Add a new solution with vehicle information and optional solution types.

        Args:
            vehicle_info: Dictionary containing vehicle configuration
            solution_types: Optional dictionary containing solution type flags and description

        Returns:
            Optional[int]: Solution ID if successful, None otherwise (CAMBIÓ DE UUID A INT)
        """
        if not self.conn or not self.cursor:
            logger.error("Cannot add solution: No active connection")
            return None

        try:
            info = vehicle_info.copy()

            if 'year' in info:
                try:
                    year_value = float(str(info['year']).strip())  # Handle potential whitespace
                    info['year'] = int(year_value)  # Convert to integer, dropping any decimal
                except (ValueError, TypeError):
                    logger.error(f"Invalid year value: {info['year']}")
                    return None

            for k, v in info.items():
                if k != 'year':
                    info[k] = str(v).strip()  # Clean any whitespace

            logger.debug(f"Storing solution with vehicle info: {info}")

            self.cursor.execute('''
                INSERT INTO vehicle_info (
                    vehicle_type, make, model, engine, year,
                    hardware_number, software_number, software_update_number,
                    ecu_type, transmission_type
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                info['vehicle_type'], info['make'],
                info['model'], info['engine'],
                info['year'], info['hardware_number'],
                info['software_number'], info['software_update_number'],
                info['ecu_type'], info['transmission_type']
            ))
            vehicle_info_id = self.cursor.fetchone()[0]

            self.cursor.execute('''
                INSERT INTO solutions (vehicle_info_id, status)
                VALUES (%s, 'active')
                RETURNING id
            ''', (vehicle_info_id,))
            solution_id = self.cursor.fetchone()[0]

            if solution_types:
                self.cursor.execute('''
                    INSERT INTO solution_types (
                        solution_id, stage_1, stage_2, pop_and_bangs, vmax,
                        dtc_off, full_decat, immo_off, evap_off, tva,
                        egr_off, dpf_off, egr_dpf_off, adblue_off,
                        egr_dpf_adblue_off, description
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    solution_id,
                    solution_types.get('stage_1', False),
                    solution_types.get('stage_2', False),
                    solution_types.get('pop_and_bangs', False),
                    solution_types.get('vmax', False),
                    solution_types.get('dtc_off', False),
                    solution_types.get('full_decat', False),
                    solution_types.get('immo_off', False),
                    solution_types.get('evap_off', False),
                    solution_types.get('tva', False),
                    solution_types.get('egr_off', False),
                    solution_types.get('dpf_off', False),
                    solution_types.get('egr_dpf_off', False),
                    solution_types.get('adblue_off', False),
                    solution_types.get('egr_dpf_adblue_off', False),
                    solution_types.get('description', '')
                ))

            self.conn.commit()
            return solution_id
        except Exception as e:
            logger.error(f"Error adding solution: {e}")
            if self.conn:
                try:
                    self.conn.rollback()
                except:
                    pass
            return None

    def get_field_values(self, field_name, filters=None):
        df = pd.read_excel('app/static/Dropdowninfo.xlsx')
        df.columns = [c.strip().lower() for c in df.columns]
        if field_name not in df.columns:
            return []
        if field_name != 'vehicle_type' and filters:
            for key, value in filters.items():
                if key in df.columns and value:
                    df = df[df[key] == value]
        values = df[field_name].dropna().unique().tolist()
        return values

    def get_child_fields(self, parent_field: str) -> List[str]:
        """
        Get child fields for a given parent field.

        Args:
            parent_field: Parent field name

        Returns:
            List[str]: List of child field names
        """
        if not self.conn or not self.cursor:
            logger.error("Cannot get child fields: No active connection")
            return []

        try:
            self.cursor.execute('''
                SELECT child_field FROM field_dependencies
                WHERE parent_field = %s
            ''', (parent_field,))
            return [row[0] for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting child fields: {e}")
            if self.conn:
                try:
                    self.conn.rollback()
                except:
                    pass
            return []

    def get_dependent_fields(self) -> Dict[str, List[str]]:
        """
        Return the hierarchical field dependencies.

        Returns:
            Dict[str, List[str]]: Dictionary mapping fields to their dependencies
        """
        if not self.conn or not self.cursor:
            logger.error("Cannot get dependent fields: No active connection")
            return {}

        try:
            self.cursor.execute('SELECT parent_field, child_field FROM field_dependencies')
            dependencies = {}
            for parent, child in self.cursor.fetchall():
                if child not in dependencies:
                    dependencies[child] = []
                dependencies[child].append(parent)
            return dependencies
        except Exception as e:
            logger.error(f"Error getting dependent fields: {e}")
            if self.conn:
                try:
                    self.conn.rollback()
                except:
                    pass
            return {}

    def search_solutions(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search solutions with optional filters.

        Args:
            filters: Optional dictionary of search criteria

        Returns:
            List[Dict]: List of matching solutions with solution types
        """
        if not self.conn or not self.cursor:
            logger.error("Cannot search solutions: No active connection")
            return []

        try:
            query = '''
                SELECT v.*, st.stage_1, st.stage_2, st.pop_and_bangs, st.vmax,
                       st.dtc_off, st.full_decat, st.immo_off, st.evap_off, st.tva,
                       st.egr_off, st.dpf_off, st.egr_dpf_off, st.adblue_off,
                       st.egr_dpf_adblue_off, st.description
                FROM solutions s
                JOIN vehicle_info v ON s.vehicle_info_id = v.id
                LEFT JOIN solution_types st ON s.id = st.solution_id
                WHERE 1=1
            '''
            params = []
            if filters:
                for field, value in filters.items():
                    if field in ['stage_1', 'stage_2', 'pop_and_bangs', 'vmax',
                               'dtc_off', 'full_decat', 'immo_off', 'evap_off', 'tva',
                               'egr_off', 'dpf_off', 'egr_dpf_off', 'adblue_off',
                               'egr_dpf_adblue_off']:
                        query += f" AND st.{field} = %s"
                    else:
                        query += f" AND v.{field} = %s"
                    params.append(value)

            self.cursor.execute(query, params)
            columns = [desc[0] for desc in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error searching solutions: {e}")
            if self.conn:
                try:
                    self.conn.rollback()
                except:
                    pass
            return []

    def update_solution(self, solution_id: int, updates: Dict[str, Any]) -> bool:
        """
        Update an existing solution.

        Args:
            solution_id: ID of solution to update
            updates: Dictionary of fields to update

        Returns:
            bool: True if update successful, False otherwise
        """
        if not self.conn or not self.cursor:
            logger.error("Cannot update solution: No active connection")
            return False

        try:
            set_clause = ", ".join([f"{key} = %s" for key in updates.keys()])
            query = f"UPDATE vehicle_info SET {set_clause} WHERE id = %s"
            params = list(updates.values()) + [solution_id]

            self.cursor.execute(query, params)
            self.conn.commit()
            logger.debug(f"Updated solution with ID: {solution_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating solution: {e}")
            if self.conn:
                try:
                    self.conn.rollback()
                except:
                    pass
            return False

    def add_solution_types(self, solution_id: int, solution_types: Dict[str, Any]) -> bool:
        """
        Add or update solution types in the database.

        Args:
            solution_id: ID of the solution to associate the types with
            solution_types: Dictionary of solution types and their values

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.conn or not self.cursor:
            logger.error("Cannot add solution types: No active database connection")
            return False

        try:
            self.cursor.execute('''
                INSERT INTO solution_types (
                    solution_id, stage_1, stage_2, pop_and_bangs, vmax,
                    dtc_off, full_decat, immo_off, evap_off, tva,
                    egr_off, dpf_off, egr_dpf_off, adblue_off,
                    egr_dpf_adblue_off, description
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (solution_id) DO UPDATE SET
                    stage_1 = EXCLUDED.stage_1,
                    stage_2 = EXCLUDED.stage_2,
                    pop_and_bangs = EXCLUDED.pop_and_bangs,
                    vmax = EXCLUDED.vmax,
                    dtc_off = EXCLUDED.dtc_off,
                    full_decat = EXCLUDED.full_decat,
                    immo_off = EXCLUDED.immo_off,
                    evap_off = EXCLUDED.evap_off,
                    tva = EXCLUDED.tva,
                    egr_off = EXCLUDED.egr_off,
                    dpf_off = EXCLUDED.dpf_off,
                    egr_dpf_off = EXCLUDED.egr_dpf_off,
                    adblue_off = EXCLUDED.adblue_off,
                    egr_dpf_adblue_off = EXCLUDED.egr_dpf_adblue_off,
                    description = EXCLUDED.description
            ''', (
                solution_id,
                solution_types.get('stage_1', False),
                solution_types.get('stage_2', False),
                solution_types.get('pop_and_bangs', False),
                solution_types.get('vmax', False),
                solution_types.get('dtc_off', False),
                solution_types.get('full_decat', False),
                solution_types.get('immo_off', False),
                solution_types.get('evap_off', False),
                solution_types.get('tva', False),
                solution_types.get('egr_off', False),
                solution_types.get('dpf_off', False),
                solution_types.get('egr_dpf_off', False),
                solution_types.get('adblue_off', False),
                solution_types.get('egr_dpf_adblue_off', False),
                solution_types.get('description', '')
            ))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding solution types: {e}")
            self.conn.rollback()
            return False

    def get_solution_by_id(self, solution_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a solution by its ID.

        Args:
            solution_id: ID of solution to retrieve

        Returns:
            Dict containing solution data if found, None otherwise
        """
        if not self.conn or not self.cursor:
            logger.error("Cannot get solution: No active connection")
            return None

        try:
            self.cursor.execute("SELECT * FROM vehicle_info WHERE id = %s", (solution_id,))
            result = self.cursor.fetchone()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting solution by ID {solution_id}: {e}")
            return None

    def delete_solution(self, solution_id: int) -> bool:
        """
        Delete a solution from the database.

        Args:
            solution_id: ID of solution to delete

        Returns:
            bool: True if deletion successful, False otherwise
        """
        if not self.conn or not self.cursor:
            logger.error("Cannot delete solution: No active connection")
            return False

        try:
            self.cursor.execute("DELETE FROM vehicle_info WHERE id = %s", (solution_id,))
            self.conn.commit()
            logger.debug(f"Deleted solution with ID: {solution_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting solution: {e}")
            if self.conn:
                try:
                    self.conn.rollback()
                except:
                    pass
            return False
