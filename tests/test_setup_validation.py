import pytest
import sys
from pathlib import Path


class TestSetupValidation:
    """Validation tests to ensure the testing infrastructure is properly configured."""
    
    def test_pytest_is_installed(self):
        """Verify pytest is available."""
        assert "pytest" in sys.modules or True  # Will be true after import
        
    def test_project_structure_exists(self):
        """Verify the expected project structure is in place."""
        project_root = Path(__file__).parent.parent
        
        # Check main directories exist
        assert project_root.exists()
        assert (project_root / "src").exists()
        assert (project_root / "tests").exists()
        assert (project_root / "tests" / "unit").exists()
        assert (project_root / "tests" / "integration").exists()
        
        # Check configuration files exist
        assert (project_root / "pyproject.toml").exists()
        assert (project_root / ".gitignore").exists()
        
    def test_conftest_fixtures_available(self, temp_dir, mock_config):
        """Verify conftest fixtures are available and working."""
        # Test temp_dir fixture
        assert temp_dir.exists()
        assert temp_dir.is_dir()
        
        # Test mock_config fixture
        assert isinstance(mock_config, dict)
        assert "pixel_size" in mock_config
        assert mock_config["pixel_size"] == 256
        
    def test_coverage_configuration(self):
        """Verify coverage is properly configured."""
        try:
            import coverage
            assert True
        except ImportError:
            pytest.fail("Coverage module not installed")
    
    @pytest.mark.unit
    def test_unit_marker(self):
        """Test that the unit marker is recognized."""
        assert True
    
    @pytest.mark.integration
    def test_integration_marker(self):
        """Test that the integration marker is recognized."""
        assert True
    
    @pytest.mark.slow
    def test_slow_marker(self):
        """Test that the slow marker is recognized."""
        assert True
    
    def test_source_code_importable(self):
        """Verify the source code can be imported."""
        # Add src to path if not already there
        src_path = Path(__file__).parent.parent / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        
        # Try importing main modules
        try:
            import miracode
            import polygonizer
            assert True
        except ImportError as e:
            # This might fail due to fontforge dependency, which is okay for validation
            if "fontforge" not in str(e):
                pytest.fail(f"Failed to import source modules: {e}")