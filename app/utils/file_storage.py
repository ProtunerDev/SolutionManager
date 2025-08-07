import json
import psycopg2
from flask import current_app
import logging
import uuid

logger = logging.getLogger(__name__)

class PostgreSQLFileStorage:
    def __init__(self):
        self.db_config = {
            'host': current_app.config['DB_HOST'],
            'database': current_app.config['DB_NAME'],
            'user': current_app.config['DB_USER'],
            'password': current_app.config['DB_PASSWORD'],
            'port': current_app.config['DB_PORT']
        }
    
    def get_connection(self):
        """Obtener conexión a PostgreSQL"""
        return psycopg2.connect(**self.db_config)
    
    def store_file(self, solution_id, file_type, file_name, file_data):
        """Método placeholder - ya no usado con S3"""
        logger.warning("PostgreSQL file storage is deprecated. Use S3 instead.")
        return False
    
    def get_file(self, solution_id, file_type):
        """Método placeholder - ya no usado con S3"""
        logger.warning("PostgreSQL file storage is deprecated. Use S3 instead.")
        return None, None