#!/usr/bin/env python3
"""
Raw API evolution runner for single-skill fast evolutions.
More controllable than skill-evolution CLI - add hard constraints in system prompt.

Usage:
  python3 evolve_raw.py <path/to/SKILL.md> [provider]

Provider: openmodel (default), deepseek

Environment variables read from ~/.hermes/.env:
  OPENMODEL_API_KEY (default)
  DEEPSEEK_API_KEY (for official DeepSeek, requires user authorization)
"""
import os, json, time, re, sys, urllib.request
from pathlib import Path

env_file = os.path.expanduser("~/.hermes/.env")

PROVIDERS = {
    "openmodel": {
        "key_var": "OPENMODEL_API_KEY",
        "base_url": "https://api.openmodel.ai/v1",
        "model": "deepseek-v4-flash",
        "anthropic_protocol": True,
    },
    "deepseek": {
        "key_var": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
    },
}


def load_key(provider_name):
    cfg = PROVIDERS[provider_name]
    with open(env_file) as f:
        for line in f:
            if line.startswith(cfg["key_var"] + "="):
                return cfg, line.split("=", 1)[1].strip()
    raise RuntimeError(f"{cfg['key_var']} not found in {env_file}")


def call_api(messages, system, key, cfg, max_tokens=8000, temperature=0.3):
    body = {
        "model": cfg["model"],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [],
    }
    if system:
        body["messages"].append({"role": "system", "content": system})
    body["messages"].extend(messages)

    url = f"{cfg['base_url']}/chat/completions"
    body_bytes = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=body_bytes,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            err = e.read()[:300].decode("utf-8", errors="replace")
            print(f"[retry {attempt+1}/3] HTTP {e.code}: {err}", file=sys.stderr)
            if e.code in (402, 401, 403):
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("API failed after 3 retries")


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path/to/SKILL.md> [provider]")
        sys.exit(1)

    skill_path = Path(sys.argv[1])
    provider_name = sys.argv[2] if len(sys.argv) > 2 else "openmodel"

    if provider_name == "deepseek":
        print(
            "WARNING: DeepSeek official requires user authorization. "
            "Ask user first!",
            file=sys.stderr,
        )

    cfg, key = load_key(provider_name)
    backup_path = skill_path.with_suffix(".md.bak-evolution")

    # Backup original
    content = skill_path.read_text()
    backup_path.write_text(content)
    print(f"Backup: {backup_path} ({len(content)} bytes)")

    # Build system prompt with hard constraints
    system = """你是 Hermes SKILL.md 优化专家。精简+重组，但保留所有关键能力。

硬约束:
1. frontmatter 保留: name, description
2. version 必须是 integer (如 2)
3. 保留 P0 全字段利用表（如有）
4. 保留算法公式（如有）
5. 保留核心数据字典（如有）
6. 保留关键执行步骤/流程顺序
7. 保留关键命令路径
8. 保留"踩坑"小节

可优化: 删冗余/合并/简化/重组

输出: 完整 SKILL.md (frontmatter + markdown body)，无前后缀说明。"""

    user_msg = f"请优化:\n\n```markdown\n{content}\n```\n\n输出优化后完整 SKILL.md。"

    t0 = time.time()
    response = call_api(
        messages=[{"role": "user", "content": user_msg}],
        system=system,
        key=key,
        cfg=cfg,
        max_tokens=8000,
    )
    elapsed = time.time() - t0

    # Strip code fences if present
    if "```markdown" in response:
        m = re.search(r"```markdown\n(.*?)```", response, re.DOTALL)
        if m:
            response = m.group(1)
    elif response.startswith("```"):
        response = re.sub(r"^```(?:markdown)?\n?", "", response)
        response = re.sub(r"\n```$", "", response)

    # Ensure frontmatter
    if not response.startswith("---"):
        response = (
            "---\n"
            f"name: {skill_path.stem}\n"
            "description: Evolved version\n"
            "version: 2\n"
            "---\n\n"
        ) + response

    # Write result
    new_path = skill_path.with_suffix(".md.new")
    new_path.write_text(response)
    print(f"\nWritten: {new_path}")
    print(f"Original: {len(content)} → Evolved: {len(response)}")
    print(f"Compression: {(1 - len(response) / len(content)) * 100:.0f}%")
    print(f"Time: {elapsed:.1f}s")

    # Show diff summary
    print(f"\n--- First 300 chars of evolved ---")
    print(response[:300])
    print(f"\n--- Last 300 chars of evolved ---")
    print(response[-300:])


if __name__ == "__main__":
    main()
