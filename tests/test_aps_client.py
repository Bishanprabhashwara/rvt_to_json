from unittest.mock import patch, MagicMock
from app.adapters.aps_client import _get_config, get_access_token

def test_get_config_defaults(monkeypatch):
    monkeypatch.delenv("APS_AUTH_URL", raising=False)
    cfg = _get_config()
    assert cfg["AUTH_URL"] is None  # Matches your latest cleanup
    assert cfg["BUCKET"] is None

def test_get_config_override(monkeypatch):
    monkeypatch.setenv("BUCKET_KEY", "custom-bucket")
    cfg = _get_config()
    assert cfg["BUCKET"] == "custom-bucket"

@patch("requests.post")
def test_get_access_token_success(mock_post, monkeypatch):
    monkeypatch.setenv("APS_AUTH_URL", "http://test-auth")
    
    # Mock response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"access_token": "fake-token-123"}
    mock_post.return_value = mock_resp
    
    token = get_access_token("id", "secret")
    assert token == "fake-token-123"
    mock_post.assert_called_once()
