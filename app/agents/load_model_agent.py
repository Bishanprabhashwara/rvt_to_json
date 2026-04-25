from __future__ import annotations

import time

import ifcopenshell

from app.agents.shared import agent_banner, agent_info, agent_step, agent_step_done, length_scale_to_m
from app.agents.state import ExtractState


def load_model_agent(state: ExtractState) -> ExtractState:
    agent_banner(1, 6, "Load Model Agent")
    t0 = time.time()
    agent_step("Loading IFC model")

    model = ifcopenshell.open(state["ifc_path"])
    agent_step_done(t0)

    entities_count = len(model.by_type("IfcProduct"))
    agent_info(f"Entities found: {entities_count} total")
    return {
        **state,
        "model": model,
        "unit_scale_to_m": length_scale_to_m(model),
        "errors": state.get("errors", []),
    }
