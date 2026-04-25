import time
from app.agents.shared import agent_banner, agent_step, agent_step_done, get_llm, C_YELLOW, C_DIM, C_RESET
from app.agents.state import ExtractState

def llm_gap_analysis_agent(state: ExtractState) -> ExtractState:
    agent_banner(3, 4, "BIM Quality Audit")
    t0 = time.time()
    agent_step("Analyzing model health & completeness")
    
    llm = get_llm()
    data = state.get("data", {})
    
    # --- 1. Heuristic Completeness Score ---
    walls = data.get("walls", [])
    slabs = data.get("slabs", [])
    total_elements = len(walls) + len(slabs)
    
    missing_mat = sum(1 for w in walls if not w.get("material"))
    missing_fire = sum(1 for w in walls if not w.get("fire_rating"))
    
    # Simple heuristic: 100% minus penalty for missing critical metadata
    base_score = 100.0
    if total_elements > 0:
        penalty = ((missing_mat + missing_fire) / (total_elements * 2)) * 100
        score = round(max(0.0, base_score - penalty), 1)
    else:
        score = 0.0

    state["audit_score"] = score
    
    if not llm:
        agent_step_done(t0)
        print(f"   {C_DIM}`-- Score: {score}% (Metadata Analysis Complete){C_RESET}")
        return state

    # --- 2. AI Audit Report ---
    prompt = f"""
    You are a Senior BIM Auditor and Risk Manager. Provide a formal audit of this BIM extraction.
    
    STATS:
    - Model Completeness Score: {score}%
    - Walls: {len(walls)} ({missing_mat} missing materials, {missing_fire} missing fire ratings)
    - Slabs: {len(slabs)}
    
    TASK:
    Provide a quality audit in 3 brief sections:
    1. SUMMARY: A 1-sentence assessment of model health.
    2. MISSING CRITICAL DATA: List specific metadata missing that will cause construction risk.
    3. BUSINESS IMPACT: How this data gap affects procurement or safety.
    
    Keep response clear and professional. No markdown bolding.
    """

    try:
        review = llm.invoke(prompt)
        report = getattr(review, "content", str(review)).strip()
        
        agent_step_done(t0)
        print(f"   {C_DIM}`-- [QA REPORT] Score: {score}%{C_RESET}")
        for line in report.split('\n'):
            if line.strip():
                print(f"       {C_YELLOW}{line.strip()}{C_RESET}")
        
        state["gemini_notes"] = report
        
    except Exception as exc:
        agent_step_done(t0)
        print(f"   {C_DIM}`-- [QA REPORT] Heuristic Score: {score}% (AI failed: {exc}){C_RESET}")
        state["gemini_notes"] = f"Heuristic Score: {score}%. AI Audit failed."
        
    return state
