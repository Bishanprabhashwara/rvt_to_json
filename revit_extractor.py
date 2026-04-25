from __future__ import annotations
import argparse
from typing import Any, Dict
from pathlib import Path
from langgraph.graph import END, StateGraph
import app.utils.path_utils as path_utils
from app.adapters.aps_adapter import APSAdapter
from app.agents.extract_elements_agent import extract_elements_agent as extract_elements_agent_node
from app.agents.llm_gap_analysis_agent import llm_gap_analysis_agent as llm_gap_analysis_agent_node
from app.agents.load_model_agent import load_model_agent as load_model_agent_node
from app.agents.schema_alignment_agent import schema_alignment_agent as schema_alignment_agent_node
from app.agents.state import ExtractState
from app.config.settings import Settings
from app.io.output_writer import ensure_output_dir, write_json

def build_graph() -> Any:
    graph = StateGraph(ExtractState)

    graph.add_node("load_model", load_model_agent_node)
    graph.add_node("extract_elements", extract_elements_agent_node)
    graph.add_node("gap_analysis", llm_gap_analysis_agent_node)
    graph.add_node("schema_alignment", schema_alignment_agent_node)

    graph.set_entry_point("load_model")
    graph.add_edge("load_model", "extract_elements")
    graph.add_edge("extract_elements", "gap_analysis")
    graph.add_edge("gap_analysis", "schema_alignment")
    graph.add_edge("schema_alignment", END)

    return graph.compile()


def run(ifc_path: str, output_path: str) -> Dict[str, Any]:
    from pathlib import Path as _Path
    model_name = _Path(ifc_path).stem
    width = 65
    print("\n" + "+" + "=" * width + "+")
    print("|" + "  [RVT->JSON]  LLM Agent Pipeline".center(width) + "|")
    print("|" + f"  Model: {model_name}".center(width) + "|")
    print("+" + "=" * width + "+")

    app = build_graph()
    final_state = app.invoke(
        {
            "ifc_path": ifc_path,
            "output_path": output_path,
            "errors": [],
        }
    )

    result = final_state.get("result", {})
    if final_state.get("errors"):
        result["errors"] = final_state["errors"]

    write_json(output_path, result)
    return result


def _prompt_rvt_path() -> str:
    while True:
        raw = input("Enter RVT file path: ").strip().strip('"').strip("'")
        if raw:
            return raw
        print("RVT path is required.")


def _mask_client_id(client_id: str | None) -> str:
    if not client_id:
        return "<missing>"
    if len(client_id) <= 8:
        return "*" * len(client_id)
    return f"{client_id[:4]}...{client_id[-4:]}"


def _convert_rvt_to_ifc(rvt_path: str, ifc_path: str, client_id: str, client_secret: str) -> None:
    APSAdapter(client_id=client_id, client_secret=client_secret).convert_rvt_to_ifc(rvt_path, ifc_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="LangGraph agents for RVT/IFC extraction with Gemini review")
    parser.add_argument("--rvt", default=None, help="Path to RVT file. If omitted, you will be prompted.")
    parser.add_argument("--ifc", default=None, help="Optional existing IFC path. If given, RVT conversion is skipped.")
    parser.add_argument("--output-dir", default="output", help="Output directory for generated IFC/JSON files.")
    args = parser.parse_args()

    settings = Settings.load(output_dir=args.output_dir)
    output_dir = settings.output_dir
    ensure_output_dir(output_dir)

    if args.ifc:
        ifc_path = str(Path(args.ifc).resolve())
        base_name = Path(ifc_path).stem
    else:
        raw_rvt = args.rvt or _prompt_rvt_path()
        rvt_path = str(path_utils.resolve_input_path(raw_rvt))
        base_name = Path(rvt_path).stem
        ifc_path = str((output_dir / f"{base_name}.ifc").resolve())

        client_id = settings.aps_client_id
        client_secret = settings.aps_client_secret
        if not client_id or not client_secret:
            raise SystemExit(
                "ERROR: APS credentials missing. Set APS_CLIENT_ID and APS_CLIENT_SECRET in environment or .env."
            )

        print(
            f"[Auth] Using APS credentials from {settings.aps_credential_source}; "
            f"client_id={_mask_client_id(client_id)}"
        )
        print("[APS] Converting RVT to IFC ...")
        _convert_rvt_to_ifc(rvt_path, ifc_path, client_id, client_secret)

    output_path = str((output_dir / f"{base_name}.json").resolve())
    result = run(ifc_path, output_path)

    data = result.get("data", {})
    n_walls = len(data.get("walls", []))
    n_slabs = len(data.get("slabs", []))
    n_doors = len(data.get("openings", {}).get("doors", []))
    n_windows = len(data.get("openings", {}).get("windows", []))
    errors  = result.get("errors", [])

    print("\n" + "=" * 67)
    print(f"  [DONE]  Pipeline complete!")
    print(f"  [OUT ]  Output : {output_path}")
    print(f"  [INFO]  Elements: {n_walls} walls, {n_slabs} slabs, {n_doors} doors, {n_windows} windows   |   Unit: meters")
    if errors:
        print(f"  [WARN]  Errors  : {len(errors)} (see JSON output for details)")
    print("=" * 67 + "\n")


if __name__ == "__main__":
    main()
