"""
API Routes Module

This module provides API endpoints for:
- Dynamic dropdown values
- Vehicle configuration data
"""

from flask import jsonify, request
from app.api import bp
from app.database.db_manager import DatabaseManager
from flask_login import login_required
import pandas as pd

@bp.route('/api/dropdown/<field_name>')
@login_required
def get_dropdown_values(field_name):
    """
    Get dropdown values for a field based on parent selections.
    
    Args:
        field_name: Name of the field to get values for
        
    Query Parameters:
        Any parent field and value pairs
        
    Returns:
        JSON array of field values
    """
    # Collect all possible filters from request.args
    filters = {k: v for k, v in request.args.items() if k != 'field_name'}
    with DatabaseManager() as db:
        parent_field = request.args.get('parent_field')
        parent_value = request.args.get('parent_value')
        filters = {}
        if parent_field and parent_value:
            filters[parent_field] = parent_value
        values = db.get_field_values(field_name, filters)
    return {'values': values}

@bp.route('/vehicle_info/<int:vehicle_id>')
@login_required
def get_vehicle_info(vehicle_id):
    """
    Get vehicle information by ID.
    
    Args:
        vehicle_id: Vehicle info ID
        
    Returns:
        JSON object with vehicle information
    """
    with DatabaseManager() as db:
        db.cursor.execute('''
            SELECT * FROM vehicle_info WHERE id = %s
        ''', (vehicle_id,))
        
        vehicle = db.cursor.fetchone()
        if not vehicle:
            return jsonify({'error': 'Vehicle not found'}), 404
        
        columns = [desc[0] for desc in db.cursor.description]
        vehicle_dict = dict(zip(columns, vehicle))
        
        return jsonify(vehicle_dict)

@bp.route('/solution_types/<int:solution_id>')
@login_required
def get_solution_types(solution_id):
    """
    Get solution types by solution ID.
    
    Args:
        solution_id: Solution ID
        
    Returns:
        JSON object with solution types
    """
    with DatabaseManager() as db:
        db.cursor.execute('''
            SELECT * FROM solution_types WHERE solution_id = %s
        ''', (solution_id,))
        
        solution_types = db.cursor.fetchone()
        if not solution_types:
            return jsonify({'error': 'Solution types not found'}), 404
        
        columns = [desc[0] for desc in db.cursor.description]
        types_dict = dict(zip(columns, solution_types))
        
        return jsonify(types_dict)


