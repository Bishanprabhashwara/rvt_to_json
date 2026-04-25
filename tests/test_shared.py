from unittest.mock import MagicMock
from app.agents.shared import (
    _resolve_boolean, safe_float, convert_to_m, unwrap_ifc_value,
    entity_storey, entity_material, length_scale_to_m, 
    extract_project_metadata, extract_site_dimensions, entity_material_layers,
    llm_call, _parse_retry_delay
)

def test_resolve_boolean():
    assert _resolve_boolean(True) is True
    assert _resolve_boolean("True") is True
    assert _resolve_boolean(False) is False
    assert _resolve_boolean(None) is None

def test_safe_float():
    assert safe_float(10) == 10.0
    assert safe_float("invalid") is None

def test_convert_to_m():
    assert convert_to_m(1000, 0.001) == 1.0

def test_unwrap_ifc_value():
    mock_val = MagicMock()
    mock_val.wrappedValue = "hello"
    assert unwrap_ifc_value(mock_val) == "hello"
    assert unwrap_ifc_value(None) is None

def test_entity_storey():
    ent = MagicMock()
    rel = MagicMock()
    rel.is_a.side_effect = lambda t: t == "IfcRelContainedInSpatialStructure"
    storey = MagicMock()
    storey.is_a.side_effect = lambda t: t == "IfcBuildingStorey"
    storey.Name = "Level 1"
    rel.RelatingStructure = storey
    ent.ContainedInStructure = [rel]
    assert entity_storey(ent) == "Level 1"

def test_entity_material_simple():
    ent = MagicMock()
    rel = MagicMock()
    rel.is_a.side_effect = lambda t: t == "IfcRelAssociatesMaterial"
    mat = MagicMock()
    mat.is_a.side_effect = lambda t: t == "IfcMaterial"
    mat.Name = "Concrete"
    rel.RelatingMaterial = mat
    ent.HasAssociations = [rel]
    assert entity_material(ent) == "Concrete"

def test_length_scale_to_m_si():
    model = MagicMock()
    ua = MagicMock()
    unit = MagicMock()
    unit.is_a.side_effect = lambda t: t == "IfcSIUnit"
    unit.UnitType = "LENGTHUNIT"
    unit.Name = "METRE"
    unit.Prefix = "MILLI"
    ua.Units = [unit]
    model.by_type.return_value = [ua]
    assert length_scale_to_m(model) == 0.001

def test_length_scale_to_m_imperial():
    model = MagicMock()
    ua = MagicMock()
    unit = MagicMock()
    unit.is_a.side_effect = lambda t: t == "IfcConversionBasedUnit"
    unit.UnitType = "LENGTHUNIT"
    unit.Name = "FOOT"
    ua.Units = [unit]
    model.by_type.return_value = [ua]
    assert length_scale_to_m(model) == 0.3048

def test_extract_project_metadata():
    model = MagicMock()
    proj = MagicMock()
    proj.Name = "TestProj"
    model.by_type.side_effect = lambda t: [proj] if t == "IfcProject" else []
    meta = extract_project_metadata(model)
    assert meta["project_name"] == "TestProj"

def test_extract_site_dimensions():
    model = MagicMock()
    st = MagicMock()
    st.Name = "Level 0"
    st.Elevation = 0.0
    model.by_type.return_value = [st]
    dims = extract_site_dimensions(model, 1.0)
    assert len(dims["ffl_levels"]) == 1

def test_get_host_wall():
    from app.agents.shared import get_host_wall
    door = MagicMock()
    rel = MagicMock()
    opening = MagicMock()
    void_rel = MagicMock()
    wall = MagicMock()
    door.FillsVoids = [rel]
    rel.RelatingOpeningElement = opening
    opening.VoidsElements = [void_rel]
    void_rel.RelatingBuildingElement = wall
    assert get_host_wall(door) == wall

def test_entity_material_layers():
    ent = MagicMock()
    rel = MagicMock()
    rel.is_a.side_effect = lambda t: t == "IfcRelAssociatesMaterial"
    mat = MagicMock()
    mat.is_a.side_effect = lambda t: t == "IfcMaterialLayerSet"
    layer = MagicMock()
    m_obj = MagicMock()
    m_obj.Name = "Brick"
    layer.Material = m_obj
    layer.LayerThickness = 110.0
    mat.MaterialLayers = [layer]
    rel.RelatingMaterial = mat
    ent.HasAssociations = [rel]
    layers = entity_material_layers(ent)
    assert len(layers) == 1
    assert str(layers[0]["name"]) == "Brick"

def test_llm_call_success():
    llm = MagicMock()
    llm.invoke.return_value.content = "answer"
    assert llm_call(llm, "prompt") == "answer"

def test_parse_retry_delay():
    err_msg = "{'details': [{'retryDelay': '5s'}]}"
    assert _parse_retry_delay(err_msg) == 5.0
    assert _parse_retry_delay("no time info") == 60.0
