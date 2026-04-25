from __future__ import annotations

import os
import time
from typing import Any, List, Optional

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except Exception:
    ChatGoogleGenerativeAI = None

# ANSI Colors
C_RESET = "\033[0m"
C_GREEN = "\033[92m"
C_BLUE = "\033[94m"
C_CYAN = "\033[96m"
C_YELLOW = "\033[93m"
C_MAGENTA = "\033[95m"
C_DIM = "\033[2m"

LENGTH_PREFIX_SCALE = {
    "EXA": 1e18,
    "PETA": 1e15,
    "TERA": 1e12,
    "GIGA": 1e9,
    "MEGA": 1e6,
    "KILO": 1e3,
    "HECTO": 1e2,
    "DECA": 1e1,
    "DECI": 1e-1,
    "CENTI": 1e-2,
    "MILLI": 1e-3,
    "MICRO": 1e-6,
    "NANO": 1e-9,
}


def get_llm():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or ChatGoogleGenerativeAI is None:
        return None
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0,
    )


def agent_banner(step: int, total: int, name: str, icon: str = "[Agent]"):
    print(f"\n{C_CYAN}[Agent {step}/{total}] {name}{C_RESET}")


def agent_step(msg: str):
    print(f"   {C_DIM}|-- {msg}...{C_RESET}", end="", flush=True)


def agent_step_done(start_time: float):
    dt = time.time() - start_time
    print(f"\r   {C_DIM}|--{C_RESET} {C_GREEN}[OK] Done ({dt:.1f}s){C_RESET}                        ")


def agent_info(msg: str):
    print(f"   {C_DIM}|-- {msg}{C_RESET}")


def _parse_retry_delay(exc: Exception) -> float:
    """Extract retryDelay seconds from a 429 RESOURCE_EXHAUSTED error, default 60s."""
    try:
        msg = str(exc)
        import re as _re
        # Match: 'retryDelay': '44s'  or  "retryDelay": "44.5s"
        m = _re.search(r"retryDelay['\"]?\s*:\s*['\"]([0-9.]+)s", msg)
        if m:
            return min(float(m.group(1)), 90.0)  # cap at 90s
    except Exception:
        pass
    return 60.0


def llm_call(llm, prompt: str, max_retries: int = 2) -> str:
    for attempt in range(1, max_retries + 2):
        start = time.time()
        if attempt == 1:
            print(f"   {C_DIM}`-- [LLM] Thinking...{C_RESET}", end="", flush=True)
        else:
            print(f"   {C_DIM}`-- [LLM] Retry {attempt-1}/{max_retries}...{C_RESET}", end="", flush=True)
        try:
            response = llm.invoke(prompt)
            content = getattr(response, "content", str(response)).strip()
            dt = time.time() - start
            content = content.replace("\n", " ")
            if len(content) > 80:
                content = content[:77] + "..."
            print(f"\r   {C_DIM}`-- [LLM] ({dt:.1f}s):{C_RESET} {C_MAGENTA}\"{content}\"{C_RESET}            ")
            return content
        except Exception as exc:
            err_str = str(exc)
            is_quota = "RESOURCE_EXHAUSTED" in err_str or "429" in err_str
            is_daily = "limit: 0" in err_str or "PerDay" in err_str
            if is_quota and not is_daily and attempt <= max_retries:
                delay = _parse_retry_delay(exc)
                print(f"\r   {C_DIM}`-- [LLM] Rate-limited. Waiting {delay:.0f}s before retry...{C_RESET}            ")
                time.sleep(delay)
                continue
            if is_daily:
                print(f"\r   {C_DIM}`-- [LLM]:{C_RESET} {C_YELLOW}Daily quota exhausted -- skipping LLM call{C_RESET}            ")
            else:
                # Truncate error msg for readability
                short_err = err_str[:120].replace("\n", " ") + ("..." if len(err_str) > 120 else "")
                print(f"\r   {C_DIM}`-- [LLM]:{C_RESET} {C_YELLOW}Failed: {short_err}{C_RESET}            ")
            return f"Error: {err_str[:80]}"


def _resolve_boolean(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "yes", "1")
    return bool(value)


def _resolve_boolean(val: Any) -> bool | None:
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    s = str(val).lower()
    if s in ["true", "1", "yes", "t"]:
        return True
    if s in ["false", "0", "no", "f", "none"]:
        return False
    return None


def safe_float(value: Any) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except Exception:
        return None


def unwrap_ifc_value(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "wrappedValue"):
        return value.wrappedValue
    return value


def property_value(entity: Any, names: List[str]) -> Any:
    wanted = {n.lower() for n in names}
    for rel in getattr(entity, "IsDefinedBy", []) or []:
        if not rel.is_a("IfcRelDefinesByProperties"):
            continue
        pset = getattr(rel, "RelatingPropertyDefinition", None)
        if not pset or not pset.is_a("IfcPropertySet"):
            continue
        for prop in getattr(pset, "HasProperties", []) or []:
            if not prop.is_a("IfcPropertySingleValue"):
                continue
            name = (getattr(prop, "Name", "") or "").strip().lower()
            if name in wanted:
                return unwrap_ifc_value(getattr(prop, "NominalValue", None))
    return None


def entity_storey(entity: Any) -> Optional[str]:
    for rel in getattr(entity, "ContainedInStructure", []) or []:
        structure = getattr(rel, "RelatingStructure", None)
        if structure and structure.is_a("IfcBuildingStorey"):
            return getattr(structure, "Name", None)
    return None


def entity_material(entity: Any) -> Optional[str]:
    mats: List[str] = []
    for assoc in getattr(entity, "HasAssociations", []) or []:
        if not assoc.is_a("IfcRelAssociatesMaterial"):
            continue
        mat = getattr(assoc, "RelatingMaterial", None)
        if not mat:
            continue
        if mat.is_a("IfcMaterial"):
            name = getattr(mat, "Name", None)
            if name:
                mats.append(name)
        elif mat.is_a("IfcMaterialLayerSetUsage"):
            layer_set = getattr(mat, "ForLayerSet", None)
            for layer in getattr(layer_set, "MaterialLayers", []) or []:
                m = getattr(layer, "Material", None)
                name = getattr(m, "Name", None) if m else None
                if name:
                    mats.append(name)
        elif mat.is_a("IfcMaterialLayerSet"):
            for layer in getattr(mat, "MaterialLayers", []) or []:
                m = getattr(layer, "Material", None)
                name = getattr(m, "Name", None) if m else None
                if name:
                    mats.append(name)
    if not mats:
        return None
    return " + ".join(dict.fromkeys(mats))


def length_scale_to_m(model: Any) -> float:
    scale = 1.0
    for ua in model.by_type("IfcUnitAssignment"):
        for unit in getattr(ua, "Units", []) or []:
            if not hasattr(unit, "UnitType"):
                continue
            if str(getattr(unit, "UnitType", "")) != "LENGTHUNIT":
                continue

            if unit.is_a("IfcSIUnit"):
                if str(getattr(unit, "Name", "")) == "METRE":
                    prefix = str(getattr(unit, "Prefix", ""))
                    return LENGTH_PREFIX_SCALE.get(prefix, 1.0)
                return 1.0

            if unit.is_a("IfcConversionBasedUnit"):
                name = (str(getattr(unit, "Name", "")) or "").upper()
                if "FOOT" in name:
                    return 0.3048
                if "INCH" in name:
                    return 0.0254

                cf = getattr(unit, "ConversionFactor", None)
                if cf:
                    vc = unwrap_ifc_value(getattr(cf, "ValueComponent", None))
                    if vc is not None:
                        base = safe_float(vc)
                        if base is not None:
                            scale = base
    return scale


def convert_to_m(value: Any, scale: float) -> Any:
    if isinstance(value, (int, float)):
        return float(value) * scale
    return value

def entity_material_layers(entity: Any) -> List[Dict[str, Any]]:
    # Extracts an array of {"name": str, "thickness": float}
    layers = []
    for assoc in getattr(entity, "HasAssociations", []) or []:
        if not assoc.is_a("IfcRelAssociatesMaterial"):
            continue
        mat = getattr(assoc, "RelatingMaterial", None)
        if not mat:
            continue
        
        target_layers = []
        if mat.is_a("IfcMaterialLayerSetUsage"):
            layer_set = getattr(mat, "ForLayerSet", None)
            target_layers = getattr(layer_set, "MaterialLayers", []) or []
        elif mat.is_a("IfcMaterialLayerSet"):
            target_layers = getattr(mat, "MaterialLayers", []) or []
            
        for layer in target_layers:
            m = getattr(layer, "Material", None)
            name = getattr(m, "Name", None) if m else "Default"
            thickness = safe_float(unwrap_ifc_value(getattr(layer, "LayerThickness", 0.0))) or 0.0
            
            layers.append({"name": str(name), "thickness": float(thickness)})

    if not layers:
        flat_mat = entity_material(entity)
        if flat_mat:
            layers.append({"name": flat_mat, "thickness": 0.0})
    return layers

def get_hosted_openings(wall: Any) -> List[Any]:
    # Returns the filler (Door/Window) entities hosted in a wall
    fillers = []
    for rel in getattr(wall, "HasOpenings", []) or []:
        opening = getattr(rel, "RelatedOpeningElement", None)
        if opening:
            for filler_rel in getattr(opening, "HasFillings", []) or []:
                filling = getattr(filler_rel, "RelatedBuildingElement", None)
                if filling:
                    fillers.append(filling)
    return fillers

def get_host_wall(door_or_window: Any) -> Optional[Any]:
    for rel in getattr(door_or_window, "FillsVoids", []) or []:
        opening = getattr(rel, "RelatingOpeningElement", None)
        if opening:
            for void_rel in getattr(opening, "VoidsElements", []) or []:
                wall = getattr(void_rel, "RelatingBuildingElement", None)
                if wall:
                    return wall
    return None

def extract_project_metadata(model: Any) -> Dict[str, Any]:
    meta = {
        "scale": None,
        "units": {"count": 0, "units": []},
        "north_point": {"x": 0.0, "y": 1.0, "description": "True North at 0.0", "compass_bearing_degrees": 0.0, "angle_from_x_axis_degrees": 90.0},
        "project_name": "Unknown",
        "drawing_name": None,
        "drawing_type": None,
        "project_description": None,
        "drawing_number": None
    }
    
    # Project Name
    for proj in model.by_type("IfcProject"):
        meta["project_name"] = str(getattr(proj, "Name", "Unknown") or "Unknown")
        meta["project_description"] = str(getattr(proj, "Description", "")) or None
    
    # Units
    for ua in model.by_type("IfcUnitAssignment"):
        units = getattr(ua, "Units", []) or []
        for unit in units:
            unit_type = str(getattr(unit, "UnitType", "")) if hasattr(unit, "UnitType") else None
            name = str(getattr(unit, "Name", "")) if hasattr(unit, "Name") else None
            prefix = str(getattr(unit, "Prefix", "")) if hasattr(unit, "Prefix") else None
            meta["units"]["units"].append({
                "name": name,
                "prefix": prefix,
                "unit_type": unit_type,
                "conversion_factor": None
            })
        meta["units"]["count"] = len(meta["units"]["units"])
        
    return meta

def extract_site_dimensions(model: Any, scale_to_m: float) -> Dict[str, Any]:
    dims = {
        "fence": [],
        "driveway": [],
        "ffl_levels": [],
        "site_area_sqm": None,
        "rear_setback_m": None,
        "front_setback_m": None,
        "north_reference": None,
        "side_setbacks_m": {"left": None, "right": None},
        "boundary_segments": [],
        "private_open_space": {"spaces": [], "total_area": None},
        "building_footprint_area_sqm": None
    }
    
    # FFL Levels
    storeys = model.by_type("IfcBuildingStorey")
    for st in sorted(storeys, key=lambda x: safe_float(getattr(x, "Elevation", 0.0)) or 0.0):
        name = str(getattr(st, "Name", "")) or "UNKNOWN"
        elev = safe_float(getattr(st, "Elevation", 0.0)) or 0.0
        dims["ffl_levels"].append({
            "name": name,
            "long_name": getattr(st, "LongName", None) or name,
            "elevation_m": elev * scale_to_m
        })
        
    return dims
