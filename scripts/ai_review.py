from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from scripts.ai_common import call_openai, load_yaml, read_file_lines, run_git

POLICY_PATH = Path("config/review-policy.yaml")
AGENT_PROMPTS_PATH = Path("config/agent-prompts.yaml")
RULES_DIR = Path("config/rules")
MAX_FILE_BYTES = 1_000_000
MAX_DIFF_CHARS = 200_000
DEFAULT_SEVERITY_RANK = {"blocking": 3, "warn": 2, "info": 1}
LEVEL_ALIASES = {
    "block": "blocking",
    "critical": "blocking",
    "high": "blocking",
    "medium": "warn",
    "low": "info",
}
REVIEW_INSTRUCTIONS = "You are an expert code reviewer. Return JSON only."


@dataclass
class Comment:
    path: str
    line: int
    agent: str
    level: str
    body: str


def load_policy() -> dict:
    return load_yaml(POLICY_PATH)


def load_agent_prompts() -> dict:
    return load_yaml(AGENT_PROMPTS_PATH)


def load_rule_templates(names: list[str]) -> dict:
    templates: dict[str, dict] = {}
    if not RULES_DIR.exists():
        return templates
    for name in names:
        path = RULES_DIR / f"{name}.yaml"
        if not path.exists():
            continue
        templates[name] = load_yaml(path)
    return templates


def get_changed_files(base_sha: str, head_sha: str) -> list[str]:
    if not base_sha or not head_sha:
        return []
    out = run_git(["diff", "--name-only", base_sha, head_sha])
    return [line.strip() for line in out.splitlines() if line.strip()]


def find_markers(lines: Iterable[str], marker: str) -> list[int]:
    hits: list[int] = []
    for idx, line in enumerate(lines, start=1):
        if marker in line:
            hits.append(idx)
    return hits


def detect_issues(files: list[str]) -> list[Comment]:
    comments: list[Comment] = []
    for file in files:
        path = Path(file)
        lines = read_file_lines(path, MAX_FILE_BYTES)
        if not lines:
            continue

        for ln in find_markers(lines, "TODO_SECURITY") + find_markers(lines, "FIXME_SECURITY"):
            comments.append(Comment(file, ln, "SecurityAgent", "blocking", "보안 관련 TODO/FIXME 발견"))

        for ln in find_markers(lines, "TODO_AUTOFIX") + find_markers(lines, "FIXME_AUTOFIX"):
            comments.append(Comment(file, ln, "BugRiskAgent", "blocking", "자동 수정 대상 표시(AUTOFIX) 발견"))

        for ln in find_markers(lines, "NPLUS1"):
            comments.append(Comment(file, ln, "PerformanceAgent", "warn", "N+1 가능성 표시(NPLUS1) 발견"))

        long_lines = [i for i, line in enumerate(lines, start=1) if len(line) > 120]
        for ln in long_lines[:5]:
            comments.append(Comment(file, ln, "StyleAgent", "info", "라인 길이 120자 초과"))

        if re.search(r"\bauth\b|\bpermission\b|\bjwt\b", " ".join(lines), re.IGNORECASE):
            comments.append(Comment(file, 1, "SecurityAgent", "warn", "인증/인가 관련 변경 감지"))

    return comments


def build_summary(comments: list[Comment], suitability_pass: bool) -> str:
    if not suitability_pass:
        return "자동 리뷰: 변경 파일 없음"
    if not comments:
        return "자동 리뷰: 문제 없음"
    blocking = sum(1 for c in comments if c.level == "blocking")
    warn = sum(1 for c in comments if c.level == "warn")
    info = sum(1 for c in comments if c.level == "info")
    return f"자동 리뷰: 차단 {blocking} / 경고 {warn} / 정보 {info}"


def format_details(comments: list[Comment]) -> str:
    if not comments:
        return "- 이슈 없음"
    lines = []
    for c in comments:
        lines.append(f"- [{c.agent}] {c.path}:{c.line} ({c.level}) {c.body}")
    return "\n".join(lines)


def build_agent_prompt(
    agent_name: str,
    agent_spec: dict,
    changed_files: list[str],
    diff_text: str,
    rule_templates: dict[str, dict],
    aggregated: dict | None = None,
) -> str:
    prompt = {
        "agent": agent_name,
        "purpose": agent_spec.get("purpose", ""),
        "instructions": agent_spec.get("prompt", ""),
        "checks": agent_spec.get("checks", []),
        "severity_guidelines": agent_spec.get("severity_guidelines", {}),
        "rule_templates": rule_templates,
        "expected_output": agent_spec.get("schema", {}),
        "changed_files": changed_files,
        "diff": diff_text,
    }
    if aggregated:
        prompt["aggregated"] = aggregated
    return json.dumps(prompt, ensure_ascii=False)


def normalize_comments(raw_comments: list) -> list[Comment]:
    comments: list[Comment] = []
    for c in raw_comments:
        if not isinstance(c, dict):
            continue
        try:
            comments.append(
                Comment(
                    path=str(c.get("path", "")),
                    line=int(c.get("line", 1)),
                    agent=str(c.get("agent", "UnknownAgent")),
                    level=str(c.get("level", "info")),
                    body=str(c.get("body", "")),
                )
            )
        except (TypeError, ValueError):
            continue
    return comments


def normalize_level(level: str, severity_rank: dict) -> str:
    level = (level or "info").strip().lower()
    level = LEVEL_ALIASES.get(level, level)
    return level if level in severity_rank else "info"


def dedupe_comments(
    comments: list[Comment],
    severity_rank: dict,
    max_total: int,
    max_per_file: int,
) -> list[Comment]:
    merged: dict[tuple[str, int, str], Comment] = {}
    for c in comments:
        key = (c.path, c.line, c.body)
        if key not in merged:
            merged[key] = c
        else:
            prev = merged[key]
            if severity_rank.get(c.level, 0) > severity_rank.get(prev.level, 0):
                merged[key] = c

    per_file_count: dict[str, int] = {}
    result: list[Comment] = []
    for c in sorted(merged.values(), key=lambda x: severity_rank.get(x.level, 0), reverse=True):
        if len(result) >= max_total:
            break
        count = per_file_count.get(c.path, 0)
        if count >= max_per_file:
            continue
        per_file_count[c.path] = count + 1
        result.append(c)

    return result


def run_agents_ai(
    policy: dict,
    agent_prompts: dict,
    changed_files: list[str],
    diff_text: str,
) -> tuple[list[Comment], list[str], bool, bool, str | None]:
    order = policy.get("review", {}).get("agents_order", [])
    blocking_agents = set(policy.get("review", {}).get("blocking_agents", []))
    severity_rank = policy.get("review", {}).get("severity_rank", DEFAULT_SEVERITY_RANK)
    agents_cfg = agent_prompts.get("agents", {})
    rules = load_rule_templates(policy.get("review", {}).get("rule_templates", []))

    all_comments: list[Comment] = []
    details_lines: list[str] = []
    blocking = False
    suitability_pass = True if changed_files else False

    for agent_name in order:
        if agent_name == "SummaryAgent":
            continue
        spec = agents_cfg.get(agent_name, {})
        if not spec:
            continue
        prompt = build_agent_prompt(agent_name, spec, changed_files, diff_text, rules)
        result = call_openai(prompt, policy, "review_model", REVIEW_INSTRUCTIONS)
        if not result:
            continue
        comments = normalize_comments(result.get("comments", []))
        for c in comments:
            c.level = normalize_level(c.level, severity_rank)
        all_comments.extend(comments)
        agent_summary = result.get("summary")
        if agent_summary:
            details_lines.append(f"[{agent_name}] {agent_summary}")
        if result.get("blocking") and agent_name in blocking_agents:
            blocking = True

    summary_text = None
    if "SummaryAgent" in order and agents_cfg.get("SummaryAgent"):
        aggregated = {
            "comments": [c.__dict__ for c in all_comments],
            "details": details_lines,
        }
        prompt = build_agent_prompt(
            "SummaryAgent",
            agents_cfg.get("SummaryAgent", {}),
            changed_files,
            diff_text,
            rules,
            aggregated,
        )
        summary_result = call_openai(prompt, policy, "review_model", REVIEW_INSTRUCTIONS)
        if summary_result and summary_result.get("summary"):
            summary_text = summary_result.get("summary")
            details_lines.append(f"[SummaryAgent] {summary_text}")

    return all_comments, details_lines, blocking, suitability_pass, summary_text


def main() -> int:
    policy = load_policy()
    agent_prompts = load_agent_prompts()
    base_sha = os.environ.get("BASE_SHA", "")
    head_sha = os.environ.get("HEAD_SHA", "")

    changed_files = get_changed_files(base_sha, head_sha)
    if not changed_files:
        changed_files = [str(p) for p in Path(".").rglob("*.py")]

    diff_text = run_git(["diff", base_sha, head_sha]) if base_sha and head_sha else ""
    if len(diff_text) > MAX_DIFF_CHARS:
        diff_text = diff_text[:MAX_DIFF_CHARS] + "\n...DIFF_TRUNCATED..."

    ai_comments: list[Comment] = []
    ai_details_lines: list[str] = []
    ai_blocking = False
    ai_suitability_pass = False
    ai_summary: str | None = None

    if agent_prompts and os.environ.get("OPENAI_API_KEY"):
        ai_comments, ai_details_lines, ai_blocking, ai_suitability_pass, ai_summary = run_agents_ai(
            policy, agent_prompts, changed_files, diff_text
        )

    if ai_comments or ai_details_lines:
        severity_rank = policy.get("review", {}).get("severity_rank", DEFAULT_SEVERITY_RANK)
        max_total = int(policy.get("review", {}).get("max_comments_total", 50))
        max_per_file = int(policy.get("review", {}).get("max_comments_per_file", 8))
        comments = dedupe_comments(ai_comments, severity_rank, max_total, max_per_file)
        blocking_agents = set(policy.get("review", {}).get("blocking_agents", []))
        blocking = ai_blocking or any(
            c.level == "blocking" and c.agent in blocking_agents for c in comments
        )
        suitability_pass = ai_suitability_pass
        summary = ai_summary or build_summary(comments, suitability_pass)
        details = "\n".join(f"- {d}" for d in ai_details_lines) if ai_details_lines else format_details(comments)
    else:
        comments = detect_issues(changed_files)
        suitability_pass = bool(changed_files)
        blocking = any(c.level == "blocking" for c in comments) or not suitability_pass
        summary = build_summary(comments, suitability_pass)
        details = format_details(comments)

    result = {
        "status": "fail" if blocking else "pass",
        "blocking": blocking,
        "suitability_pass": suitability_pass,
        "summary": summary,
        "details": details,
        "comments": [c.__dict__ for c in comments],
        "changed_files": changed_files,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "policy": policy,
    }

    out = os.environ.get("AI_REVIEW_OUTPUT", "ai_review.json")
    Path(out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote review to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
