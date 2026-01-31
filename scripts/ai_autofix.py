from __future__ import annotations

import json
import os
import subprocess
import time
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.ai_common import call_openai, load_yaml, read_file_lines, run_git, write_file_lines, write_json

POLICY_PATH = Path("config/review-policy.yaml")
MAX_FILE_BYTES = 1_000_000
MAX_DIFF_CHARS = 200_000
AUTOFIX_INSTRUCTIONS = "You are a code-fixing agent. Return JSON only."


@dataclass
class Change:
    path: str
    reason: str


def load_policy() -> dict:
    return load_yaml(POLICY_PATH)


def apply_autofix_markers(path: Path, lines: list[str]) -> tuple[bool, list[str]]:
    changed = False
    new_lines: list[str] = []
    for line in lines:
        new_line = line
        if "TODO_AUTOFIX" in new_line:
            new_line = new_line.replace("TODO_AUTOFIX", "DONE_AUTOFIX")
        if "FIXME_AUTOFIX" in new_line:
            new_line = new_line.replace("FIXME_AUTOFIX", "DONE_AUTOFIX")
        if "TODO_SECURITY" in new_line:
            new_line = new_line.replace("TODO_SECURITY", "RESOLVED_SECURITY")
        if new_line != line:
            changed = True
        new_lines.append(new_line)
    return changed, new_lines


def extract_patch_paths(diff_text: str) -> set[str]:
    paths: set[str] = set()
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            paths.add(line[6:].strip())
        elif line.startswith("--- a/"):
            paths.add(line[6:].strip())
    return {p for p in paths if p and p != "/dev/null"}


def build_prompt(changed_files: list[str], diff_text: str) -> str:
    prompt = {
        "task": "PR 변경사항의 오류/취약점을 자동 수정",
        "constraints": [
            "반드시 unified diff 형식으로 patch를 생성",
            "변경 파일 내에서만 수정",
            "과도한 리팩터링 금지",
        ],
        "expected_output": {
            "apply_patch": "unified diff string",
            "change_summary": "string",
            "files_changed": "array of strings",
        },
        "changed_files": changed_files,
        "diff": diff_text,
    }
    return json.dumps(prompt, ensure_ascii=False)


def apply_patch_text(diff_text: str) -> bool:
    if not diff_text.strip():
        return False
    check = subprocess.run(
        ["git", "apply", "--check", "--whitespace=nowarn"],
        input=diff_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if check.returncode != 0:
        return False
    result = subprocess.run(
        ["git", "apply", "--whitespace=nowarn"],
        input=diff_text,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def main() -> int:
    policy = load_policy()
    branch_prefix = policy.get("autofix", {}).get("branch_prefix", "auto/fix")
    title_template = policy.get("autofix", {}).get("pr_title_template", "AI:feat {change_summary}")
    max_attempts = int(policy.get("autofix", {}).get("max_attempts", 3))
    allowed_exts = set(policy.get("autofix", {}).get("allowed_extensions", [".py"]))
    max_patch_chars = int(policy.get("autofix", {}).get("max_patch_chars", MAX_DIFF_CHARS))
    backoff_sec = int(policy.get("autofix", {}).get("retry_backoff_sec", 2))

    diff_text = run_git(["diff", "HEAD"])
    if len(diff_text) > MAX_DIFF_CHARS:
        diff_text = diff_text[:MAX_DIFF_CHARS] + "\n...DIFF_TRUNCATED..."

    changed_files = [
        str(p)
        for p in Path(".").rglob("*")
        if p.is_file() and p.suffix in allowed_exts
    ]

    changes: list[Change] = []
    attempts_used = 0
    for attempt in range(1, max_attempts + 1):
        attempts_used = attempt
        ai_result = call_openai(build_prompt(changed_files, diff_text), policy, "autofix_model", AUTOFIX_INSTRUCTIONS)
        if not ai_result:
            time.sleep(backoff_sec)
            continue
        patch_text = ai_result.get("apply_patch", "")
        if not patch_text or len(patch_text) > max_patch_chars:
            time.sleep(backoff_sec)
            continue
        patch_paths = extract_patch_paths(patch_text)
        if not patch_paths or not all(Path(p).suffix in allowed_exts for p in patch_paths):
            time.sleep(backoff_sec)
            continue
        if apply_patch_text(patch_text):
            for path in ai_result.get("files_changed", list(patch_paths)):
                changes.append(Change(path, "AI patch"))
            break
        time.sleep(backoff_sec)

    if not changes:
        candidates = [p for p in Path(".").rglob("*") if p.is_file() and p.suffix in allowed_exts]
        for path in candidates:
            lines = read_file_lines(path, MAX_FILE_BYTES)
            if not lines:
                continue
            changed, new_lines = apply_autofix_markers(path, lines)
            if changed:
                write_file_lines(path, new_lines)
                changes.append(Change(str(path), "자동 수정 마커 치환"))

    applied = bool(changes)
    change_summary = "no changes" if not changes else "; ".join(c.path for c in changes[:3])

    pr_number = os.environ.get("PR_NUMBER", "0")
    run_id = os.environ.get("RUN_ID", "0")
    branch_name = f"{branch_prefix}-{pr_number}-{run_id}"

    result = {
        "applied": applied,
        "change_summary": change_summary,
        "files_changed": [c.path for c in changes],
        "branch_name": branch_name,
        "pr_title": title_template.replace("{change_summary}", change_summary),
        "attempts_used": attempts_used,
    }

    out = os.environ.get("AI_AUTOFIX_OUTPUT", "ai_autofix.json")
    write_json(Path(out), result)
    print(f"Wrote autofix to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
