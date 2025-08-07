import pytest
from app import create_app
from app.database.db_manager import DatabaseManager
import os
import tempfile
import json
from flask_login import current_user
from werkzeug.security import generate_password_hash

class TestRoutes:
    @pytest.fixture
    def client(self):
        """Create a test client for the Flask application."""
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        
        with tempfile.TemporaryDirectory() as temp_dir:
            app.config['UPLOAD_FOLDER'] = temp_dir
            
            with app.test_client() as client:
                with app.app_context():
                    with DatabaseManager() as db:
                        try:
                            db.cursor.execute(
                                'INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id',
                                ('testuser', 'test@example.com', generate_password_hash('password'))
                            )
                            db.conn.commit()
                        except:
                            db.conn.rollback()
                            
                yield client
                
                with app.app_context():
                    with DatabaseManager() as db:
                        db.cursor.execute('DELETE FROM users WHERE username = %s', ('testuser',))
                        db.conn.commit()
    
    def login(self, client, username='testuser', password='password'):
        """Helper function to log in a user."""
        return client.post('/auth/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)
        
    def logout(self, client):
        """Helper function to log out a user."""
        return client.get('/auth/logout', follow_redirects=True)
    
    def test_index_route(self, client):
        """Test the index route."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Vehicle Binary Tool' in response.data
        
    def test_login_route(self, client):
        """Test the login route."""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'Login' in response.data
        
        response = self.login(client)
        assert response.status_code == 200
        assert b'Welcome' in response.data
        
        self.logout(client)
        response = client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Login unsuccessful' in response.data
        
    def test_register_route(self, client):
        """Test the register route."""
        response = client.get('/auth/register')
        assert response.status_code == 200
        assert b'Register' in response.data
        
        response = client.post('/auth/register', data={
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'password',
            'confirm_password': 'password'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Your account has been created' in response.data
        
        response = client.post('/auth/register', data={
            'username': 'testuser',
            'email': 'another@example.com',
            'password': 'password',
            'confirm_password': 'password'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'That username is taken' in response.data
        
    def test_logout_route(self, client):
        """Test the logout route."""
        self.login(client)
        response = self.logout(client)
        assert response.status_code == 200
        assert b'You have been logged out' in response.data
        
    def test_protected_routes_without_login(self, client):
        """Test protected routes without login."""
        routes = [
            '/upload',
            '/compare',
            '/solutions',
            '/api/dropdown/vehicle_type'
        ]
        
        for route in routes:
            response = client.get(route, follow_redirects=True)
            assert response.status_code == 200
            assert b'Login' in response.data
            
    def test_upload_route(self, client):
        """Test the upload route."""
        self.login(client)
        
        response = client.get('/upload')
        assert response.status_code == 200
        assert b'Upload Files' in response.data
        
        with tempfile.NamedTemporaryFile(suffix='.bin') as temp_file:
            temp_file.write(b'\x00\x01\x02\x03')
            temp_file.flush()
            
            with open(temp_file.name, 'rb') as f:
                response = client.post('/upload', data={
                    'file': (f, 'test.bin'),
                    'file_type': 'ori1'
                }, follow_redirects=True)
                
            assert response.status_code == 200
            assert b'ORI1 file uploaded successfully' in response.data
            
    def test_compare_route(self, client):
        """Test the compare route."""
        self.login(client)
        
        response = client.get('/compare')
        assert response.status_code == 200
        assert b'Compare Files' in response.data
        
        response = client.post('/compare', follow_redirects=True)
        assert response.status_code == 200
        assert b'Please upload ORI1 and MOD1 files first' in response.data
        
    def test_solutions_route(self, client):
        """Test the solutions route."""
        self.login(client)
        
        response = client.get('/solutions')
        assert response.status_code == 200
        assert b'Solutions' in response.data
        
    def test_api_dropdown_route(self, client):
        """Test the API dropdown route."""
        self.login(client)
        
        response = client.get('/api/dropdown/vehicle_type')
        assert response.status_code == 200
        assert response.json is not None
        
        response = client.get('/api/dropdown/make?vehicle_type=Car')
        assert response.status_code == 200
        assert response.json is not None
