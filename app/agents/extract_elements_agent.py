import time

from app.agents.shared import (
    agent_banner, agent_info, agent_step, agent_step_done, 
    entity_material, entity_storey, property_value, safe_float,
    entity_material_layers, get_hosted_openings, get_host_wall,
    extract_project_metadata, extract_site_dimensions, _resolve_boolean
)
from app.agents.state import ExtractState

def extract_elements_agent(state: ExtractState) -> ExtractState:
    agent_banner(2, 3, "Extract Elements & Topologies")
    t0 = time.time()
    agent_step("Building hierarchical data structure (SI Meters)")

    model = state["model"]
    scale_m = state.get("unit_scale_to_m", 1.0)
    to_sqm = scale_m * scale_m

    data = {
        "slabs": [],
        "walls": [],
        "proxies": [],
        "openings": {
            "doors": [],
            "windows": []
        },
        "coverings": [],
        "wet_areas": [],
        "furnishing": [],
        "project_metadata": extract_project_metadata(model),
        "distribution_elements": [],
        "rooms_internal_layout": [],
        "building_site_dimensions": extract_site_dimensions(model, scale_m),
        "stairs_ramps_balustrades": []
    }

    entity_counts = {}

    for entity in model.by_type("IfcProduct"):
        ifc_type = entity.is_a()
        entity_counts[ifc_type] = entity_counts.get(ifc_type, 0) + 1
        
        gid = getattr(entity, "GlobalId", None)
        name = getattr(entity, "Name", None) or f"{ifc_type}:{gid}"
        storey = entity_storey(entity)
        
        flat_mat = entity_material(entity)
        
        # Dimensions in SI Meters
        height_raw = safe_float(property_value(entity, ["Height", "Unconnected Height", "OverallHeight"]) or getattr(entity, "OverallHeight", None))
        width_raw = safe_float(property_value(entity, ["Width", "OverallWidth", "Thickness"]) or getattr(entity, "OverallWidth", None))
        length_raw = safe_float(property_value(entity, ["Length", "OverallLength"] ) or getattr(entity, "OverallLength", None))
        area_raw = safe_float(property_value(entity, ["Area", "NetArea"]))
        
        height_m = height_raw * scale_m if height_raw is not None else None
        width_m = width_raw * scale_m if width_raw is not None else None
        length_m = length_raw * scale_m if length_raw is not None else None
        thickness_m = width_m  # Revit mapped width is thickness for walls
        area_sqm = area_raw * to_sqm if area_raw is not None else None
        
        fire_rating = property_value(entity, ["FireRating", "Fire Rating"])
        is_external = _resolve_boolean(property_value(entity, ["IsExternal"]))
        load_bearing = _resolve_boolean(property_value(entity, ["LoadBearing"]))
        object_type = getattr(entity, "ObjectType", None)
        predefined = str(getattr(entity, "PredefinedType", None)) if getattr(entity, "PredefinedType", None) is not None else None

        # Helper to process material layers into meters
        def process_layers(item):
            raw_layers = entity_material_layers(item)
            processed = []
            for lyr in raw_layers:
                processed.append({
                    "name": lyr["name"],
                    "thickness_m": lyr["thickness"] * scale_m  # raw value from shared scaled to m
                })
            return processed

        if ifc_type in ("IfcWall", "IfcWallStandardCase"):
            hosted = get_hosted_openings(entity)
            openings_list = []
            for h in hosted:
                openings_list.append({
                    "name": getattr(h, "Name", None) or "Unknown",
                    "type": h.is_a().replace("Ifc", ""),
                    "global_id": getattr(h, "GlobalId", None)
                })
            
            data["walls"].append({
                "name": name,
                "storey": storey,
                "area_sqm": area_sqm,
                "material": flat_mat,
                "global_id": gid,
                "height_m": height_m,
                "length_m": length_m,
                "fire_rating": fire_rating,
                "is_external": bool(is_external) if is_external is not None else False,
                "object_type": object_type,
                "load_bearing": bool(load_bearing) if load_bearing is not None else False,
                "thickness_m": thickness_m,
                "material_layers": process_layers(entity),
                "contains_openings": openings_list,
                "structural_function": property_value(entity, ["StructuralFunction", "Structural Function"])
            })

        elif ifc_type == "IfcSlab":
            data["slabs"].append({
                "name": name,
                "storey": storey,
                "area_sqm": area_sqm,
                "material": flat_mat,
                "global_id": gid,
                "fire_rating": fire_rating,
                "is_external": bool(is_external) if is_external is not None else False,
                "object_type": object_type,
                "load_bearing": load_bearing,
                "thickness_m": thickness_m,
                "predefined_type": predefined
            })

        elif ifc_type in ("IfcDoor", "IfcWindow"):
            host = get_host_wall(entity)
            host_dict = None
            if host:
                host_dict = {
                    "name": getattr(host, "Name", None),
                    "global_id": getattr(host, "GlobalId", None)
                }
            
            op_dict = {
                "name": name,
                "storey": storey,
                "material": flat_mat,
                "width_m": width_m,
                "global_id": gid,
                "height_m": height_m,
                "host_wall": host_dict,
                "fire_rating": fire_rating,
                "is_external": bool(is_external) if is_external is not None else False,
                "object_type": object_type,
                "orientation": property_value(entity, ["Orientation"]),
                "nominal_size": None,
                "thickness_m": thickness_m,
                "operation_type": property_value(entity, ["OperationType"]),
                "acoustic_rating": property_value(entity, ["AcousticRating"]),
                "connected_rooms": [],
                "leaf_dimensions": None,
                "egress_dimensions": None,
                "wallhole_dimensions": None
            }
            if ifc_type == "IfcDoor":
                data["openings"]["doors"].append(op_dict)
            else:
                op_dict["head_height_m"] = safe_float(property_value(entity, ["HeadHeight"])) # HeadHeight is often already scaled or needs scale_m
                sill_raw = safe_float(property_value(entity, ["SillHeight"]))
                op_dict["sill_height_m"] = sill_raw * scale_m if sill_raw is not None else 0.0
                op_dict["glazing_fraction"] = safe_float(property_value(entity, ["GlazingFraction"]))
                op_dict["thermal_transmittance"] = property_value(entity, ["ThermalTransmittance"])
                op_dict["area_sqm"] = area_sqm
                data["openings"]["windows"].append(op_dict)

        elif ifc_type in ("IfcStair", "IfcStairFlight", "IfcRailing"):
            data["stairs_ramps_balustrades"].append({
                "name": name,
                "type": predefined or ifc_type.replace("Ifc", ""),
                "storey": storey,
                "global_id": gid,
                "height_m": height_m,
                "material": flat_mat,
                "total_rise": None,
                "fire_rating": fire_rating,
                "riser_count": None,
                "riser_height": None,
                "tread_length": None,
                "handrail_present": None,
                "going": None
            })

    agent_step_done(t0)
    agent_info(f"Categorized {len(data['walls'])} walls, {len(data['slabs'])} slabs. Units: SI Meters.")

    return {
        **state,
        "data": data,
        "project_metadata": data["project_metadata"],
        "building_site_dimensions": data["building_site_dimensions"],
        "extraction_metadata": {
            "note": "All dimensions converted to SI Meters.",
            "has_zones": False,
            "has_spaces": False,
            "ifc_schema": model.schema,
            "entity_counts": entity_counts,
            "extraction_date": time.strftime("%Y-%m-%dT%H:%M:%S.000000"),
            "extractor_version": "3.1"
        }
    }
