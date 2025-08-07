import pytest
import os
import tempfile
from app.utils.binary_handler import BinaryHandler

class TestBinaryHandler:
    @pytest.fixture
    def binary_handler(self):
        """Create a binary handler instance."""
        return BinaryHandler()
        
    @pytest.fixture
    def test_files(self):
        """Create test binary files."""
        with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f1:
            f1.write(bytes([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]))
            file1_path = f1.name
            
        with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f2:
            f2.write(bytes([0, 1, 2, 3, 5, 5, 6, 7, 8, 9]))  # Difference at index 4
            file2_path = f2.name
            
        yield (file1_path, file2_path)
        
        os.unlink(file1_path)
        os.unlink(file2_path)
        
    def test_set_read_size(self, binary_handler):
        """Test setting read size."""
        binary_handler.set_read_size(16)
        assert binary_handler.read_size == 16
        
        binary_handler.set_read_size(32)
        assert binary_handler.read_size == 32
        
    def test_read_file(self, binary_handler, test_files):
        """Test reading a file."""
        file1_path, _ = test_files
        
        data = binary_handler.read_file(file1_path)
        assert len(data) == 10
        assert data[0] == 0
        assert data[9] == 9
        
    def test_compare_files(self, binary_handler, test_files):
        """Test comparing files."""
        file1_path, file2_path = test_files
        
        differences = binary_handler.compare_files(file1_path, file2_path)
        assert len(differences) == 1
        assert differences[0][0] == 4  # Difference at index 4
        assert differences[0][1] == 4  # Original value
        assert differences[0][2] == 5  # Modified value
        
    def test_write_mod2(self, binary_handler, test_files):
        """Test writing a MOD2 file."""
        file1_path, _ = test_files
        
        ori2_data = binary_handler.read_file(file1_path)
        
        differences = [(4, 4, 5)]
        
        with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
            output_path = f.name
            
        try:
            success = binary_handler.write_mod2(ori2_data, differences, output_path)
            assert success
            
            mod2_data = binary_handler.read_file(output_path)
            
            assert mod2_data[4] == 5  # Value at index 4 should be changed
            assert mod2_data[0] == 0  # Other values should remain the same
            assert mod2_data[9] == 9
        finally:
            os.unlink(output_path)
            
    def test_verify_structure(self, binary_handler, test_files):
        """Test structure verification."""
        file1_path, file2_path = test_files
        
        result = binary_handler.verify_structure(file1_path, file2_path)
        
        assert isinstance(result, dict)
        assert 'size_match' in result
        assert 'size1' in result
        assert 'size2' in result
        assert 'structural_similarity' in result
        
        assert result['size_match'] is True
        assert result['size1'] == result['size2']
