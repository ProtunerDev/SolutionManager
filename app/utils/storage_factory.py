from app.utils.s3_storage import S3FileStorage
from app.utils.file_storage import PostgreSQLFileStorage
from flask import current_app

def get_file_storage():
    """Factory para obtener el storage configurado"""
    storage_type = current_app.config.get('STORAGE_TYPE', 's3')
    
    if storage_type == 's3':
        return S3FileStorage()
    else:
        return PostgreSQLFileStorage()