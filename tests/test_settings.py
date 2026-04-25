from unittest.mock import patch
from app.config.settings import Settings,_read_value_from_env_file

@patch("pathlib.Path.exists")
def test_settings_object(mock_exists, monkeypatch):
    mock_exists.return_value = False
    monkeypatch.setenv("APS_CLIENT_ID", "fixed_id")
    s = Settings.load()
    assert s.aps_client_id == "fixed_id"

def test_settings_load_relative(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = tmp_path / "custom.env"
    env.write_text("APS_CLIENT_ID=custom")
    s = Settings.load(env_file="custom.env")
    assert s.aps_client_id == "custom"

def test_read_value_from_env_file_missing(tmp_path):
    assert _read_value_from_env_file(tmp_path / "missing", "KEY") is None

