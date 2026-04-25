import json
from app.io.output_writer import write_json

def test_write_json(tmp_path):
    out_file = tmp_path / "test.json"
    data = {"test": "data"}
    
    write_json(str(out_file), data)
    
    assert out_file.exists()
    with open(out_file, "r") as f:
        saved = json.load(f)
        assert saved == data
