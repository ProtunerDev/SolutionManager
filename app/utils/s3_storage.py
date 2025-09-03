import boto3
import json
from flask import current_app
import logging
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime

logger = logging.getLogger(__name__)

class S3FileStorage:
    def __init__(self):
        self.bucket_name = current_app.config['AWS_S3_BUCKET']
        self.region = current_app.config['AWS_S3_REGION']
        
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
                aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY'],
                region_name=self.region
            )
            # Verificar conectividad al inicializar
            self._test_connection()
        except Exception as e:
            logger.error(f"Error initializing S3 client: {e}")
            raise
    
    def _test_connection(self):
        """Probar conectividad con S3"""
        try:
            # Verificar que el bucket existe y es accesible
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"✅ S3 connection successful - Bucket: {self.bucket_name}")
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.error(f"❌ S3 bucket '{self.bucket_name}' not found")
            elif error_code == '403':
                logger.error(f"❌ Access denied to S3 bucket '{self.bucket_name}'")
            else:
                logger.error(f"❌ S3 connection error: {e}")
            return False
        except NoCredentialsError:
            logger.error("❌ AWS credentials not found")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected S3 error: {e}")
            return False
    
    def _get_s3_key(self, solution_id, file_type, file_name):
        """Generar clave S3 para el archivo"""
        return f"solutions/{solution_id}/{file_type}/{file_name}"
    
    def store_file(self, solution_id, file_type, file_name, file_data):
        """Subir archivo a S3 y guardar metadatos en PostgreSQL"""
        try:
            # Convertir solution_id a entero si es posible, mantener como string si es temporal
            temp_solution_id = str(solution_id)
            is_permanent_solution = False
            
            # Verificar si es un ID de solución permanente (entero positivo)
            try:
                int_solution_id = int(solution_id)
                if int_solution_id > 0 and int_solution_id < 1000000000:  # ID razonable
                    is_permanent_solution = True
                    solution_id = int_solution_id
            except (ValueError, TypeError):
                # Es un ID temporal, mantener como string
                pass
            
            # Generar clave S3
            s3_key = self._get_s3_key(temp_solution_id, file_type, file_name)
            
            # Subir archivo a S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_data,
                ContentType='application/octet-stream',
                Metadata={
                    'solution_id': str(temp_solution_id),
                    'file_type': file_type,
                    'original_filename': file_name,
                    'file_size': str(len(file_data))
                }
            )
            
            # Solo guardar metadatos en PostgreSQL si es un ID entero válido de solución permanente
            if is_permanent_solution:
                self._save_file_metadata(solution_id, file_type, file_name, len(file_data), s3_key)
            
            logger.info(f"File {file_name} ({file_type}) uploaded to S3: {s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading to S3: {e}")
            return False
    
    def upload_temp_file(self, file_data, file_name, file_type, temp_solution_id):
        """Subir archivo temporal a S3 (alias de store_file para archivos temporales)"""
        try:
            s3_key = self.store_file(temp_solution_id, file_type, file_name, file_data)
            if s3_key:
                # Retornar la clave S3 para archivos temporales
                return self._get_s3_key(temp_solution_id, file_type, file_name)
            return None
        except Exception as e:
            logger.error(f"Error uploading temp file: {e}")
            return None
    
    def _save_file_metadata(self, solution_id, file_type, file_name, file_size, s3_key):
        """Guardar metadatos del archivo en PostgreSQL"""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=current_app.config['DB_HOST'],
                database=current_app.config['DB_NAME'],
                user=current_app.config['DB_USER'],
                password=current_app.config['DB_PASSWORD'],
                port=current_app.config['DB_PORT']
            )
            cur = conn.cursor()
            
            # Verificar si la solution existe
            cur.execute("SELECT id FROM solutions WHERE id = %s", (solution_id,))
            if not cur.fetchone():
                logger.warning(f"Solution {solution_id} not found, creating test solution")
                # Crear solution de prueba si no existe
                cur.execute("""
                    INSERT INTO solutions (id, vehicle_info_id, description, status) 
                    VALUES (%s, 1, 'Auto-created solution for file upload', 'active')
                    ON CONFLICT (id) DO NOTHING
                """, (solution_id,))
            
            # Eliminar metadatos anteriores del mismo tipo si existen
            cur.execute(
                "DELETE FROM file_metadata WHERE solution_id = %s AND file_type = %s",
                (solution_id, file_type)
            )
            
            # Insertar nuevos metadatos
            cur.execute("""
                INSERT INTO file_metadata (solution_id, file_type, file_name, file_size, s3_key)
                VALUES (%s, %s, %s, %s, %s)
            """, (solution_id, file_type, file_name, file_size, s3_key))
            
            conn.commit()
            cur.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving file metadata: {e}")
    
    def get_file(self, solution_id, file_type):
        """Obtener archivo desde S3"""
        try:
            # Manejar tanto IDs temporales como permanentes
            temp_solution_id = str(solution_id)
            
            # Para IDs temporales, construir directamente la clave S3
            s3_key = self._get_s3_key(temp_solution_id, file_type, None)
            
            # Intentar obtener archivo desde S3 (buscar por prefijo si no sabemos el nombre exacto)
            try:
                # Listar objetos con el prefijo para encontrar el archivo
                prefix = f"solutions/{temp_solution_id}/{file_type}/"
                response = self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=prefix
                )
                
                if 'Contents' not in response or not response['Contents']:
                    logger.error(f"No files found for {solution_id}/{file_type}")
                    return None, None
                
                # Usar el primer archivo encontrado
                s3_key = response['Contents'][0]['Key']
                file_name = s3_key.split('/')[-1]  # Extraer nombre del archivo
                
                # Descargar desde S3
                file_response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=s3_key
                )
                
                file_data = file_response['Body'].read()
                return file_name, file_data
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    logger.error(f"File not found in S3: {s3_key}")
                else:
                    logger.error(f"Error accessing S3: {e}")
                return None, None
            
        except Exception as e:
            logger.error(f"Error getting file from S3: {e}")
            return None, None
    
    def get_file_info(self, solution_id, file_type):
        """Obtener información del archivo desde PostgreSQL"""
        try:
            solution_id = int(solution_id)
            
            import psycopg2
            conn = psycopg2.connect(
                host=current_app.config['DB_HOST'],
                database=current_app.config['DB_NAME'],
                user=current_app.config['DB_USER'],
                password=current_app.config['DB_PASSWORD'],
                port=current_app.config['DB_PORT']
            )
            cur = conn.cursor()
            
            cur.execute("""
                SELECT file_name, file_size, uploaded_at FROM file_metadata 
                WHERE solution_id = %s AND file_type = %s
            """, (solution_id, file_type))
            
            result = cur.fetchone()
            cur.close()
            conn.close()
            
            if result:
                return {
                    'name': result[0],
                    'size': result[1],
                    'uploaded_at': result[2]
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return None
    
    def store_differences(self, solution_id, differences_list):
        """Guardar diferencias como JSON en S3 y metadatos en PostgreSQL"""
        try:
            solution_id = int(solution_id)
            
            s3_key = f"solutions/{solution_id}/differences/differences.json"
            logger.info(f"Storing {len(differences_list)} differences for solution {solution_id} to S3 key: {s3_key}")
            
            differences_data = {
                'solution_id': solution_id,
                'total_differences': len(differences_list),
                'differences': differences_list,
                'created_at': str(datetime.utcnow())
            }
            
            json_data = json.dumps(differences_data, indent=2)
            
            # Subir a S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json_data.encode('utf-8'),
                ContentType='application/json',
                Metadata={
                    'solution_id': str(solution_id),
                    'total_differences': str(len(differences_list))
                }
            )
            
            logger.info(f"Successfully stored differences in S3 for solution {solution_id}")
            
            # Guardar metadatos en PostgreSQL
            self._save_differences_metadata(solution_id, len(differences_list), s3_key)
            
            logger.info(f"Differences storage completed for solution {solution_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing differences: {e}")
            return False
            
            logger.info(f"Differences stored in S3: {s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing differences in S3: {e}")
            return False
    
    def _save_differences_metadata(self, solution_id, total_differences, s3_key):
        """Guardar metadatos de diferencias en PostgreSQL"""
        try:
            solution_id = int(solution_id)
            
            import psycopg2
            conn = psycopg2.connect(
                host=current_app.config['DB_HOST'],
                database=current_app.config['DB_NAME'],
                user=current_app.config['DB_USER'],
                password=current_app.config['DB_PASSWORD'],
                port=current_app.config['DB_PORT']
            )
            cur = conn.cursor()
            
            # Verificar si la solution existe
            cur.execute("SELECT id FROM solutions WHERE id = %s", (solution_id,))
            if not cur.fetchone():
                # Crear solution de prueba si no existe
                cur.execute("""
                    INSERT INTO solutions (id, vehicle_info_id, description, status) 
                    VALUES (%s, 1, 'Auto-created solution for differences', 'active')
                    ON CONFLICT (id) DO NOTHING
                """, (solution_id,))
            
            # Eliminar metadatos anteriores si existen
            cur.execute(
                "DELETE FROM differences_metadata WHERE solution_id = %s",
                (solution_id,)
            )
            
            # Insertar nuevos metadatos
            cur.execute("""
                INSERT INTO differences_metadata (solution_id, total_differences, s3_key)
                VALUES (%s, %s, %s)
            """, (solution_id, total_differences, s3_key))
            
            conn.commit()
            cur.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving differences metadata: {e}")
    
    def get_differences(self, solution_id):
        """Obtener diferencias desde S3"""
        try:
            solution_id = int(solution_id)
            
            s3_key = f"solutions/{solution_id}/differences/differences.json"
            logger.info(f"Attempting to get differences for solution {solution_id} from S3 key: {s3_key}")
            
            # Verificar si el objeto existe
            try:
                self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
                logger.info(f"Differences file found in S3 for solution {solution_id}")
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    logger.warning(f"Differences file not found in S3 for solution {solution_id}")
                    return None, 0
                else:
                    logger.error(f"Error checking differences file existence: {e}")
                    return None, 0
            
            # Descargar desde S3
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            json_data = response['Body'].read().decode('utf-8')
            differences_data = json.loads(json_data)
            
            logger.info(f"Successfully retrieved {differences_data['total_differences']} differences for solution {solution_id}")
            return differences_data['differences'], differences_data['total_differences']
            
        except Exception as e:
            logger.error(f"Error getting differences from S3: {e}")
            return None, 0
    
    def transfer_temp_files(self, temp_solution_id, real_solution_id):
        """Transferir ORI1 y MOD1 permanentemente para trazabilidad completa de la solución"""
        try:
            real_solution_id = int(real_solution_id)
            temp_solution_id = str(temp_solution_id)
            
            logger.info(f"Transferring ORI1 + MOD1 from temp {temp_solution_id} to solution {real_solution_id}")
            
            # Listar todos los archivos temporales
            temp_prefix = f"solutions/{temp_solution_id}/"
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=temp_prefix
            )
            
            if 'Contents' not in response:
                logger.warning(f"No temp files found for {temp_solution_id}")
                return False
            
            # Transferir AMBOS archivos (ORI1 + MOD1) permanentemente
            files_transferred = 0
            transferred_files = []
            
            for obj in response['Contents']:
                old_key = obj['Key']
                
                # Extraer file_type y filename del path
                # Format: solutions/{temp_id}/{file_type}/{filename}
                path_parts = old_key.split('/')
                if len(path_parts) >= 4:
                    file_type = path_parts[2]
                    filename = path_parts[3]
                    
                    # Transferir TANTO ORI1 como MOD1 permanentemente
                    if file_type in ['ori1', 'mod1']:
                        # Nueva clave para la solución real
                        new_key = f"solutions/{real_solution_id}/{file_type}/{filename}"
                        
                        # Copiar archivo permanentemente
                        copy_source = {'Bucket': self.bucket_name, 'Key': old_key}
                        self.s3_client.copy_object(
                            CopySource=copy_source,
                            Bucket=self.bucket_name,
                            Key=new_key,
                            MetadataDirective='REPLACE',
                            Metadata={
                                'solution_id': str(real_solution_id),
                                'file_type': file_type,
                                'original_filename': filename
                            }
                        )
                        
                        # Obtener tamaño del archivo
                        file_size = obj['Size']
                        
                        # Guardar metadatos en PostgreSQL para ambos archivos
                        self._save_file_metadata(real_solution_id, file_type, filename, file_size, new_key)
                        
                        transferred_files.append({
                            'file_type': file_type,
                            'filename': filename,
                            'old_key': old_key,
                            'new_key': new_key,
                            'size': file_size
                        })
                        
                        logger.info(f"✅ {file_type.upper()} transferred permanently: {old_key} -> {new_key}")
                        files_transferred += 1
                    
                    else:
                        logger.info(f"ℹ️ Other file type found: {file_type} - {old_key}")
            
            # Eliminar archivos temporales después de transferir
            self.delete_temp_files(temp_solution_id)
            
            if files_transferred > 0:
                logger.info(f"✅ Successfully transferred {files_transferred} files from {temp_solution_id} to {real_solution_id}")
                for file_info in transferred_files:
                    logger.info(f"   � {file_info['file_type'].upper()}: {file_info['filename']} ({file_info['size']:,} bytes)")
                logger.info(f"🗑️ Temporary files deleted from {temp_solution_id}")
                logger.info(f"🎯 RESULTADO: ORI1 + MOD1 guardados permanentemente para trazabilidad completa")
                return True
            else:
                logger.warning(f"⚠️ No ORI1/MOD1 files found to transfer from {temp_solution_id}")
                return False
            
        except Exception as e:
            logger.error(f"Error transferring temp files: {e}")
            return False
    
    def delete_temp_files(self, temp_solution_id):
        """Eliminar archivos temporales"""
        try:
            temp_solution_id = str(temp_solution_id)
            
            # Listar todos los objetos temporales
            prefix = f"solutions/{temp_solution_id}/"
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            # Eliminar objetos de S3
            if 'Contents' in response:
                objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
                
                self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': objects_to_delete}
                )
                
                logger.info(f"Deleted {len(objects_to_delete)} temp files for {temp_solution_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting temp files: {e}")
            return False

    def delete_solution_files(self, solution_id):
        """Eliminar todos los archivos de una solution"""
        try:
            solution_id = int(solution_id)
            
            # Listar todos los objetos de la solution
            prefix = f"solutions/{solution_id}/"
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            # Eliminar objetos de S3
            if 'Contents' in response:
                objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
                
                self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': objects_to_delete}
                )
            
            # Eliminar metadatos de PostgreSQL
            import psycopg2
            conn = psycopg2.connect(
                host=current_app.config['DB_HOST'],
                database=current_app.config['DB_NAME'],
                user=current_app.config['DB_USER'],
                password=current_app.config['DB_PASSWORD'],
                port=current_app.config['DB_PORT']
            )
            cur = conn.cursor()
            
            cur.execute("DELETE FROM file_metadata WHERE solution_id = %s", (solution_id,))
            cur.execute("DELETE FROM differences_metadata WHERE solution_id = %s", (solution_id,))
            
            conn.commit()
            cur.close()
            conn.close()
            
            logger.info(f"Solution {solution_id} files deleted")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting solution files: {e}")
            return False