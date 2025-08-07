import pytest
import os
from app.database.db_manager import DatabaseManager
import psycopg2
from app import create_app

class TestDatabaseManager:
    @pytest.fixture
    def app(self):
        """Create a test Flask application."""
        app = create_app()
        app.config['TESTING'] = True
        return app
        
    @pytest.fixture
    def db_manager(self, app):
        """Create a test database manager."""
        with app.app_context():
            db = DatabaseManager()
            yield db
            db.close()
        
    def test_connection(self, app, db_manager):
        """Test database connection."""
        with app.app_context():
            assert db_manager.conn is not None
            assert db_manager.cursor is not None
        
    def test_context_manager(self, app):
        """Test context manager functionality."""
        with app.app_context():
            with DatabaseManager() as db:
                assert db.conn is not None
                assert db.cursor is not None
            
    def test_search_solutions(self, app, db_manager):
        """Test searching solutions with filters."""
        with app.app_context():
            filters = {'vehicle_type': 'Car', 'make': 'Toyota'}
            solutions = db_manager.search_solutions(filters)
            assert isinstance(solutions, list)
        
    def test_get_field_values(self, app, db_manager):
        """Test getting field values."""
        with app.app_context():
            values = db_manager.get_field_values('vehicle_type')
            assert isinstance(values, list)
            assert len(values) > 0
        
    def test_get_dependent_fields(self, app, db_manager):
        """Test getting dependent fields."""
        with app.app_context():
            dependent_fields = db_manager.get_dependent_fields()
            assert isinstance(dependent_fields, dict)
            assert 'make' in dependent_fields
            assert 'vehicle_type' in dependent_fields['make']
        
    def test_add_and_delete_solution(self, app, db_manager):
        """Test adding and deleting a solution."""
        with app.app_context():
            vehicle_info = {
                'vehicle_type': 'Car',
                'make': 'Toyota',
                'model': 'Camry',
                'engine': '2.5L',
                'year': 2022,
                'hardware_number': 'HW002',
                'software_number': 'SW002',
                'software_update_number': 'UPDATE001',
                'ecu_type': 'Type A',
                'transmission_type': 'Automatic'
            }
            solution_types = {
                'stage_1': True,
                'description': 'Test solution'
            }
            
            solution_id = db_manager.add_solution(vehicle_info, solution_types)
            assert solution_id is not None
            
            solutions = db_manager.search_solutions({'id': solution_id})
            assert len(solutions) == 1
            assert solutions[0]['id'] == solution_id
            
            assert db_manager.delete_solution(solution_id)
            
            solutions = db_manager.search_solutions({'id': solution_id})
            assert len(solutions) == 0
        
    def test_update_solution(self, app, db_manager):
        """Test updating a solution."""
        with app.app_context():
            vehicle_info = {
                'vehicle_type': 'Car',
                'make': 'Toyota',
                'model': 'Camry',
                'engine': '2.5L',
                'year': 2022,
                'hardware_number': 'HW002',
                'software_number': 'SW002',
                'software_update_number': 'UPDATE001',
                'ecu_type': 'Type A',
                'transmission_type': 'Automatic'
            }
            solution_types = {
                'stage_1': True,
                'description': 'Test solution'
            }
            
            solution_id = db_manager.add_solution(vehicle_info, solution_types)
            assert solution_id is not None
            
            updated_vehicle_info = vehicle_info.copy()
            updated_vehicle_info['year'] = 2023
            
            assert db_manager.update_solution(solution_id, updated_vehicle_info)
            
            solutions = db_manager.search_solutions({'id': solution_id})
            assert len(solutions) == 1
            assert solutions[0]['year'] == 2023
            
            assert db_manager.delete_solution(solution_id)
        
    def test_store_file_differences(self, app, db_manager):
        """Test storing file differences."""
        with app.app_context():
            vehicle_info = {
                'vehicle_type': 'Car',
                'make': 'Toyota',
                'model': 'Camry',
                'engine': '2.5L',
                'year': 2022,
                'hardware_number': 'HW002',
                'software_number': 'SW002',
                'software_update_number': 'UPDATE001',
                'ecu_type': 'Type A',
                'transmission_type': 'Automatic'
            }
            solution_types = {
                'stage_1': True,
                'description': 'Test solution'
            }
            
            solution_id = db_manager.add_solution(vehicle_info, solution_types)
            assert solution_id is not None
            
            differences = [
                {
                    'memory_address': 100,
                    'ori1_value': 1,
                    'mod1_value': 2,
                    'bit_size': 8
                },
                {
                    'memory_address': 200,
                    'ori1_value': 3,
                    'mod1_value': 4,
                    'bit_size': 8
                }
            ]
            
            assert db_manager.store_file_differences(solution_id, differences)
            
            db_manager.cursor.execute(
                'SELECT memory_address FROM file_differences WHERE solution_id = %s',
                (solution_id,)
            )
            addresses = [row[0] for row in db_manager.cursor.fetchall()]
            assert 100 in addresses
            assert 200 in addresses
            
            assert db_manager.delete_solution(solution_id)
