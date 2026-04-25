import os
import time
import requests
import urllib.parse
import base64
import re
from pathlib import Path

# Constants used for polling and uploading
POLL_INTERVAL_SEC = 15
MAX_POLL_ATTEMPTS = 60
UPLOAD_PART_SIZE  = 32 * 1024 * 1024
MAX_UPLOAD_RETRY  = 3
SIGNED_URL_MINUTES_EXPIRY = 60
S3_UPLOAD_TIMEOUT_SEC = 90
RETRY_INITIAL_BACKOFF_SEC = 0.5
RETRY_MAX_BACKOFF_SEC = 3

def _get_config():
    return {
        "AUTH_URL": os.environ.get("APS_AUTH_URL"),
        "OSS_BASE": os.environ.get("APS_OSS_BASE"),
        "MD_BASE":  os.environ.get("APS_MD_BASE"),
        "BUCKET":   os.environ.get("BUCKET_KEY")
    }

def make_safe_object_key(file_path: str) -> str:
    p = Path(file_path)
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", p.stem).strip("._") or "model"
    return f"{stem}{p.suffix}"


def get_access_token(client_id: str, client_secret: str) -> str:
    cfg = _get_config()
    print("[Auth] Requesting APS access token …")
    resp = requests.post(
        cfg["AUTH_URL"],
        data={
            "grant_type":    "client_credentials",
            "scope":         "data:read data:write data:create bucket:read bucket:create",
        },
        auth=(client_id, client_secret),
    )
    if resp.status_code >= 400:
        detail = (resp.text or "").strip()
        hint = "Check APS_CLIENT_ID / APS_CLIENT_SECRET values."
        raise RuntimeError(f"APS token request failed ({resp.status_code}).\nResponse: {detail}\nHint: {hint}")
    
    token = resp.json()["access_token"]
    print("    Token obtained.")
    return token


def ensure_bucket(token: str) -> None:
    cfg = _get_config()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    bucket_key = cfg["BUCKET"]
    
    r = requests.get(f"{cfg['OSS_BASE']}/buckets/{bucket_key}/details", headers=headers)
    if r.status_code == 200:
        print(f"[OSS] Bucket '{bucket_key}' already exists.")
        return
        
    print(f"[OSS] Creating bucket '{bucket_key}' …")
    r = requests.post(
        f"{cfg['OSS_BASE']}/buckets",
        headers=headers,
        json={"bucketKey": bucket_key, "policyKey": "transient"},
    )
    r.raise_for_status()
    print("    Bucket created.")


def upload_file(token: str, rvt_path: str) -> str:
    cfg = _get_config()
    bucket_key = cfg["BUCKET"]
    object_key = make_safe_object_key(rvt_path)
    file_size  = os.path.getsize(rvt_path)
    headers    = {"Authorization": f"Bearer {token}"}
    part_count = max(1, (file_size + UPLOAD_PART_SIZE - 1) // UPLOAD_PART_SIZE)

    print(f"[OSS] Uploading '{object_key}' ({file_size / 1e6:.1f} MB) in {part_count} part(s) …")

    encoded_key = urllib.parse.quote(object_key, safe="")
    upload_key = None

    with open(rvt_path, "rb") as f:
        for part_idx in range(1, part_count + 1):
            part_bytes = f.read(UPLOAD_PART_SIZE)
            
            for attempt in range(1, MAX_UPLOAD_RETRY + 1):
                try:
                    sign_params = {"parts": 1, "firstPart": part_idx, "minutesExpiration": SIGNED_URL_MINUTES_EXPIRY}
                    if upload_key: sign_params["uploadKey"] = upload_key

                    sign_resp = requests.get(
                        f"{cfg['OSS_BASE']}/buckets/{bucket_key}/objects/{encoded_key}/signeds3upload",
                        headers=headers, params=sign_params
                    )
                    sign_resp.raise_for_status()
                    signed = sign_resp.json()
                    
                    upload_key = upload_key or signed.get("uploadKey")
                    url = signed.get("urls", [None])[0]

                    requests.put(url, data=part_bytes, timeout=S3_UPLOAD_TIMEOUT_SEC).raise_for_status()
                    print(f"    Uploaded part {part_idx}/{part_count}")
                    break
                except Exception as exc:
                    print(f"    Attempt {attempt} failed: {exc}")
                    time.sleep(RETRY_INITIAL_BACKOFF_SEC * attempt)

    # Complete upload
    requests.post(
        f"{cfg['OSS_BASE']}/buckets/{bucket_key}/objects/{encoded_key}/signeds3upload",
        headers={**headers, "Content-Type": "application/json"},
        json={"uploadKey": upload_key}
    ).raise_for_status()

    object_id = f"urn:adsk.objects:os.object:{bucket_key}/{object_key}"
    return base64.urlsafe_b64encode(object_id.encode()).decode().rstrip("=")


def start_translation(token: str, urn: str) -> None:
    cfg = _get_config()
    print("[MD] Starting RVT -> IFC translation ...")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {"input": {"urn": urn}, "output": {"formats": [{"type": "ifc"}]}}
    r = requests.post(f"{cfg['MD_BASE']}/designdata/job", headers=headers, json=body)
    r.raise_for_status()


def poll_translation(token: str, urn: str) -> str:
    cfg = _get_config()
    headers = {"Authorization": f"Bearer {token}"}
    print("[MD] Waiting for translation to complete …")
    
    for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        r = requests.get(f"{cfg['MD_BASE']}/designdata/{urn}/manifest", headers=headers)
        r.raise_for_status()
        manifest = r.json()
        status = manifest.get("status", "")
        
        print(f"    Attempt {attempt}/{MAX_POLL_ATTEMPTS} — status: {status}    ", end="\r")
        if status == "success": return urn
        if status == "failed": raise RuntimeError("Translation failed.")
        time.sleep(POLL_INTERVAL_SEC)
    raise RuntimeError("Translation timed out.")


def download_ifc(token: str, urn: str, output_ifc_path: str) -> None:
    cfg = _get_config()
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{cfg['MD_BASE']}/designdata/{urn}/manifest", headers=headers)
    r.raise_for_status()
    manifest = r.json()

    ifc_urn = None
    for derivative in manifest.get("derivatives", []):
        if derivative.get("outputType") == "ifc":
            for child in derivative.get("children", []):
                if child.get("role") == "ifc":
                    ifc_urn = child["urn"]
                    break
    
    encoded_ifc_urn = urllib.parse.quote(ifc_urn, safe="")
    r = requests.get(f"{cfg['MD_BASE']}/designdata/{urn}/manifest/{encoded_ifc_urn}", headers=headers, stream=True)
    r.raise_for_status()

    with open(output_ifc_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"    IFC saved to: {output_ifc_path}")
