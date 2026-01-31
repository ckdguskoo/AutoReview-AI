from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Iterable

import requests
import yaml


def run_git(args: list[str]) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def read_file_lines(path: Path, max_bytes: int) -> list[str]:
    if not path.exists() or not path.is_file():
        return []
    if path.stat().st_size > max_bytes:
        return []
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return []


def write_file_lines(path: Path, lines: Iterable[str]) -> None:
    text = "\n".join(lines) + "\n"
    path.write_text(text, encoding="utf-8")


def extract_output_text(response_json: dict) -> str:
    output = response_json.get("output", [])
    texts: list[str] = []
    for item in output:
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                texts.append(content.get("text", ""))
    return "\n".join(t for t in texts if t)


def parse_json_from_text(text: str) -> dict | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def call_openai(prompt: str, policy: dict, model_key: str, instructions: str) -> dict | None:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    ai_cfg = policy.get("ai", {})
    model = os.environ.get("OPENAI_MODEL", ai_cfg.get(model_key, "gpt-4.1"))
    temperature = float(ai_cfg.get("temperature", 0.2))
    max_output_tokens = int(ai_cfg.get("max_output_tokens", 1200))
    timeout_sec = int(ai_cfg.get("request_timeout_sec", 120))

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    org = os.environ.get("OPENAI_ORG", "").strip()
    proj = os.environ.get("OPENAI_PROJECT", "").strip()
    if org:
        headers["OpenAI-Organization"] = org
    if proj:
        headers["OpenAI-Project"] = proj

    payload = {
        "model": model,
        "input": prompt,
        "instructions": instructions,
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
        "store": False,
    }

    resp = requests.post(
        "https://api.openai.com/v1/responses",
        headers=headers,
        json=payload,
        timeout=timeout_sec,
    )
    if resp.status_code != 200:
        return None

    data = resp.json()
    text = extract_output_text(data)
    return parse_json_from_text(text)
