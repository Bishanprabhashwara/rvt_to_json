import difflib
import re
from pathlib import Path

def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip().lower()

def resolve_input_path(raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser().resolve()
    if candidate.exists():
        return candidate

    parent = candidate.parent if str(candidate.parent) else Path.cwd()
    if not parent.exists():
        raise FileNotFoundError(f"Input folder not found: {parent}")

    target_name = candidate.name
    norm_target = _normalize_name(target_name)

    exact_norm = [p for p in parent.iterdir() if p.is_file() and _normalize_name(p.name) == norm_target]
    if len(exact_norm) == 1:
        print(f"[Input] Using matched file: {exact_norm[0]}")
        return exact_norm[0].resolve()

    file_names = [p.name for p in parent.iterdir() if p.is_file()]
    close = difflib.get_close_matches(target_name, file_names, n=3, cutoff=0.6)

    msg = [f"ERROR: RVT file not found: {candidate}"]
    if close:
        msg.append("Did you mean one of these?")
        msg.extend([f"  - {name}" for name in close])
    raise FileNotFoundError("\n".join(msg))
