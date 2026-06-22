#!/usr/bin/env python3
"""Apply evolved SKILL.md over original, preserving original frontmatter.

Usage:
  python3 apply_evolution.py <original_SKILL.md> <evolved_SKILL.md>

This is needed because skill-evolution CLI overwrites the frontmatter with
its own metadata (version/parent_hash/evolution_round), which can break
description/triggers fields - and sometimes sets name=untitled.
"""
import sys, yaml

def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <original_SKILL.md> <evolved_SKILL.md>")
        sys.exit(1)

    orig_path = sys.argv[1]
    evo_path = sys.argv[2]

    orig = open(orig_path).read()
    orig_fm = "---" + orig.split("---", 2)[1] + "---"

    evo = open(evo_path).read()
    evo_parts = evo.split("---", 2)
    evo_body = evo_parts[2] if len(evo_parts) >= 3 else evo

    final = orig_fm + "\n" + evo_body
    open(orig_path, "w").write(final)

    fm_data = yaml.safe_load(orig.split("---", 2)[1])
    print(f"OK: desc={str(fm_data.get('description',''))[:40]} size={len(final)}B")

if __name__ == "__main__":
    main()
