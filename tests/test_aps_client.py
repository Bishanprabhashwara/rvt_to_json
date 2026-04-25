import pytest
from unittest.mock import MagicMock, patch
from app.adapters.aps_client import (
    get_access_token, ensure_bucket, upload_file, 
    start_translation, poll_translation, download_ifc
)

@patch("requests.post")
def test_get_access_token_success(mock_post, monkeypatch):
    monkeypatch.setenv("APS_AUTH_URL", "http://test-auth")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"access_token": "fake-token"}
    mock_post.return_value = mock_resp
    assert get_access_token("id", "secret") == "fake-token"

@patch("requests.get")
@patch("requests.post")
def test_ensure_bucket(mock_post, mock_get):
    mock_get.return_value.status_code = 404
    mock_post.return_value.status_code = 200
    ensure_bucket("token")
    mock_post.assert_called_once()

@patch("requests.post")
def test_start_translation(mock_post):
    mock_post.return_value.status_code = 201
    start_translation("token", "urn")
    mock_post.assert_called_once()

@patch("requests.get")
def test_poll_translation_success(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"status": "success"}
    assert poll_translation("token", "urn") == "urn"

@patch("requests.get")
def test_poll_translation_failure(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"status": "failed"}
    with pytest.raises(RuntimeError):
        poll_translation("token", "urn")

@patch("requests.get")
def test_download_ifc(mock_get, tmp_path):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "derivatives": [{"outputType": "ifc", "children": [{"role": "ifc", "urn": "ifc-urn"}]}]
    }
    mock_get.return_value.iter_content.return_value = [b"data"]
    out = tmp_path / "test.ifc"
    download_ifc("token", "urn", str(out))
    assert out.exists()

@patch("os.path.getsize")
@patch("requests.post")
@patch("requests.put")
@patch("requests.get")
def test_upload_file(mock_get, mock_put, mock_post, mock_size, tmp_path):
    mock_size.return_value = 100
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"urls": ["http://put-url"], "uploadKey": "ukey"}
    mock_post.return_value.status_code = 200
    f = tmp_path / "test.rvt"
    f.write_text("dummy")
    urn = upload_file("token", str(f))
    assert urn is not None
    mock_put.assert_called_once()
