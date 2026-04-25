import pytest
from unittest.mock import MagicMock, patch
from app.agents.load_model_agent import load_model_agent
from app.agents.extract_elements_agent import extract_elements_agent
from app.agents.llm_gap_analysis_agent import llm_gap_analysis_agent
from app.agents.schema_alignment_agent import schema_alignment_agent

@pytest.fixture
def mock_state():
    mock_model = MagicMock()
    mock_model.by_type.return_value = []
    mock_model.schema = "IFC4"
    
    return {
        "ifc_path": "test.ifc",
        "model": mock_model,
        "unit_scale_to_m": 1.0,
        "data": {"walls": [], "slabs": [], "openings": {"doors": [], "windows": []}},
        "errors": []
    }

# 1. Test Load Model Agent
@patch("ifcopenshell.open")
@patch("app.agents.load_model_agent.length_scale_to_m")
def test_load_model_agent(mock_scale, mock_open, mock_state):
    mock_open.return_value = mock_state["model"]
    mock_scale.return_value = 0.001 # Assume mm
    
    new_state = load_model_agent({"ifc_path": "dummy.ifc"})
    
    assert new_state["model"] is not None
    assert new_state["unit_scale_to_m"] == 0.001
    mock_open.assert_called_once_with("dummy.ifc")

# 2. Test Extract Elements Agent
@patch("app.agents.extract_elements_agent.property_value")
@patch("app.agents.extract_elements_agent.entity_storey")
def test_extract_elements_with_mock_wall(mock_storey, mock_prop, mock_state):
    mock_wall = MagicMock()
    mock_wall.is_a.return_value = "IfcWall"
    mock_wall.GlobalId = "123"
    mock_wall.Name = "TestWall"
    
    mock_state["model"].by_type.return_value = [mock_wall]
    mock_storey.return_value = "Level 1"
    mock_prop.return_value = 3000.0
    
    new_state = extract_elements_agent(mock_state)
    
    assert len(new_state["data"]["walls"]) == 1
    assert new_state["data"]["walls"][0]["name"] == "TestWall"
    assert new_state["data"]["walls"][0]["height_m"] == 3000.0

@patch("app.agents.extract_elements_agent.property_value")
def test_extract_elements_various_types(mock_prop, mock_state):
    # Mocking Slab, Door, Window, Stair
    slab = MagicMock(); slab.is_a.return_value = "IfcSlab"; slab.GlobalId = "s1"
    door = MagicMock(); door.is_a.return_value = "IfcDoor"; door.GlobalId = "d1"
    win = MagicMock(); win.is_a.return_value = "IfcWindow"; win.GlobalId = "w1"
    stair = MagicMock(); stair.is_a.return_value = "IfcStair"; stair.GlobalId = "st1"
    
    mock_state["model"].by_type.return_value = [slab, door, win, stair]
    mock_prop.return_value = 1.0 # default scale 1.0
    
    new_state = extract_elements_agent(mock_state)
    
    assert len(new_state["data"]["slabs"]) == 1
    assert len(new_state["data"]["openings"]["doors"]) == 1
    assert len(new_state["data"]["openings"]["windows"]) == 1
    assert len(new_state["data"]["stairs_ramps_balustrades"]) == 1

# 3. Test LLM Gap Analysis Agent (Skip if no key)
@patch("app.agents.llm_gap_analysis_agent.get_llm")
def test_llm_gap_analysis_agent_no_key(mock_get_llm, mock_state):
    mock_get_llm.return_value = None # No API Key
    new_state = llm_gap_analysis_agent(mock_state)
    assert "gemini_notes" not in new_state

# 4. Test LLM Gap Analysis Agent (Successful AI call)
@patch("app.agents.llm_gap_analysis_agent.get_llm")
def test_llm_gap_analysis_agent_success(mock_get_llm, mock_state):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value.content = "1. Add materials\n2. Fix fire ratings\n3. Check heights"
    mock_get_llm.return_value = mock_llm
    
    new_state = llm_gap_analysis_agent(mock_state)
    assert "gemini_notes" in new_state
    assert "Add materials" in new_state["gemini_notes"]

# 5. Test Schema Alignment Agent
def test_schema_alignment_agent(mock_state):
    mock_state["data"]["walls"] = [{"name": "Wall1"}]
    mock_state["gemini_notes"] = "AI Summary"
    
    final_output = schema_alignment_agent(mock_state)
    
    assert "result" in final_output
    assert final_output["result"]["extraction_metadata"]["llm_gap_analysis"] == "AI Summary"
    assert len(final_output["result"]["data"]["walls"]) == 1
