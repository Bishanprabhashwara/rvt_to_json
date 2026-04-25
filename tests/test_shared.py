from unittest.mock import MagicMock
from app.agents.shared import _resolve_boolean, safe_float, convert_to_m, unwrap_ifc_value

def test_resolve_boolean():
    assert _resolve_boolean(True) is True
    assert _resolve_boolean("True") is True
    assert _resolve_boolean("yes") is True
    assert _resolve_boolean(1) is True
    assert _resolve_boolean(False) is False
    assert _resolve_boolean("False") is False
    assert _resolve_boolean("no") is False
    assert _resolve_boolean(0) is False
    assert _resolve_boolean(None) is None

def test_safe_float():
    assert safe_float(10) == 10.0
    assert safe_float("10.5") == 10.5
    assert safe_float("invalid") is None
    assert safe_float(None) is None

def test_convert_to_m():
    assert convert_to_m(1000, 0.001) == 1.0  # mm to m
    assert convert_to_m(1, 0.3048) == 0.3048 # ft to m
    assert convert_to_m("string", 1.0) == "string"

def test_unwrap_ifc_value():
    mock_val = MagicMock()
    mock_val.wrappedValue = "hello"
    assert unwrap_ifc_value(mock_val) == "hello"
    assert unwrap_ifc_value("already_raw") == "already_raw"
