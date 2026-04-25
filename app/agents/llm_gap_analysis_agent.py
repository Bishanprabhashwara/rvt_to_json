import time
from app.agents.shared import agent_banner, agent_step, agent_step_done, get_llm, C_YELLOW, C_DIM, C_RESET
from app.agents.state import ExtractState

def llm_gap_analysis_agent(state: ExtractState) -> ExtractState:
    agent_banner(3, 4, "LLM Gap Analysis")
    t0 = time.time()
    agent_step("Analyzing data completeness")
    
    llm = get_llm()
    if not llm:
        agent_step_done(t0)
        print(f"   {C_DIM}`-- [LLM] Skipping: GEMINI_API_KEY not set.{C_RESET}")
        return state

    data = state.get("data", {})
    
    n_walls = len(data.get("walls", []))
    n_slabs = len(data.get("slabs", []))
    n_doors = len(data.get("openings", {}).get("doors", []))
    
    missing_materials = sum(1 for w in data.get("walls", []) if not w.get("material"))
    missing_fire_rating = sum(1 for w in data.get("walls", []) if not w.get("fire_rating"))
    
    prompt = f"""
    You are an expert BIM data analyst. Analyze this extraction summary and provide 3 concrete suggestions for gap-filling or geometry inferences.
    
    Summary:
    Walls: {n_walls} (Missing materials: {missing_materials}, Missing fire rating: {missing_fire_rating})
    Slabs: {n_slabs}
    Doors: {n_doors}
    
    Keep your answer to exactly 3 bullet points. Do not include markdown formatting like bolding.
    """

    try:
        review = llm.invoke(prompt)
        note = getattr(review, "content", str(review)).strip()
        
        # Format the response clearly
        agent_step_done(t0)
        print(f"   {C_DIM}`-- [LLM Analysis]:{C_RESET}")
        for line in note.split('\n'):
            if line.strip():
                print(f"       {C_YELLOW}{line.strip()}{C_RESET}")
        
        state["gemini_notes"] = note
        
    except Exception as exc:
        agent_step_done(t0)
        print(f"   {C_DIM}`-- [LLM] Failed: {exc}{C_RESET}")
        errors = list(state.get("errors", []))
        errors.append(f"LLM Gap Analysis failed: {exc}")
        state["errors"] = errors
        
    return state
