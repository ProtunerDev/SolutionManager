"""
Main Routes Module

This module provides the main application routes including:
- Home page
- File upload
- Binary comparison
- Solution management
"""

import os
import json
import tempfile
from flask import render_template, url_for, flash, redirect, request, session, current_app, send_from_directory, make_response, jsonify
from flask_login import login_required, current_user, logout_user
from werkzeug.utils import secure_filename
from app.main import bp
from app.database.db_manager import DatabaseManager
from app.utils.binary_handler import BinaryHandler
from app.utils.storage_factory import get_file_storage
import uuid
import json
from flask import send_file
import io

import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'bin', 'ori', 'mod', 'dtf'}

def allowed_file(filename):
    """Check if file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/')
@bp.route('/index')
def index():
    """Home page route - redirects to login page if not authenticated, home if logged in."""
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    return redirect(url_for('auth.login'))

@bp.route('/home')
@login_required
def home():
    """Home dashboard with recent solutions."""
    search_query = request.args.get('search', '').strip()
    limit = int(request.args.get('limit', 20))
    recent_solutions = []
    
    try:
        with DatabaseManager() as db:
            # Query para obtener las últimas soluciones con información extendida
            base_query = '''
                SELECT s.id, s.created_at, s.updated_at, s.description as solution_description,
                       v.vehicle_type, v.make, v.model, v.engine, v.year,
                       v.hardware_number, v.software_number, v.ecu_type,
                       st.stage_1, st.stage_2, st.pop_and_bangs, st.vmax,
                       st.dtc_off, st.full_decat, st.immo_off, st.evap_off, st.tva,
                       st.egr_off, st.dpf_off, st.egr_dpf_off, st.adblue_off,
                       st.egr_dpf_adblue_off, st.description as type_description
                FROM solutions s
                JOIN vehicle_info v ON s.vehicle_info_id = v.id
                LEFT JOIN solution_types st ON s.id = st.solution_id
            '''
            
            params = []
            if search_query:
                base_query += '''
                    WHERE (
                        v.vehicle_type ILIKE %s OR
                        v.make ILIKE %s OR
                        v.model ILIKE %s OR
                        v.engine ILIKE %s OR
                        v.hardware_number ILIKE %s OR
                        v.software_number ILIKE %s OR
                        s.description ILIKE %s OR
                        st.description ILIKE %s
                    )
                '''
                search_pattern = f'%{search_query}%'
                params = [search_pattern] * 8
                
            base_query += ' ORDER BY s.updated_at DESC, s.created_at DESC LIMIT %s'
            params.append(limit)
            
            db.cursor.execute(base_query, params)
            columns = [desc[0] for desc in db.cursor.description]
            recent_solutions = [dict(zip(columns, row)) for row in db.cursor.fetchall()]
            
            # Agregar información de tipos de solución activos
            for solution in recent_solutions:
                solution['active_types'] = []
                for type_name in ['stage_1', 'stage_2', 'pop_and_bangs', 'vmax',
                                'dtc_off', 'full_decat', 'immo_off', 'evap_off', 'tva',
                                'egr_off', 'dpf_off', 'egr_dpf_off', 'adblue_off',
                                'egr_dpf_adblue_off']:
                    if solution.get(type_name):
                        solution['active_types'].append(type_name.replace('_', ' ').title())
                        
    except Exception as e:
        logger.error(f"Error fetching recent solutions: {e}")
        flash('Error loading recent solutions. Please try again.', 'danger')
    
    return render_template(
        'main/home.html',
        title='Home',
        recent_solutions=recent_solutions,
        search_query=search_query,
        total_shown=len(recent_solutions),
        limit=limit
    )

@bp.route('/upload_file', methods=['POST'])
@login_required
def upload_file():
    """File upload route - ahora usa S3"""
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('main.add_solution'))
    
    file = request.files['file']
    file_type = request.form.get('file_type')
    
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('main.add_solution'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_data = file.read()
        
        logger.info(f"Uploading file: {filename} (type: {file_type}, size: {len(file_data)} bytes)")
        
        # Usar storage configurado (S3 según .env)
        storage = get_file_storage()
        
        # Obtener o crear solution_id temporal como entero
        solution_id = session.get('temp_solution_id')
        if not solution_id:
            # Generar un ID temporal único basado en timestamp
            import time
            solution_id = int(time.time() * 1000000) % 999999999  # Usar timestamp en microsegundos como ID temporal
            session['temp_solution_id'] = solution_id
        
        logger.info(f"Using solution_id: {solution_id}")
        
        # Guardar archivo en S3
        try:
            if storage.store_file(solution_id, file_type, filename, file_data):
                # Actualizar session para tracking
                if 'files' not in session:
                    session['files'] = {}
                session['files'][file_type] = {'solution_id': solution_id, 'filename': filename}
                
                # Store original filename for MOD2
                if file_type == 'ori2':
                    session['ori2_base_name'] = os.path.splitext(filename)[0]
                
                session.modified = True
                
                # Build search params for redirect
                search_params = {}
                for field in [
                    'vehicle_type', 'make', 'model', 'engine', 'ecu_type',
                    'hardware_number', 'software_number', 'software_update_number',
                    'year', 'transmission_type'
                ]:
                    value = request.form.get(field)
                    if value:
                        search_params[field] = value
                
                if file_type == 'ori2':
                    flash('ORI2 file uploaded successfully', 'success')
                    return redirect(url_for('main.modify_file', **search_params))
                else:
                    flash(f'{file_type.upper()} file uploaded successfully', 'success')
                    return redirect(url_for('main.add_solution'))
            else:
                flash('Error uploading file to storage', 'danger')
        except Exception as e:
            logger.error(f"Error during file upload: {e}")
            flash(f'Error uploading file: {str(e)}', 'danger')
    else:
        flash(f'Invalid file type. Allowed types: .ori, .mod, .bin, .dtf, .DTF (got: {file.filename})', 'danger')
    
    return redirect(url_for('main.add_solution'))

@bp.route('/compare_files', methods=['POST'])
@login_required
def compare_files():
    """
    Binary comparison route for add_solution page.
    
    POST: Process comparison request and redirect back to add_solution
    """
    if 'files' not in session or 'ori1' not in session['files'] or 'mod1' not in session['files']:
        flash('Please upload ORI1 and MOD1 files first', 'warning')
        return redirect(url_for('main.add_solution'))
        
    bit_size = int(request.form.get('bit_size', 8))
    
    try:
        binary_handler = BinaryHandler()
        binary_handler.set_read_size(bit_size)
        
        # Obtener archivos desde S3 storage
        storage = get_file_storage()
        ori1_info = session['files']['ori1']
        mod1_info = session['files']['mod1']
        
        # Descargar archivos temporalmente para comparación
        ori1_filename, ori1_data = storage.get_file(ori1_info['solution_id'], 'ori1')
        mod1_filename, mod1_data = storage.get_file(mod1_info['solution_id'], 'mod1')
        
        if not ori1_data or not mod1_data:
            flash('Error retrieving files from storage', 'danger')
            return redirect(url_for('main.add_solution'))
        
        # Crear archivos temporales para la comparación
        import tempfile
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.ori', delete=False) as ori1_temp:
            ori1_temp.write(ori1_data)
            ori1_temp_path = ori1_temp.name
            
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.mod', delete=False) as mod1_temp:
            mod1_temp.write(mod1_data)
            mod1_temp_path = mod1_temp.name
        
        try:
            # Comparar archivos
            differences = binary_handler.compare_files(ori1_temp_path, mod1_temp_path)
            
            session['bit_size'] = bit_size

            # --- NEW: Save differences to a file instead of session ---
            # Usar timestamp para filename único
            import time
            filename = f"differences_{int(time.time() * 1000000)}.json"
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            with open(filepath, 'w') as f:
                json.dump([
                    (diff[0], diff[1], diff[2]) for diff in differences
                ], f)
            session['differences_file'] = filename
            session.modified = True
            # ---------------------------------------------------------

            flash(f'Files compared successfully. {len(differences)} differences found.', 'success')
            
        finally:
            # Limpiar archivos temporales
            try:
                os.unlink(ori1_temp_path)
                os.unlink(mod1_temp_path)
            except Exception as e:
                logger.warning(f"Error cleaning up temp files: {e}")
                
        return redirect(url_for('main.add_solution'))
    except Exception as e:
        logger.error(f"Error comparing files: {e}")
        flash(f'Error comparing files: {str(e)}', 'danger')
        return redirect(url_for('main.add_solution'))

@bp.route('/modify_file', methods=['GET', 'POST'])
@login_required
def modify_file():
    """
    Modify file route (formerly compare).
    
    GET: Display modify file form with solution search
    POST: Process modification request
    """
    solutions = []
    search_performed = False
    
    if request.method == 'GET' and any(request.args.values()):
        search_performed = True
        filters = {}
        
        for key, value in request.args.items():
            # Do not require ecu_type or software_update_number
            if value:
                filters[key] = value
        
        with DatabaseManager() as db:
            solutions = db.search_solutions(filters)
    
    with DatabaseManager() as db:
        vehicle_types = db.get_field_values('vehicle_type')
    
    return render_template(
        'main/modify_file.html',
        title='Modify File',
        solutions=solutions,
        search_performed=search_performed,
        vehicle_types=vehicle_types
    )

@bp.route('/compare/results')
@login_required
def compare_results():
    if 'differences_file' not in session:
        flash('No comparison results available', 'warning')
        return redirect(url_for('main.compare'))

    filename = session['differences_file']
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    try:
        with open(filepath, 'r') as f:
            differences = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        flash('Comparison data is missing or corrupted. Please re-compare files.', 'danger')
        session.pop('differences_file', None)
        return redirect(url_for('main.compare'))

    return render_template(
        'main/compare_results.html',
        title='Comparison Results',
        differences=differences
    )

@bp.route('/solutions')
@login_required
def solutions():
    """Display solutions based on search criteria."""
    solutions_data = []
    search_performed = False
    
    if request.args and any(request.args.values()):
        search_performed = True
        filters = {}
        for key, value in request.args.items():
            # Do not require ecu_type or software_update_number
            if value:
                filters[key] = value
        
        with DatabaseManager() as db:
            solutions_data = db.search_solutions(filters)
    
    if session.pop('mod2_downloaded', None):
        flash('Modification was successfully applied and downloaded', 'success')
    
    return render_template(
        'main/solutions.html',
        title='Solutions',
        solutions=solutions_data,
        search_performed=search_performed
    )

@bp.route('/solutions/<int:solution_id>')
@login_required
def solution_detail(solution_id):
    """Display solution details."""
    with DatabaseManager() as db:
        solution = db.search_solutions({'id': solution_id})
        if not solution:
            flash('Solution not found', 'danger')
            return redirect(url_for('main.solutions'))
            
        solution = solution[0]
        
        # Obtener diferencias desde S3
        storage = get_file_storage()
        differences_data, total_differences = storage.get_differences(solution_id)
        
        differences = []
        has_differences = False
        if differences_data:
            has_differences = True
            for diff in differences_data:
                address = diff['memory_address']
                ori1_value = diff['ori1_value']
                mod1_value = diff['mod1_value']
                bit_size = diff['bit_size']
                differences.append((address, ori1_value, mod1_value, bit_size))
        else:
            logger.warning(f"No differences found for solution {solution_id}")
    
    return render_template(
        'main/solution_detail.html',
        title=f'Solution {solution_id}',
        solution=solution,
        differences=differences,
        has_differences=has_differences,
        total_differences=total_differences
    )

@bp.route('/add_solution', methods=['GET', 'POST'])
@login_required
def add_solution():
    """
    Add solution route.
    
    GET: Display add solution form with file upload functionality
    POST: Process add solution request
    """
    logger.info("=== ADD_SOLUTION ROUTE CALLED ===")
    try:
        if request.method == 'POST':
            logger.info("Processing POST request for add_solution")
            if 'differences_file' not in session:
                flash('Please upload and compare ORI1 and MOD1 files first', 'warning')
                return redirect(url_for('main.add_solution'))

            filename = session['differences_file']
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            try:
                with open(filepath, 'r') as f:
                    differences = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                flash('Comparison data is missing or corrupted. Please re-compare files.', 'danger')
                session.pop('differences_file', None)
                return redirect(url_for('main.add_solution'))

            vehicle_info = {
                'vehicle_type': request.form.get('vehicle_type'),
                'make': request.form.get('make'),
                'model': request.form.get('model'),
                'engine': request.form.get('engine'),
                'year': request.form.get('year'),
                'ecu_type': request.form.get('ecu_type', ''),  # Optional
                'hardware_number': request.form.get('hardware_number'),
                'software_number': request.form.get('software_number'),
                'software_update_number': request.form.get('software_update_number', ''),  # Optional
                'transmission_type': request.form.get('transmission_type')
            }
            
            solution_types = {
                'stage_1': 'stage_1' in request.form,
                'stage_2': 'stage_2' in request.form,
                'pop_and_bangs': 'pop_and_bangs' in request.form,
                'vmax': 'vmax' in request.form,
                'dtc_off': 'dtc_off' in request.form,
                'full_decat': 'full_decat' in request.form,
                'immo_off': 'immo_off' in request.form,
                'evap_off': 'evap_off' in request.form,
                'tva': 'tva' in request.form,
                'egr_off': 'egr_off' in request.form,
                'dpf_off': 'dpf_off' in request.form,
                'egr_dpf_off': 'egr_dpf_off' in request.form,
                'adblue_off': 'adblue_off' in request.form,
                'egr_dpf_adblue_off': 'egr_dpf_adblue_off' in request.form,
                'description': request.form.get('description', '')
            }
            
            with DatabaseManager() as db:
                solution_id = db.add_solution(vehicle_info, solution_types)
                
                if solution_id:
                    bit_size = session.get('bit_size', 8)
                    
                    # Preparar diferencias para S3 storage
                    differences_for_storage = []
                    for address, ori1_value, mod1_value in differences:
                        differences_for_storage.append({
                            'memory_address': address,
                            'ori1_value': ori1_value,
                            'mod1_value': mod1_value,
                            'bit_size': bit_size
                        })
                    
                    # Guardar diferencias en S3
                    storage = get_file_storage()
                    if storage.store_differences(solution_id, differences_for_storage):
                        logger.info(f"Differences stored in S3 for solution {solution_id}")
                    else:
                        logger.error(f"Failed to store differences in S3 for solution {solution_id}")

                    flash('Solution added successfully', 'success')
                    # Clean up uploaded files and related session data
                    session.pop('files', None)
                    session.pop('ori2_base_name', None)
                    session.pop('differences_file', None)  # Limpiar archivo temporal
                    session.modified = True
                    return redirect(url_for('main.solution_detail', solution_id=solution_id))
                else:
                    flash('Error adding solution', 'danger')
        
        logger.info("Getting vehicle types from database")
        with DatabaseManager() as db:
            vehicle_types = db.get_field_values('vehicle_type')
            logger.info(f"Found {len(vehicle_types)} vehicle types")
        
        logger.info("Rendering add_solution.html template")
        return render_template(
            'main/add_solution.html',
            title='Add Solution',
            vehicle_types=vehicle_types,
            search_performed=False
        )
    except Exception as e:
        logger.error(f"Error in add_solution route: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        flash(f'An error occurred: {str(e)}', 'danger')
        return redirect(url_for('main.home'))

@bp.route('/solutions/edit/<int:solution_id>', methods=['GET', 'POST'])
@login_required
def edit_solution(solution_id):
    """
    Edit solution route.
    
    GET: Display edit solution form
    POST: Process edit solution request
    """
    with DatabaseManager() as db:
        solution = db.search_solutions({'id': solution_id})
        if not solution:
            flash('Solution not found', 'danger')
            return redirect(url_for('main.solutions'))
            
        solution = solution[0]
        
        if request.method == 'POST':
            vehicle_info = {
                'vehicle_type': request.form.get('vehicle_type'),
                'make': request.form.get('make'),
                'model': request.form.get('model'),
                'engine': request.form.get('engine'),
                'year': request.form.get('year'),
                'ecu_type': request.form.get('ecu_type', ''),  # Optional
                'hardware_number': request.form.get('hardware_number'),
                'software_number': request.form.get('software_number'),
                'software_update_number': request.form.get('software_update_number', ''),  # Optional
                'transmission_type': request.form.get('transmission_type')
            }
            
            solution_types = {
                'stage_1': 'stage_1' in request.form,
                'stage_2': 'stage_2' in request.form,
                'pop_and_bangs': 'pop_and_bangs' in request.form,
                'vmax': 'vmax' in request.form,
                'dtc_off': 'dtc_off' in request.form,
                'full_decat': 'full_decat' in request.form,
                'immo_off': 'immo_off' in request.form,
                'evap_off': 'evap_off' in request.form,
                'tva': 'tva' in request.form,
                'egr_off': 'egr_off' in request.form,
                'dpf_off': 'dpf_off' in request.form,
                'egr_dpf_off': 'egr_dpf_off' in request.form,
                'adblue_off': 'adblue_off' in request.form,
                'egr_dpf_adblue_off': 'egr_dpf_adblue_off' in request.form,
                'description': request.form.get('description', '')
            }
            
            db.update_solution(solution_id, vehicle_info)
            db.add_solution_types(solution_id, solution_types)
            
            flash('Solution updated successfully', 'success')
            return redirect(url_for('main.solution_detail', solution_id=solution_id))
    
    with DatabaseManager() as db:
        vehicle_types = db.get_field_values('vehicle_type')
    
    return render_template(
        'main/edit_solution.html',
        title='Edit Solution',
        solution=solution,
        vehicle_types=vehicle_types
    )

@bp.route('/solutions/delete/<int:solution_id>', methods=['POST'])
@login_required
def delete_solution(solution_id):
    """Delete solution route."""
    try:
        # Eliminar archivos de S3
        storage = get_file_storage()
        storage.delete_solution_files(solution_id)
        
        # Eliminar de la base de datos
        with DatabaseManager() as db:
            if db.delete_solution(solution_id):
                flash('Solution deleted successfully', 'success')
            else:
                flash('Error deleting solution from database', 'danger')
    except Exception as e:
        logger.error(f"Error deleting solution {solution_id}: {e}")
        flash('Error deleting solution', 'danger')
    
    return redirect(url_for('main.solutions'))

@bp.route('/solutions/delete_from_home/<int:solution_id>', methods=['POST'])
@login_required
def delete_solution_from_home(solution_id):
    """Delete solution from home/recent solutions."""
    try:
        # Eliminar archivos de S3
        storage = get_file_storage()
        storage.delete_solution_files(solution_id)
        
        # Eliminar de la base de datos
        with DatabaseManager() as db:
            if db.delete_solution(solution_id):
                flash('Solution deleted successfully', 'success')
            else:
                flash('Error deleting solution from database', 'danger')
    except Exception as e:
        logger.error(f"Error deleting solution {solution_id}: {e}")
        flash('Error deleting solution', 'danger')
    
    return redirect(url_for('main.home'))

@bp.route('/delete_solution_from_home', methods=['POST'])
@login_required
def delete_solution_from_home_ajax():
    """Delete solution from home/recent solutions via AJAX."""
    logger.info(f"Delete solution request from user: {current_user.email}")
    
    try:
        data = request.get_json()
        solution_id = data.get('solution_id')
        
        logger.info(f"Attempting to delete solution ID: {solution_id}")
        
        if not solution_id:
            return jsonify({'success': False, 'message': 'Solution ID is required'})
        
        # Verificar que la solución existe antes de intentar eliminarla
        with DatabaseManager() as db:
            if not db.get_solution_by_id(solution_id):
                logger.warning(f"Solution {solution_id} not found in database")
                return jsonify({'success': False, 'message': 'Solution not found'})
        
        # Eliminar archivos de S3
        storage = get_file_storage()
        logger.info(f"Deleting S3 files for solution {solution_id}")
        try:
            storage.delete_solution_files(solution_id)
            logger.info(f"Successfully deleted S3 files for solution {solution_id}")
        except Exception as e:
            logger.warning(f"Failed to delete S3 files for solution {solution_id}: {e}")
            # Continue with database deletion even if S3 deletion fails
        
        # Eliminar de la base de datos
        with DatabaseManager() as db:
            logger.info(f"Deleting solution {solution_id} from database")
            if db.delete_solution(solution_id):
                logger.info(f"Successfully deleted solution {solution_id}")
                return jsonify({
                    'success': True, 
                    'message': 'Solution deleted successfully',
                    'solution_id': solution_id
                })
            else:
                logger.error(f"Failed to delete solution {solution_id} from database")
                return jsonify({'success': False, 'message': 'Error deleting solution from database'})
    except Exception as e:
        logger.error(f"Error deleting solution via AJAX: {e}")
        return jsonify({'success': False, 'message': f'Error deleting solution: {str(e)}'})

@bp.route('/solutions/apply/<int:solution_id>', methods=['POST'])
@login_required
def apply_solution(solution_id):
    """Check compatibility using differences data and show confirmation before applying solution to ORI2 file."""
    if 'files' not in session or 'ori2' not in session['files']:
        flash('Please upload ORI2 file first', 'warning')
        return redirect(url_for('main.modify_file'))
    
    try:
        # Obtener diferencias desde S3
        storage = get_file_storage()
        differences_data, total_differences = storage.get_differences(solution_id)
        
        if not differences_data:
            flash(f'No differences found for solution {solution_id}. This solution may not have been created through the complete comparison process. Please contact the administrator to regenerate the differences for this solution.', 'warning')
            logger.warning(f"No differences found for solution {solution_id}")
            return redirect(url_for('main.modify_file'))
        
        # Obtener archivo ORI2 desde S3
        ori2_info = session['files']['ori2']
        ori2_filename, ori2_file_data = storage.get_file(ori2_info['solution_id'], 'ori2')
        
        if not ori2_file_data:
            flash('Error retrieving ORI2 file from storage', 'danger')
            return redirect(url_for('main.modify_file'))
        
        # Crear archivo temporal ORI2 para procesar
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.ori', delete=False) as ori2_temp:
            ori2_temp.write(ori2_file_data)
            ori2_temp_path = ori2_temp.name
        
        try:
            # Obtener archivo ORI1 de la solución desde S3
            ori1_filename, ori1_file_data = storage.get_file(solution_id, 'ori1')
            
            if not ori1_file_data:
                logger.error(f"ORI1 file not found for solution {solution_id}")
                flash(f'Esta solución (ID: {solution_id}) no tiene archivo ORI1 disponible. Por favor, selecciona una solución diferente o contacta al administrador para que complete esta solución.', 'warning')
                return redirect(url_for('main.modify_file'))
            
            # Crear archivo temporal ORI1 para procesar
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.ori', delete=False) as ori1_temp:
                ori1_temp.write(ori1_file_data)
                ori1_temp_path = ori1_temp.name
            
            # Calcular compatibilidad comparando ORI2 vs ORI1 directamente
            binary_handler = BinaryHandler()
            bit_size = differences_data[0]['bit_size'] if differences_data else 8
            binary_handler.set_read_size(bit_size)

            # Leer datos de ambos archivos
            ori2_data = binary_handler.read_file(ori2_temp_path)
            ori1_data = binary_handler.read_file(ori1_temp_path)

            # ESTRATEGIA CORREGIDA: Comparar ORI2 del usuario vs ORI1 de la solución
            compatibility_result = binary_handler.calculate_similarity(ori2_data, ori1_data)
            
            # Convertir resultado de similitud a formato compatible con template
            # Mapear campos de similarity a formato de compatibility esperado por el template
            compatibility_result['compatibility_percentage'] = compatibility_result['similarity_percentage']
            compatibility_result['matching_points'] = compatibility_result['identical_bytes']
            compatibility_result['total_points'] = compatibility_result['total_bytes']
            compatibility_result['incompatible_points'] = []  # No hay detalles específicos de puntos incompatibles con similitud
            compatibility_result['analysis_type'] = 'similarity_based'            # Obtener información de la solución para mostrar en el modal
            from app.database.db_manager import DatabaseManager
            db = DatabaseManager()
            solution = db.get_solution_by_id(solution_id)
            
            if not solution:
                logger.error(f"Solution {solution_id} not found in database")
                flash(f'Solution {solution_id} not found in database', 'danger')
                return redirect(url_for('main.modify_file'))
            
            # Guardar datos en sesión para la confirmación
            session['compatibility_check'] = {
                'solution_id': solution_id,
                'compatibility_result': compatibility_result,
                'solution_info': {
                    'id': solution['id'],
                    'vehicle_type': solution['vehicle_type'],
                    'make': solution['make'],
                    'model': solution['model'],
                    'engine': solution['engine'],
                    'year': solution['year'],
                    'ecu_type': solution['ecu_type'],
                    'hardware_number': solution['hardware_number'],
                    'software_number': solution['software_number']
                },
                'analysis_details': {
                    'total_differences': total_differences,
                    'ori2_filename': ori2_filename
                }
            }
            session.modified = True
            
            logger.info(f"Redirecting to compatibility confirmation for solution {solution_id}")
            logger.info(f"Compatibility result: {compatibility_result['compatibility_percentage']}%")
            
            # Redirigir a página de confirmación de compatibilidad
            return redirect(url_for('main.confirm_compatibility'))
            
        finally:
            # Limpiar archivos temporales
            try:
                os.unlink(ori2_temp_path)
                os.unlink(ori1_temp_path)  # Limpiar también el archivo ORI1 temporal
            except Exception as e:
                logger.warning(f"Error cleaning up temp files: {e}")
                
    except Exception as e:
        logger.error(f"Error checking compatibility: {e}")
        flash(f'Error checking compatibility: {str(e)}', 'danger')
        return redirect(url_for('main.modify_file'))

@bp.route('/solutions/confirm_compatibility')
@login_required
def confirm_compatibility():
    """Show compatibility confirmation page."""
    logger.info("Accessing confirm_compatibility route")
    
    if 'compatibility_check' not in session:
        logger.warning("No compatibility check in progress - redirecting to modify_file")
        flash('No compatibility check in progress', 'warning')
        return redirect(url_for('main.modify_file'))
    
    compatibility_data = session['compatibility_check']
    logger.info(f"Rendering compatibility confirmation with {compatibility_data['compatibility_result']['compatibility_percentage']}% compatibility")
    
    return render_template('main/confirm_compatibility.html', 
                         compatibility_data=compatibility_data)

@bp.route('/solutions/apply_confirmed/<int:solution_id>', methods=['POST'])
@login_required
def apply_solution_confirmed(solution_id):
    """Apply solution to ORI2 file after compatibility confirmation."""
    if 'files' not in session or 'ori2' not in session['files']:
        flash('Please upload ORI2 file first', 'warning')
        return redirect(url_for('main.modify_file'))
    
    if 'compatibility_check' not in session or session['compatibility_check']['solution_id'] != solution_id:
        flash('Invalid compatibility check session', 'warning')
        return redirect(url_for('main.modify_file'))
    
    try:
        # Obtener diferencias desde S3
        storage = get_file_storage()
        differences_data, total_differences = storage.get_differences(solution_id)
        
        if not differences_data:
            flash(f'No differences found for solution {solution_id}', 'warning')
            return redirect(url_for('main.modify_file'))
        
        # Convertir formato de diferencias
        differences = []
        bit_size = 8  # Default
        for diff in differences_data:
            address = diff['memory_address']
            ori1_value = diff['ori1_value']
            mod1_value = diff['mod1_value']
            bit_size = diff['bit_size']
            differences.append((address, ori1_value, mod1_value))
        
        # Obtener archivo ORI2 desde S3
        ori2_info = session['files']['ori2']
        ori2_filename, ori2_file_data = storage.get_file(ori2_info['solution_id'], 'ori2')
        
        if not ori2_file_data:
            flash('Error retrieving ORI2 file from storage', 'danger')
            return redirect(url_for('main.modify_file'))
        
        # Crear archivo temporal para procesar
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.ori', delete=False) as ori2_temp:
            ori2_temp.write(ori2_file_data)
            ori2_temp_path = ori2_temp.name
        
        try:
            binary_handler = BinaryHandler()
            binary_handler.set_read_size(bit_size)
            ori2_data = binary_handler.read_file(ori2_temp_path)
            
            # Use the original ORI2 base name if available
            ori2_base_name = session.get('ori2_base_name', 'mod2')
            mod2_filename = f"{ori2_base_name}.mod"
            
            # Crear archivo MOD2 temporal
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.mod', delete=False) as mod2_temp:
                mod2_temp_path = mod2_temp.name
            
            success = binary_handler.write_mod2(ori2_data, differences, mod2_temp_path)
            
            if success:
                # Leer el archivo MOD2 generado
                with open(mod2_temp_path, 'rb') as f:
                    mod2_data = f.read()
                
                # Guardar MOD2 en S3
                mod2_stored = storage.store_file(ori2_info['solution_id'], 'mod2', mod2_filename, mod2_data)
                
                if mod2_stored:
                    if 'files' not in session:
                        session['files'] = {}
                    session['files']['mod2'] = {'solution_id': ori2_info['solution_id'], 'filename': mod2_filename}
                    
                    # Limpiar datos de compatibilidad de la sesión
                    session.pop('compatibility_check', None)
                    session.modified = True
                    
                    flash('Solution applied successfully', 'success')
                    return redirect(url_for('main.choose_mod2_filename'))
                else:
                    flash('Error storing MOD2 file', 'danger')
            else:
                flash('Error applying solution', 'danger')
        
        finally:
            # Limpiar archivos temporales
            try:
                os.unlink(ori2_temp_path)
                if 'mod2_temp_path' in locals():
                    os.unlink(mod2_temp_path)
            except Exception as e:
                logger.warning(f"Error cleaning up temp files: {e}")
                
        return redirect(url_for('main.modify_file'))
    except Exception as e:
        logger.error(f"Error applying solution: {e}")
        flash(f'Error applying solution: {str(e)}', 'danger')
        return redirect(url_for('main.modify_file'))

@bp.route('/solutions/<int:solution_id>/regenerate_differences', methods=['GET', 'POST'])
@login_required  
def regenerate_differences(solution_id):
    """Regenerate differences for a solution that doesn't have them."""
    with DatabaseManager() as db:
        # Verificar que la solución existe
        solutions = db.search_solutions({'id': solution_id})
        if not solutions:
            flash('Solution not found', 'danger')
            return redirect(url_for('main.solutions'))
        
        solution = solutions[0]
        
        # Verificar si ya tiene diferencias
        storage = get_file_storage()
        differences_data, total_differences = storage.get_differences(solution_id)
        
        if differences_data:
            flash(f'Solution {solution_id} already has {total_differences} differences', 'info')
            return redirect(url_for('main.solution_detail', solution_id=solution_id))
    
    if request.method == 'POST':
        if 'ori1_file' not in request.files or 'mod1_file' not in request.files:
            flash('Both ORI1 and MOD1 files are required', 'danger')
            return render_template('main/regenerate_differences.html', solution=solution)
        
        ori1_file = request.files['ori1_file']
        mod1_file = request.files['mod1_file']
        bit_size = int(request.form.get('bit_size', 8))
        
        if ori1_file.filename == '' or mod1_file.filename == '':
            flash('Both files must be selected', 'danger')
            return render_template('main/regenerate_differences.html', solution=solution)
        
        if not (allowed_file(ori1_file.filename) and allowed_file(mod1_file.filename)):
            flash('Invalid file type. Only .bin, .ori, .mod files are allowed', 'danger')
            return render_template('main/regenerate_differences.html', solution=solution)
        
        try:
            # Crear archivos temporales
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.ori', delete=False) as ori1_temp:
                ori1_file.save(ori1_temp.name)
                ori1_temp_path = ori1_temp.name
            
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.mod', delete=False) as mod1_temp:
                mod1_file.save(mod1_temp.name)
                mod1_temp_path = mod1_temp.name
            
            try:
                # Comparar archivos
                binary_handler = BinaryHandler()
                binary_handler.set_read_size(bit_size)
                
                ori1_data = binary_handler.read_file(ori1_temp_path)
                mod1_data = binary_handler.read_file(mod1_temp_path)
                
                if len(ori1_data) != len(mod1_data):
                    flash('Files have different sizes and cannot be compared', 'danger')
                    return render_template('main/regenerate_differences.html', solution=solution)
                
                differences = binary_handler.compare_files(ori1_data, mod1_data)
                
                if not differences:
                    flash('No differences found between the files', 'warning')
                    return render_template('main/regenerate_differences.html', solution=solution)
                
                # Preparar diferencias para almacenamiento
                differences_for_storage = []
                for address, ori1_value, mod1_value in differences:
                    differences_for_storage.append({
                        'memory_address': address,
                        'ori1_value': ori1_value,
                        'mod1_value': mod1_value,
                        'bit_size': bit_size
                    })
                
                # Guardar diferencias
                if storage.store_differences(solution_id, differences_for_storage):
                    flash(f'Successfully regenerated {len(differences)} differences for solution {solution_id}', 'success')
                    logger.info(f"Regenerated {len(differences)} differences for solution {solution_id}")
                    return redirect(url_for('main.solution_detail', solution_id=solution_id))
                else:
                    flash('Error storing differences', 'danger')
                    
            finally:
                # Limpiar archivos temporales
                try:
                    os.unlink(ori1_temp_path)
                    os.unlink(mod1_temp_path)
                except Exception as e:
                    logger.warning(f"Error cleaning up temp files: {e}")
                    
        except Exception as e:
            logger.error(f"Error regenerating differences: {e}")
            flash(f'Error processing files: {str(e)}', 'danger')
    
    return render_template('main/regenerate_differences.html', solution=solution)

@bp.route('/download/mod2')
@login_required
def download_mod2():
    if 'files' not in session or 'mod2' not in session['files']:
        flash('No MOD2 file available', 'warning')
        return redirect(url_for('main.solutions'))
    
    try:
        mod2_info = session['files']['mod2']
        storage = get_file_storage()
        
        # Descargar archivo desde S3
        mod2_filename, mod2_data = storage.get_file(mod2_info['solution_id'], 'mod2')
        
        if not mod2_data:
            flash('No MOD2 file available', 'warning')
            return redirect(url_for('main.solutions'))
        
        # Use user-provided filename if available
        download_filename = session.pop('mod2_download_name', None)
        if not download_filename:
            ori2_base_name = session.get('ori2_base_name', 'mod2')
            download_filename = f"{ori2_base_name}.mod"
        
        # Crear respuesta con el archivo
        response = make_response(mod2_data)
        response.headers['Content-Type'] = 'application/octet-stream'
        response.headers['Content-Disposition'] = f'attachment; filename="{download_filename}"'
        
        session['mod2_downloaded'] = True
        session.modified = True
        return response
        
    except Exception as e:
        logger.error(f"Error downloading MOD2: {e}")
        flash('Error downloading MOD2 file', 'danger')
        return redirect(url_for('main.solutions'))

@bp.route('/api/dropdown/<field_name>')
@login_required
def get_dropdown_values(field_name):
    """API route to get dropdown values."""
    parent_field = request.args.get('parent_field')
    parent_value = request.args.get('parent_value')
    
    with DatabaseManager() as db:
        filters = {}
        if parent_field and parent_value:
            filters[parent_field] = parent_value
        values = db.get_field_values(field_name, filters)
    
    return {'values': values}

@bp.route('/logout')
@login_required
def logout():
    # Clean up differences file if it exists
    filename = session.pop('differences_file', None)
    if filename:
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        try:
            os.remove(filepath)
        except OSError:
            pass
    logout_user()
    session.clear()
    resp = make_response(redirect(url_for('main.index')))
    resp.set_cookie('session', '', expires=0)
    return resp

@bp.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@bp.route('/choose_mod2_filename', methods=['GET', 'POST'])
@login_required
def choose_mod2_filename():
    if request.method == 'POST':
        filename = request.form.get('mod2_filename')
        if not filename:
            flash('Please enter a filename.', 'danger')
            return render_template('main/choose_mod2_filename.html')
        # Ensure .mod extension
        if not filename.lower().endswith('.mod'):
            filename += '.mod'
        session['mod2_download_name'] = filename
        session.modified = True
        return redirect(url_for('main.download_mod2'))
    return render_template('main/choose_mod2_filename.html')

@bp.route('/debug/config')
@login_required
def debug_config():
    """Debug endpoint to check configuration"""
    config_info = {
        'DB_HOST': current_app.config.get('DB_HOST', 'NOT_SET'),
        'DB_NAME': current_app.config.get('DB_NAME', 'NOT_SET'),
        'DB_USER': current_app.config.get('DB_USER', 'NOT_SET'),
        'DB_PORT': current_app.config.get('DB_PORT', 'NOT_SET'),
        'STORAGE_TYPE': current_app.config.get('STORAGE_TYPE', 'NOT_SET'),
        'SECRET_KEY_SET': 'YES' if current_app.config.get('SECRET_KEY') else 'NO',
        'SUPABASE_URL_SET': 'YES' if current_app.config.get('SUPABASE_URL') else 'NO',
        'AWS_KEYS_SET': 'YES' if current_app.config.get('AWS_ACCESS_KEY_ID') else 'NO',
    }
    
    return f"<pre>Config Debug:\n{json.dumps(config_info, indent=2)}</pre>"

@bp.route('/s3_status')
@login_required
def s3_status():
    """Verificar estado de conectividad S3"""
    try:
        storage = get_file_storage()
        
        # Información de configuración
        s3_config = {
            'bucket': current_app.config.get('AWS_S3_BUCKET'),
            'region': current_app.config.get('AWS_S3_REGION'),
            'storage_type': current_app.config.get('STORAGE_TYPE'),
            'has_credentials': bool(current_app.config.get('AWS_ACCESS_KEY_ID'))
        }
        
        # Test de conectividad
        try:
            connection_test = storage._test_connection()
            s3_config['connection_status'] = 'Connected' if connection_test else 'Failed'
            s3_config['status_class'] = 'success' if connection_test else 'danger'
        except Exception as e:
            s3_config['connection_status'] = f'Error: {str(e)}'
            s3_config['status_class'] = 'danger'
        
        return render_template('main/s3_status.html', s3_config=s3_config)
        
    except Exception as e:
        flash(f'Error verificando estado S3: {str(e)}', 'error')
        return redirect(url_for('main.index'))
