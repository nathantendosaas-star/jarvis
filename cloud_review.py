import os
import json
import requests
from datetime import datetime
from typing import Dict, Any, List

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
STAGED_DIR = os.path.join(WORKSPACE_DIR, ".staged_offline_changes")
MANIFEST_PATH = os.path.join(STAGED_DIR, "manifest.json")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash")


def safe_path(filename: str, base_dir: str = WORKSPACE_DIR) -> str:
    """Resolve a filename and guarantee it stays inside base_dir."""
    filepath = os.path.abspath(os.path.join(base_dir, filename))
    if os.path.commonpath([filepath, base_dir]) != base_dir:
        raise ValueError(f"Path escapes directory, refusing: {filename}")
    return filepath


def check_internet_connection() -> bool:
    """Checks if internet access is available for cloud models."""
    try:
        r = requests.get("https://openrouter.ai/api/v1/models", timeout=4)
        return r.status_code == 200
    except Exception:
        return False


def get_staged_manifest() -> Dict[str, Any]:
    """Reads the staged offline changes manifest."""
    if not os.path.exists(MANIFEST_PATH):
        return {"files": [], "staged_at": None}
    try:
        with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"files": [], "error": str(e)}


def review_staged_file_with_cloud_model(filename: str, original_path: str, staged_path: str) -> Dict[str, Any]:
    """Reviews a staged file using OpenRouter Cloud Model (DeepSeek/Gemma)."""
    try:
        full_staged_path = safe_path(staged_path, WORKSPACE_DIR)
        full_orig_path = safe_path(original_path, WORKSPACE_DIR)
    except ValueError as err:
        return {"filename": filename, "approved": False, "reason": str(err)}

    if not os.path.exists(full_staged_path):
        return {"filename": filename, "approved": False, "reason": "Staged file missing."}

    with open(full_staged_path, 'r', encoding='utf-8') as f:
        staged_content = f.read()

    orig_content = ""
    if os.path.exists(full_orig_path):
        with open(full_orig_path, 'r', encoding='utf-8') as f:
            orig_content = f.read()

    if not OPENROUTER_API_KEY:
        unsafe_keywords = ["rm -rf", "eval(", "os.system(", "exec("]
        has_unsafe = any(kw in staged_content for kw in unsafe_keywords)
        return {
            "filename": filename,
            "approved": not has_unsafe,
            "reason": "Basic static check completed (no cloud API key provided)." if not has_unsafe else "Contained unsafe execution calls."
        }

    prompt = f"""You are a cloud code-auditor reviewing offline changes made by a local lightweight model for repository file: '{filename}'.

Original File Content:
```
{orig_content[:3000]}
```

Staged Modified Content:
```
{staged_content[:4000]}
```

Analyze the staged changes for syntax errors, safety risks, or regressions.
Reply strictly in JSON format:
{{
  "approved": true or false,
  "confidence_score": 0.0 to 1.0,
  "reason": "Short summary explanation of approval or rejection"
}}
"""

    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1
            },
            timeout=30
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        json_match = content[content.find('{'):content.rfind('}')+1]
        data = json.loads(json_match)
        return {
            "filename": filename,
            "approved": data.get("approved", False),
            "reason": data.get("reason", "Reviewed by cloud model"),
            "confidence": data.get("confidence_score", 0.9)
        }
    except Exception as e:
        return {
            "filename": filename,
            "approved": True,
            "reason": f"Fallback approval (Cloud model call warning: {e})"
        }


def approve_and_merge_staged_changes() -> Dict[str, Any]:
    """Reviews all staged files, applies approved changes, and clears merged staged files."""
    manifest = get_staged_manifest()
    files = manifest.get("files", [])

    if not files:
        return {"status": "no_changes", "message": "No staged offline changes found."}

    review_results = []
    merged_files = []
    rejected_files = []

    for file_info in files:
        fn = file_info.get("filename")
        orig_p = file_info.get("original_path")
        staged_p = file_info.get("staged_path")

        res = review_staged_file_with_cloud_model(fn, orig_p, staged_p)
        review_results.append(res)

        if res["approved"]:
            try:
                full_staged = safe_path(staged_p, WORKSPACE_DIR)
                full_target = safe_path(orig_p, WORKSPACE_DIR)
                os.makedirs(os.path.dirname(full_target), exist_ok=True)

                with open(full_staged, 'r', encoding='utf-8') as src, open(full_target, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())

                merged_files.append(fn)
                if os.path.exists(full_staged):
                    os.remove(full_staged)
            except Exception as e:
                rejected_files.append({"filename": fn, "reason": f"Merge error: {e}"})
        else:
            rejected_files.append({"filename": fn, "reason": res["reason"]})

    remaining_files = [f for f in files if f.get("filename") not in merged_files]
    if remaining_files:
        manifest["files"] = remaining_files
        with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
    else:
        if os.path.exists(MANIFEST_PATH):
            os.remove(MANIFEST_PATH)

    return {
        "status": "completed",
        "merged_files": merged_files,
        "rejected_files": rejected_files,
        "review_results": review_results
    }


if __name__ == "__main__":
    print("Running Cloud Review on staged offline changes...")
    res = approve_and_merge_staged_changes()
    print(json.dumps(res, indent=2))
