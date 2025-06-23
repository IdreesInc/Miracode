import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock


@pytest.fixture
def temp_dir():
    """Create a temporary directory that's automatically cleaned up after the test."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def temp_file(temp_dir):
    """Create a temporary file in the temp directory."""
    def _create_temp_file(filename="test_file.txt", content=""):
        file_path = temp_dir / filename
        file_path.write_text(content)
        return file_path
    return _create_temp_file


@pytest.fixture
def sample_json_data():
    """Provide sample JSON data for testing."""
    return {
        "characters": [
            {"codepoint": 65, "name": "A", "pixels": [[1, 1], [2, 2]]},
            {"codepoint": 66, "name": "B", "pixels": [[3, 3], [4, 4]]}
        ],
        "ligatures": [
            {"name": "arrow", "sequence": "->", "pixels": [[5, 5], [6, 6]]}
        ]
    }


@pytest.fixture
def mock_json_file(temp_file, sample_json_data):
    """Create a mock JSON file with sample data."""
    def _create_json_file(filename="test.json", data=None):
        if data is None:
            data = sample_json_data
        return temp_file(filename, json.dumps(data, indent=2))
    return _create_json_file


@pytest.fixture
def mock_fontforge():
    """Mock the fontforge module for testing without actual font generation."""
    mock_ff = MagicMock()
    mock_font = MagicMock()
    mock_ff.font.return_value = mock_font
    mock_font.createChar.return_value = MagicMock()
    return mock_ff


@pytest.fixture
def mock_config():
    """Provide a mock configuration for testing."""
    return {
        "pixel_size": 256,
        "font_name": "TestFont",
        "version": "1.0.0",
        "author": "Test Author",
        "license": "Test License"
    }


@pytest.fixture
def character_data():
    """Sample character data for testing font generation."""
    return [
        {
            "codepoint": 65,
            "name": "LATIN CAPITAL LETTER A",
            "pixels": [
                [0, 0], [1, 0], [2, 0],
                [0, 1], [2, 1],
                [0, 2], [1, 2], [2, 2],
                [0, 3], [2, 3],
                [0, 4], [2, 4]
            ]
        },
        {
            "codepoint": 97,
            "name": "LATIN SMALL LETTER A",
            "pixels": [
                [1, 0], [2, 0],
                [0, 1], [2, 1],
                [0, 2], [1, 2], [2, 2],
                [0, 3], [2, 3]
            ]
        }
    ]


@pytest.fixture
def ligature_data():
    """Sample ligature data for testing."""
    return [
        {
            "name": "arrow_right",
            "sequence": "->",
            "pixels": [[0, 2], [1, 2], [2, 2], [3, 1], [3, 3]]
        },
        {
            "name": "arrow_left",
            "sequence": "<-",
            "pixels": [[3, 2], [2, 2], [1, 2], [0, 1], [0, 3]]
        }
    ]


@pytest.fixture
def diacritic_data():
    """Sample diacritic data for testing."""
    return [
        {
            "name": "COMBINING ACUTE ACCENT",
            "codepoint": 769,
            "pixels": [[1, 0], [2, 1]]
        },
        {
            "name": "COMBINING GRAVE ACCENT",
            "codepoint": 768,
            "pixels": [[2, 0], [1, 1]]
        }
    ]


@pytest.fixture(autouse=True)
def reset_modules(monkeypatch):
    """Reset module imports between tests to ensure clean state."""
    import sys
    modules_to_reset = [
        mod for mod in sys.modules 
        if mod.startswith('src.') or mod in ['miracode', 'polygonizer', 'monocraft']
    ]
    for mod in modules_to_reset:
        monkeypatch.delitem(sys.modules, mod, raising=False)


@pytest.fixture
def capture_logs(caplog):
    """Fixture to easily capture and assert on log messages."""
    with caplog.at_level("DEBUG"):
        yield caplog