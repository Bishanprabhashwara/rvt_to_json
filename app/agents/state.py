from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class ExtractState(TypedDict, total=False):
    ifc_path: str
    output_path: str
    model: Any
    unit_scale_to_m: float
    data: Dict[str, Any]
    project_metadata: Dict[str, Any]
    building_site_dimensions: Dict[str, Any]
    extraction_metadata: Dict[str, Any]
    result: Dict[str, Any]
    gemini_notes: Optional[str]
    errors: List[str]
