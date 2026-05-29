import json
import os
import shutil
from flask import current_app
import logging
from datetime import datetime
from app.database.db_pool import pooled_connection

logger = logging.getLogger(__name__)

class PostgreSQLFileStorage:
    def __init__(self):
        self.upload_folder = current_app.config['UPLOAD_FOLDER']

    def _get_file_path(self, solution_id, file_type, file_name):
        return os.path.join(self.upload_folder, 'solutions', str(solution_id), file_type, file_name)

    def _get_file_key(self, solution_id, file_type, file_name):
        return f"solutions/{solution_id}/{file_type}/{file_name}"

    def store_file(self, solution_id, file_type, file_name, file_data):
        try:
            temp_solution_id = str(solution_id)
            is_permanent_solution = False

            try:
                int_solution_id = int(solution_id)
                if 0 < int_solution_id < 1000000000:
                    is_permanent_solution = True
                    solution_id = int_solution_id
            except (ValueError, TypeError):
                pass

            file_path = self._get_file_path(temp_solution_id, file_type, file_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'wb') as f:
                f.write(file_data)

            file_key = self._get_file_key(temp_solution_id, file_type, file_name)

            if is_permanent_solution:
                self._save_file_metadata(solution_id, file_type, file_name, len(file_data), file_key)

            logger.info(f"File {file_name} ({file_type}) stored locally: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error storing file locally: {e}")
            return False

    def upload_temp_file(self, file_data, file_name, file_type, temp_solution_id):
        try:
            success = self.store_file(temp_solution_id, file_type, file_name, file_data)
            if success:
                return self._get_file_key(temp_solution_id, file_type, file_name)
            return None
        except Exception as e:
            logger.error(f"Error uploading temp file: {e}")
            return None

    def _save_file_metadata(self, solution_id, file_type, file_name, file_size, file_key):
        try:
            with pooled_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT id FROM solutions WHERE id = %s", (solution_id,))
                if not cur.fetchone():
                    logger.error(f"Solution {solution_id} not found — file metadata not saved")
                    cur.close()
                    return
                cur.execute(
                    "DELETE FROM file_metadata WHERE solution_id = %s AND file_type = %s",
                    (solution_id, file_type)
                )
                cur.execute("""
                    INSERT INTO file_metadata (solution_id, file_type, file_name, file_size, s3_key)
                    VALUES (%s, %s, %s, %s, %s)
                """, (solution_id, file_type, file_name, file_size, file_key))
                cur.close()
        except Exception as e:
            logger.error(f"Error saving file metadata: {e}")

    def get_file(self, solution_id, file_type):
        try:
            prefix_path = os.path.join(self.upload_folder, 'solutions', str(solution_id), file_type)

            if not os.path.exists(prefix_path):
                logger.error(f"No directory found for {solution_id}/{file_type}")
                return None, None

            files = os.listdir(prefix_path)
            if not files:
                logger.error(f"No files found for {solution_id}/{file_type}")
                return None, None

            file_name = files[0]
            with open(os.path.join(prefix_path, file_name), 'rb') as f:
                file_data = f.read()

            return file_name, file_data
        except Exception as e:
            logger.error(f"Error getting file locally: {e}")
            return None, None

    def get_file_info(self, solution_id, file_type):
        try:
            solution_id = int(solution_id)
            with pooled_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT file_name, file_size, uploaded_at FROM file_metadata
                    WHERE solution_id = %s AND file_type = %s
                """, (solution_id, file_type))
                result = cur.fetchone()
                cur.close()
            if result:
                return {'name': result[0], 'size': result[1], 'uploaded_at': result[2]}
            return None
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return None

    def store_differences(self, solution_id, differences_list):
        try:
            solution_id = int(solution_id)

            file_key = f"solutions/{solution_id}/differences/differences.json"
            file_path = os.path.join(self.upload_folder, file_key)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            differences_data = {
                'solution_id': solution_id,
                'total_differences': len(differences_list),
                'differences': differences_list,
                'created_at': str(datetime.utcnow())
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(differences_data, f, indent=2)

            self._save_differences_metadata(solution_id, len(differences_list), file_key)

            logger.info(f"Differences stored locally for solution {solution_id}")
            return True
        except Exception as e:
            logger.error(f"Error storing differences: {e}")
            return False

    def _save_differences_metadata(self, solution_id, total_differences, file_key):
        try:
            solution_id = int(solution_id)
            with pooled_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT id FROM solutions WHERE id = %s", (solution_id,))
                if not cur.fetchone():
                    logger.error(f"Solution {solution_id} not found — differences metadata not saved")
                    cur.close()
                    return
                cur.execute("DELETE FROM differences_metadata WHERE solution_id = %s", (solution_id,))
                cur.execute("""
                    INSERT INTO differences_metadata (solution_id, total_differences, s3_key)
                    VALUES (%s, %s, %s)
                """, (solution_id, total_differences, file_key))
                cur.close()
        except Exception as e:
            logger.error(f"Error saving differences metadata: {e}")

    def get_differences(self, solution_id):
        try:
            solution_id = int(solution_id)

            file_path = os.path.join(
                self.upload_folder, 'solutions', str(solution_id), 'differences', 'differences.json'
            )

            if not os.path.exists(file_path):
                logger.warning(f"Differences file not found for solution {solution_id}")
                return None, 0

            with open(file_path, 'r', encoding='utf-8') as f:
                differences_data = json.load(f)

            return differences_data['differences'], differences_data['total_differences']
        except Exception as e:
            logger.error(f"Error getting differences: {e}")
            return None, 0

    def transfer_temp_files(self, temp_solution_id, real_solution_id):
        try:
            real_solution_id = int(real_solution_id)
            temp_solution_id = str(temp_solution_id)

            temp_prefix = os.path.join(self.upload_folder, 'solutions', temp_solution_id)

            if not os.path.exists(temp_prefix):
                logger.warning(f"No temp files found for {temp_solution_id}")
                return False

            files_transferred = 0

            for file_type in ['ori1', 'mod1']:
                src_dir = os.path.join(temp_prefix, file_type)
                if not os.path.exists(src_dir):
                    continue

                for file_name in os.listdir(src_dir):
                    src_path = os.path.join(src_dir, file_name)
                    dst_path = self._get_file_path(real_solution_id, file_type, file_name)
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    shutil.copy2(src_path, dst_path)

                    file_key = self._get_file_key(real_solution_id, file_type, file_name)
                    self._save_file_metadata(
                        real_solution_id, file_type, file_name, os.path.getsize(dst_path), file_key
                    )
                    files_transferred += 1
                    logger.info(f"Transferred {file_type}: {src_path} -> {dst_path}")

            self.delete_temp_files(temp_solution_id)

            if files_transferred > 0:
                logger.info(f"Transferred {files_transferred} files from {temp_solution_id} to {real_solution_id}")
                return True

            logger.warning(f"No ORI1/MOD1 files found for {temp_solution_id}")
            return False
        except Exception as e:
            logger.error(f"Error transferring temp files: {e}")
            return False

    def delete_temp_files(self, temp_solution_id):
        try:
            temp_path = os.path.join(self.upload_folder, 'solutions', str(temp_solution_id))
            if os.path.exists(temp_path):
                shutil.rmtree(temp_path)
                logger.info(f"Deleted temp files for {temp_solution_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting temp files: {e}")
            return False

    def delete_solution_files(self, solution_id):
        try:
            solution_id = int(solution_id)

            solution_path = os.path.join(self.upload_folder, 'solutions', str(solution_id))
            if os.path.exists(solution_path):
                shutil.rmtree(solution_path)

            with pooled_connection() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM file_metadata WHERE solution_id = %s", (solution_id,))
                cur.execute("DELETE FROM differences_metadata WHERE solution_id = %s", (solution_id,))
                cur.close()

            logger.info(f"Solution {solution_id} files deleted")
            return True
        except Exception as e:
            logger.error(f"Error deleting solution files: {e}")
            return False
