from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

def load_dotenv_file(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

@dataclass
class Settings:
    env_file: Path
    env_loaded_from: Path | None
    output_dir: Path
    aps_client_id: str | None
    aps_client_secret: str | None
    aps_credential_source: str
    gemini_api_key: str | None

    @classmethod
    def load(cls, env_file: str | None = None, output_dir: str = "output") -> "Settings":
        candidates = []
        if env_file:
            env_path = Path(env_file)
            if env_path.is_absolute():
                candidates.append(env_path)
            else:
                candidates.append((Path.cwd() / env_path).resolve())
                candidates.append((Path(__file__).resolve().parents[2] / env_path).resolve())
        else:
            # Automatic discovery order: workspace root .env, current dir .env, app/.env
            root = Path(__file__).resolve().parents[2]
            candidates.append((root / ".env").resolve())
            candidates.append((Path.cwd() / ".env").resolve())
            candidates.append((root / "app" / ".env").resolve())

        env_loaded_from = None
        for candidate in candidates:
            if candidate.exists():
                load_dotenv_file(candidate)
                env_loaded_from = candidate
                break

        file_client_id = _read_value_from_env_file(env_loaded_from, "APS_CLIENT_ID") if env_loaded_from else None
        file_client_secret = _read_value_from_env_file(env_loaded_from, "APS_CLIENT_SECRET") if env_loaded_from else None

        aps_client_id = file_client_id or os.environ.get("APS_CLIENT_ID")
        aps_client_secret = file_client_secret or os.environ.get("APS_CLIENT_SECRET")

        if file_client_id and file_client_secret:
            aps_credential_source = f".env ({env_loaded_from})"
        else:
            aps_credential_source = "environment"

        return cls(
            env_file=(Path(env_file).resolve() if env_file else (env_loaded_from or Path(".env").resolve())),
            env_loaded_from=env_loaded_from,
            output_dir=Path(output_dir).resolve(),
            aps_client_id=aps_client_id,
            aps_client_secret=aps_client_secret,
            aps_credential_source=aps_credential_source,
            gemini_api_key=_read_value_from_env_file(env_loaded_from, "GEMINI_API_KEY") if env_loaded_from else os.environ.get("GEMINI_API_KEY"),
        )


def _read_value_from_env_file(env_path: Path, key: str) -> str | None:
    if not env_path.exists():
        return None

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == key:
            return v.strip().strip('"').strip("'")
    return None
