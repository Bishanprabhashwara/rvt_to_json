from __future__ import annotations

import os
from app.agents.shared import C_BLUE, C_DIM, C_RESET
from app.agents.state import ExtractState

def schema_alignment_agent(state: ExtractState) -> ExtractState:
    print(f"\n{C_BLUE}[Schema Alignment] Assembling final JSON output...{C_RESET}")
    
    file_path = state.get("ifc_path", "model.ifc")
    file_name = os.path.basename(file_path)
    # Get file size safely
    try:
        size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)
    except Exception:
        size_mb = 0.0

    meta = state.get("extraction_metadata", {})
    
    # --- Quality Audit Section ---
    score = state.get("audit_score", 0.0)
    report = state.get("gemini_notes", "Audit not performed.")
    
    audit_report = {
        "completeness_score": f"{score}%",
        "detailed_report": report
    }

    result = {
        "data": state.get("data", {}),
        "status": "success",
        "file_name": file_name,
        "file_size_mb": size_mb,
        "bim_quality_audit": audit_report,
        "extraction_metadata": meta
    }

    n_walls = len(result["data"].get("walls", []))
    n_slabs = len(result["data"].get("slabs", []))
    n_doors = len(result["data"].get("openings", {}).get("doors", []))
    
    print(f"   {C_DIM}`-- Schema ready: {n_walls} walls, {n_slabs} slabs, {n_doors} doors{C_RESET}")

    return {**state, "result": result}
