import pytest
from app.utils.path_utils import _normalize_name, resolve_input_path

def test_normalize_name():
    assert _normalize_name("  Test   Name  ") == "test name"
    assert _normalize_name("UPPER CASE") == "upper case"
    assert _normalize_name("already.normalized") == "already.normalized"

def test_resolve_input_path_exists(tmp_path):
    # Create a dummy file
    d = tmp_path / "models"
    d.mkdir()
    f = d / "test.rvt"
    f.write_text("dummy")
    
    resolved = resolve_input_path(str(f))
    assert resolved == f.resolve()

def test_resolve_input_path_fuzzy(tmp_path, monkeypatch):
    # Create a dummy file with spaces
    d = tmp_path / "models"
    d.mkdir()
    f = d / "My Revit Model.rvt"
    f.write_text("dummy")
    
    # Change CWD to the tmp_path/models to test local discovery
    monkeypatch.chdir(d)
    
    # Try resolving with a slightly different name (collapsed spaces)
    # We expect a FileNotFoundError because it's a fuzzy match, not an exact match
    with pytest.raises(FileNotFoundError) as excinfo:
        resolve_input_path("MyRevitModel.rvt")
    
    assert "Did you mean" in str(excinfo.value)
    assert "My Revit Model.rvt" in str(excinfo.value)
