import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import os
from app import create_app
from app.database.db_manager import DatabaseManager
from werkzeug.security import generate_password_hash
import threading
import tempfile

class TestSelenium:
    @pytest.fixture(scope='class')
    def setup_app(self):
        """Set up the Flask application for testing."""
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SERVER_NAME'] = 'localhost:5000'
        
        temp_dir = tempfile.mkdtemp()
        app.config['UPLOAD_FOLDER'] = temp_dir
        
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
        
        threading.Thread(target=lambda: app.run(use_reloader=False)).start()
        time.sleep(1)  # Give the server time to start
        
        yield app
        
        os.system('rm -rf ' + temp_dir)
        with app.app_context():
            with DatabaseManager() as db:
                db.cursor.execute('DELETE FROM users WHERE username = %s', ('testuser',))
                db.conn.commit()
    
    @pytest.fixture(scope='class')
    def driver(self, setup_app):
        """Set up the Selenium WebDriver."""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        
        yield driver
        
        driver.quit()
    
    def test_login_flow(self, driver):
        """Test the login flow."""
        driver.get('http://localhost:5000/auth/login')
        
        username_input = driver.find_element(By.ID, 'username')
        password_input = driver.find_element(By.ID, 'password')
        submit_button = driver.find_element(By.ID, 'submit')
        
        username_input.send_keys('testuser')
        password_input.send_keys('password')
        submit_button.click()
        
        WebDriverWait(driver, 10).until(
            EC.url_to_be('http://localhost:5000/')
        )
        
        assert 'Welcome' in driver.page_source
        
    def test_upload_and_compare_flow(self, driver):
        """Test the upload and compare flow."""
        driver.get('http://localhost:5000/auth/login')
        username_input = driver.find_element(By.ID, 'username')
        password_input = driver.find_element(By.ID, 'password')
        submit_button = driver.find_element(By.ID, 'submit')
        
        username_input.send_keys('testuser')
        password_input.send_keys('password')
        submit_button.click()
        
        driver.get('http://localhost:5000/upload')
        
        ori1_file = tempfile.NamedTemporaryFile(suffix='.bin', delete=False)
        ori1_file.write(b'\x00\x01\x02\x03')
        ori1_file.close()
        
        mod1_file = tempfile.NamedTemporaryFile(suffix='.bin', delete=False)
        mod1_file.write(b'\x00\x01\x03\x03')  # Difference at index 2
        mod1_file.close()
        
        try:
            file_input = driver.find_element(By.ID, 'file')
            file_type_select = driver.find_element(By.ID, 'file_type')
            submit_button = driver.find_element(By.ID, 'submit')
            
            file_input.send_keys(ori1_file.name)
            file_type_select.send_keys('ORI1')
            submit_button.click()
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'alert-success'))
            )
            
            file_input = driver.find_element(By.ID, 'file')
            file_type_select = driver.find_element(By.ID, 'file_type')
            submit_button = driver.find_element(By.ID, 'submit')
            
            file_input.send_keys(mod1_file.name)
            file_type_select.send_keys('MOD1')
            submit_button.click()
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'alert-success'))
            )
            
            driver.get('http://localhost:5000/compare')
            
            bit_size_select = driver.find_element(By.ID, 'bit_size')
            submit_button = driver.find_element(By.ID, 'submit')
            
            bit_size_select.send_keys('8')
            submit_button.click()
            
            WebDriverWait(driver, 10).until(
                EC.url_to_be('http://localhost:5000/compare/results')
            )
            
            assert 'Comparison Results' in driver.page_source
            assert '2' in driver.page_source  # Memory address
            assert '2' in driver.page_source  # Original value
            assert '3' in driver.page_source  # Modified value
        finally:
            os.unlink(ori1_file.name)
            os.unlink(mod1_file.name)
    
    def test_solutions_flow(self, driver):
        """Test the solutions flow."""
        driver.get('http://localhost:5000/auth/login')
        username_input = driver.find_element(By.ID, 'username')
        password_input = driver.find_element(By.ID, 'password')
        submit_button = driver.find_element(By.ID, 'submit')
        
        username_input.send_keys('testuser')
        password_input.send_keys('password')
        submit_button.click()
        
        driver.get('http://localhost:5000/solutions')
        
        assert 'Solutions' in driver.page_source
        
        add_button = driver.find_element(By.LINK_TEXT, 'Add Solution')
        add_button.click()
        
        assert 'Add Solution' in driver.page_source
