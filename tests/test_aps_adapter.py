from unittest.mock import patch
from app.adapters.aps_adapter import APSAdapter

def test_aps_adapter_initialization():
    adapter = APSAdapter("id", "secret")
    assert adapter.client_id == "id"
    assert adapter.client_secret == "secret"

@patch("app.adapters.aps_client.get_access_token")
@patch("app.adapters.aps_client.ensure_bucket")
@patch("app.adapters.aps_client.upload_file")
@patch("app.adapters.aps_client.start_translation")
@patch("app.adapters.aps_client.poll_translation")
@patch("app.adapters.aps_client.download_ifc")
def test_aps_adapter_full_flow(mock_dl, mock_poll, mock_start, mock_up, mock_eb, mock_token):
    mock_token.return_value = "token"
    mock_up.return_value = "urn"
    mock_poll.return_value = "urn"
    
    adapter = APSAdapter("id", "secret")
    adapter.convert_rvt_to_ifc("input.rvt", "output.ifc")
    
    mock_token.assert_called_once()
    mock_up.assert_called_once()
    mock_dl.assert_called_once_with("token", "urn", "output.ifc")
