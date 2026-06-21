#!/usr/bin/env python3
"""
free_ai_resources — 免费 AI 资源自动发现与推送脚本
用法:
  python3 free_ai_resources.py                   # 正常执行
  python3 free_ai_resources.py --dry-run         # 不推送，只输出
  python3 free_ai_resources.py --force           # 强制重新爬取，忽略缓存
  python3 free_ai_resources.py fetch             # 仅爬取
  python3 free_ai_resources.py parse             # 仅解析
  python3 free_ai_resources.py dedup             # 仅去重
  python3 free_ai_resources.py classify         # 仅分类
  python3 free_ai_resources.py format_feishu    # 仅格式化飞书消息
  python3 free_ai_resources.py sync_ima         # 仅同步 IMA

缓存: ~/.hermes/data/free_ai_resources.json
日志:  stdout
兼容: Python 3.10+
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# 路径常量
# ─────────────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = Path.home() / ".hermes" / "data"
CACHE_FILE = DATA_DIR / "free_ai_resources.json"
MD_FILE = DATA_DIR / "free_ai_resources.md"
IMA_SCRIPT = Path.home() / ".hermes" / "scripts" / "ima_kb.py"

# ─────────────────────────────────────────────────────────────────────────────
# 白名单（来自设计文档）
# ─────────────────────────────────────────────────────────────────────────────
WHITELIST: dict[str, dict[str, Any]] = {
    "deepseek.com":      {"name": "DeepSeek",  "aliases": ["深度求索", "DeepSeek"]},
    "aliyuncs.com":      {"name": "DashScope",  "aliases": ["阿里云百炼", "通义千问", "Qwen", "DashScope"]},
    "moonshot.cn":       {"name": "Moonshot",   "aliases": ["月之暗面", "Kimi", "Moonshot"]},
    "minimaxi.com":      {"name": "MiniMax",    "aliases": ["MiniMax"]},
    "glm-ai.com":        {"name": "GLM",        "aliases": ["智谱", "Zhipu", "GLM"]},
    "open.bigmodel.cn":  {"name": "GLM",        "aliases": ["智谱", "Zhipu", "GLM"]},
    "siliconflow.cn":    {"name": "硅基流动",   "aliases": ["SiliconFlow", "硅基流动"]},
    "tencent.com":       {"name": "腾讯混元",   "aliases": ["Hunyuan", "混元", "腾讯"]},
    "modelscope.cn":     {"name": "魔搭",       "aliases": ["ModelScope", "魔搭"]},
}

WHITELIST_ALIAS_MAP: dict[str, str] = {}
for _domain, _info in WHITELIST.items():
    for _a in _info["aliases"]:
        WHITELIST_ALIAS_MAP[_a.lower()] = _info["name"]

# ─────────────────────────────────────────────────────────────────────────────
# 搜索关键词（来自设计文档 §3）
# ─────────────────────────────────────────────────────────────────────────────
SEARCH_QUERIES = [
    "免费 AI API tokens 2026",
    "免费大模型 API 2026",
    "free LLM API 2026 free tier",
    "AI API 新用户免费 2026",
    "无需信用卡 AI API 免费",
    "学生免费 AI API 2026",
    "free AI API new platform 2026",
    "免费大模型 新平台 注册送额度",
]


# ─────────────────────────────────────────────────────────────────────────────
# 数据结构
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Resource:
    id: str = ""
    name: str = ""
    url: str = ""
    models: list[str] = field(default_factory=list)
    offer: str = ""
    status: str = ""            # new_platform | new_activity | expired | verified
    source: str = ""
    first_seen: str = ""
    last_verified: str = ""
    is_known: bool = False
    tags: list[str] = field(default_factory=list)
    raw_text: str = ""
    domain: str = ""

    @staticmethod
    def make_id(domain: str, name: str, offer: str) -> str:
        raw = f"{domain}|{name}|{offer}"
        return hashlib.sha1(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Resource:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ─────────────────────────────────────────────────────────────────────────────
# 日志
# ─────────────────────────────────────────────────────────────────────────────
class Logger:
    def __init__(self, prefix: str = ""):
        self.prefix = prefix

    def _ts(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def debug(self, msg: str):
        print(f"[{self._ts()}] {self.prefix}DEBUG: {msg}", flush=True)

    def info(self, msg: str):
        print(f"[{self._ts()}] {self.prefix}INFO: {msg}", flush=True)

    def warn(self, msg: str):
        print(f"[{self._ts()}] {self.prefix}WARN: {msg}", flush=True)

    def error(self, msg: str):
        print(f"[{self._ts()}] {self.prefix}ERROR: {msg}", flush=True)


log = Logger()


# ─────────────────────────────────────────────────────────────────────────────
# 1. fetch() — 用 web_search 搜索免费 AI 资源
# ─────────────────────────────────────────────────────────────────────────────
def extract_domain(url: str) -> str:
    """从 URL 提取注册域名（去掉 www. 和路径）。"""
    url = url.strip().rstrip("/")
    # 去掉协议
    if "://" in url:
        url = url.split("://", 1)[1]
    # 取主机部分
    host = url.split("/", 1)[0]
    # 去掉 www.
    if host.startswith("www."):
        host = host[4:]
    # 提取主域名（最后两段）
    parts = host.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def is_whitelisted(domain: str, name: str = "") -> tuple[bool, str]:
    """判断是否为白名单平台，返回 (is_known, platform_name)。"""
    # 精确域名匹配
    if domain in WHITELIST:
        return True, WHITELIST[domain]["name"]
    # 别名匹配
    haystack = (domain + " " + name).lower()
    for alias, pname in WHITELIST_ALIAS_MAP.items():
        if alias in haystack:
            return True, pname
    return False, ""


def fetch(force: bool = False) -> list[dict]:
    """
    使用 mcp_jina_search_web 搜索免费 AI 资源。
    返回原始搜索结果列表（每个元素包含 title, url, snippet 等）。
    """
    log.info("开始 fetch（搜索免费 AI 资源）...")
    cache = _load_cache()

    # 检查缓存（非 force 模式）
    if not force and cache.get("raw_results"):
        log.info(f"使用缓存 raw_results（共 {len(cache['raw_results'])} 条）。"
                 "使用 --force 强制重新爬取。")
        return cache["raw_results"]

    all_results: list[dict] = []
    seen_urls: set[str] = set()

    for query in SEARCH_QUERIES:
        try:
            log.info(f"搜索: {query}")
            # 调用 jina web_search（通过 mcp_jina_search_web 工具）
            results = _jina_web_search(query, num=20)
            for r in results:
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(r)
            log.info(f"  获取到 {len(results)} 条结果，累计 {len(all_results)} 条")
        except Exception as exc:
            log.warn(f"搜索 '{query}' 失败: {exc}")

    log.info(f"fetch 完成，共 {len(all_results)} 条原始结果")
    # 更新缓存
    cache["raw_results"] = all_results
    cache["fetched_at"] = datetime.now(timezone.utc).isoformat()
    _save_cache(cache)
    return all_results


def _jina_web_search(query: str, num: int = 20) -> list[dict]:
    """
    调用 jina web_search（通过 MCP 工具）。

    本函数在脚本内部通过子进程调用 jina CLI，或者直接利用
    mcp_jina_search_web 工具的结果（由外层代理在 fetch 阶段
    调用）。这里提供降级实现：如果环境中有 JINA_API_KEY 则
    直接用 HTTP 请求；否则返回空列表并提示。
    """
    # 该脚本被 Hermes Agent 调用时，fetch 步骤实际上由 Hermes 的
    # mcp_jina_search_web 工具完成（在 task runner 层）。此处保留
    # 接口，实际数据通过 run_pipeline() 的参数传入。
    # 若单独运行本脚本，尝试用 curl 调用 jina API。
    api_key = os.environ.get("JINA_API_KEY", "")
    if not api_key:
        # 从 Hermes config.yaml 读取 Jina key
        try:
            import yaml
            cfg_path = os.path.expanduser("~/.hermes/config.yaml")
            if os.path.exists(cfg_path):
                with open(cfg_path) as f:
                    cfg = yaml.safe_load(f)
                auth = (cfg.get("mcp_servers", {})
                          .get("jina", {})
                          .get("headers", {})
                          .get("Authorization", ""))
                if auth.startswith("Bearer "):
                    api_key = auth[len("Bearer "):]
        except Exception:
            pass
    if not api_key:
        log.warn("未设置 JINA_API_KEY，且无法从 Hermes config.yaml 读取。"
                 "请通过 Hermes Agent 调用或设置环境变量。")
        return []

    import urllib.request, urllib.error
    url = "https://s.jina.ai/search"
    payload = json.dumps({"q": query, "count": num}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Return-Format": "json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data.get("data", [])
    except Exception as exc:
        log.warn(f"Jina 搜索请求失败: {exc}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# 2. parse() — 从搜索结果提取结构化信息
# ─────────────────────────────────────────────────────────────────────────────
_MODEL_PATTERNS = [
    r'\b([A-Z][A-Za-z0-9\s\-\.]+?)\s+(v?\d+(?:\.\d+)*[A-Za-z]*)\b',
    r'(DeepSeek[-\s]?[A-Za-z0-9]+)',
    r'(Qwen[-\s]?\d?[A-Za-z0-9]*)',
    r'(Gemini\s+\d(?:\.\d)?\s*\w*)',
    r'(GPT[-\s]?\d?[A-Za-z0-9]*)',
    r'(Claude\s+\d(?:\.\d)?\s*\w*)',
    r'(Llama\s+\d(?:\.\d)?\s*\w*)',
    r'(GLM[-\s]?\d?[A-Za-z0-9.]*)',
    r'(Kimi[-\s]?[A-Za-z0-9]*)',
    r'(Step\s+\d(?:\.\d)?\s*\w*)',
]

_OFFER_KEYWORDS = [
    "免费", "free", "credits", "tokens", "额度", "RPD", "RPM",
    "req/min", "req/day", "$0", "¥0", "永久免费",
]

_TAG_KEYWORDS = {
    "国内": ["国内", "中文", "直连", "阿里云", "腾讯", "字节", "DeepSeek", "Moonshot"],
    "国际": ["international", "OpenRouter", "Groq", "Google", "NVIDIA"],
    "无需信用卡": ["无需信用卡", "no credit card", "学生友好"],
    "永久免费": ["永久免费", "永久", "permanent free"],
    "限时免费": ["限时免费", "限时", "limited time"],
    "学生友好": ["学生友好", "student", ".edu"],
}


def parse(raw_results: list[dict]) -> list[Resource]:
    """从原始搜索结果提取结构化资源条目。"""
    log.info(f"开始 parse，输入 {len(raw_results)} 条结果...")

    resources: list[Resource] = []
    seen_ids: set[str] = set()

    for item in raw_results:
        text = " ".join([
            item.get("title", ""),
            item.get("description", ""),
            item.get("snippet", ""),
            item.get("content", "")[:500],
        ])
        url = item.get("url", "")
        domain = extract_domain(url)
        name = _extract_name(item.get("title", ""), domain)
        models = _extract_models(text)
        offer = _extract_offer(text)
        tags = _extract_tags(text, domain)

        rid = Resource.make_id(domain, name, offer[:50])
        if rid in seen_ids:
            continue
        seen_ids.add(rid)

        is_known, platform_name = is_whitelisted(domain, name)
        if is_known and not name:
            name = platform_name

        r = Resource(
            id=rid,
            name=name or domain,
            url=url,
            models=models,
            offer=offer,
            source=url,
            first_seen=datetime.now(timezone.utc).isoformat(),
            last_verified=datetime.now(timezone.utc).isoformat(),
            is_known=is_known,
            tags=tags,
            raw_text=text[:1000],
            domain=domain,
        )
        resources.append(r)

    log.info(f"parse 完成，提取 {len(resources)} 条结构化资源")
    return resources


def _extract_name(title: str, domain: str) -> str:
    """从标题中提取平台名称。"""
    # 去掉常见后缀
    t = re.sub(r'\s*[-–—|:：].*', '', title).strip()
    if t:
        return t
    # 用域名生成
    parts = domain.split(".")
    return parts[0].capitalize()


def _extract_models(text: str) -> list[str]:
    """从文本中提取模型名称。"""
    models: list[str] = []
    seen: set[str] = set()
    for pat in _MODEL_PATTERNS:
        for m in re.finditer(pat, text, re.IGNORECASE):
            name = m.group(0).strip()
            name = re.sub(r'\s+', ' ', name)
            if 3 <= len(name) <= 60 and name.lower() not in seen:
                seen.add(name.lower())
                models.append(name)
    return models[:10]


def _extract_offer(text: str) -> str:
    """提取额度描述。"""
    # 找包含关键字的最短句子
    sentences = re.split(r'[。.!?\n]', text)
    candidates = [s.strip() for s in sentences
                  if any(kw in s.lower() for kw in _OFFER_KEYWORDS)
                  and 10 <= len(s.strip()) <= 200]
    if candidates:
        return max(candidates, key=len)[:200]
    return ""


def _extract_tags(text: str, domain: str) -> list[str]:
    """提取标签。"""
    tags: list[str] = []
    text_lower = text.lower()
    for tag, keywords in _TAG_KEYWORDS.items():
        if any(kw.lower() in text_lower for kw in keywords):
            tags.append(tag)
    return tags[:5]


# ─────────────────────────────────────────────────────────────────────────────
# 3. dedup() — 与现有 free_ai_resources.md 和 JSON 缓存去重
# ─────────────────────────────────────────────────────────────────────────────
def _parse_md_platforms(md_path: Path) -> dict[str, dict]:
    """解析 Markdown 文件，提取已知平台信息。"""
    known: dict[str, dict] = {}
    if not md_path.exists():
        return known

    text = md_path.read_text(encoding="utf-8")

    # 匹配 "### N. 平台名 (模型)" 或 "### 平台名" 格式
    section_pattern = re.compile(
        r'^###\s+\d*\.?\s*(.+?)(?:\s*\(([^)]+)\))?\s*$',
        re.MULTILINE
    )
    for m in section_pattern.finditer(text):
        platform_name = m.group(1).strip()
        model_info = m.group(2) or ""
        # 提取后续字段
        start = m.end()
        block = text[start:start + 800]
        url_m = re.search(r'\*\*地址\*\*:\s*(\S+)', block)
        offer_m = re.search(r'\*\*额度\*\*:\s*(.+)', block)
        status_m = re.search(r'\*\*状态\*\*:\s*(.+)', block)

        url = url_m.group(1).strip() if url_m else ""
        offer = offer_m.group(1).strip() if offer_m else ""
        status_raw = status_m.group(1).strip() if status_m else ""

        domain = extract_domain(url) if url else ""
        status = "verified"
        if "新发现" in status_raw:
            status = "new_platform"
        elif "新活动" in status_raw:
            status = "new_activity"
        elif "expired" in status_raw.lower() or "失效" in status_raw:
            status = "expired"

        key = domain or platform_name
        known[key] = {
            "name": platform_name,
            "domain": domain,
            "url": url,
            "offer": offer,
            "status": status,
            "models": [m.strip() for m in model_info.split(",") if m.strip()],
        }

    return known


def _similarity(a: str, b: str) -> float:
    """简单的字符串相似度（Jaccard on bigrams）。"""
    if not a or not b:
        return 0.0
    a, b = a.lower(), b.lower()
    if a == b:
        return 1.0
    a_bg = set(a[i:i+2] for i in range(len(a) - 1))
    b_bg = set(b[i:i+2] for i in range(len(b) - 1))
    if not a_bg or not b_bg:
        return 0.0
    return len(a_bg & b_bg) / len(a_bg | b_bg)


def _is_duplicate(new_r: Resource, existing: dict) -> bool:
    """判断是否与已知平台重复（三层去重）。"""
    # Layer 1: 域名精确匹配
    if new_r.domain and new_r.domain == existing.get("domain", ""):
        return True
    # Layer 2: 名称相似度
    sim = _similarity(new_r.name, existing.get("name", ""))
    if sim > 0.7:
        return True
    # Layer 3: 别名匹配
    existing_name = existing.get("name", "").lower()
    for alias in WHITELIST_ALIAS_MAP:
        if alias in new_r.name.lower() and alias in existing_name:
            return True
    return False


def dedup(resources: list[Resource], force: bool = False) -> list[Resource]:
    """与现有 Markdown 和 JSON 缓存去重。"""
    log.info(f"开始 dedup，输入 {len(resources)} 条资源...")

    if force:
        log.info("--force 模式，跳过去重")
        return resources

    # 加载 JSON 缓存中的已知条目
    cache = _load_cache()
    cached_resources: list[dict] = cache.get("resources", [])

    # 解析 Markdown
    md_known = _parse_md_platforms(MD_FILE)
    log.info(f"从 Markdown 解析到 {len(md_known)} 个已知平台")

    # 构建已有 ID 集合
    existing_ids: set[str] = set()
    existing_entries: list[dict] = list(md_known.values()) + cached_resources

    for entry in existing_entries:
        eid = entry.get("id", "")
        if eid:
            existing_ids.add(eid)
        # 也存域名集合
        domain = entry.get("domain", "")
        if domain:
            existing_ids.add(f"domain:{domain}")

    deduped: list[Resource] = []
    for r in resources:
        # 检查 ID
        if r.id in existing_ids:
            log.info(f"  去重 (ID): {r.name}")
            continue
        if f"domain:{r.domain}" in existing_ids and r.domain:
            log.info(f"  去重 (domain): {r.name}")
            continue
        # 检查与已知条目是否重复
        is_dup = any(_is_duplicate(r, e) for e in existing_entries)
        if is_dup:
            log.info(f"  去重 (fuzzy): {r.name}")
            continue
        deduped.append(r)

    log.info(f"dedup 完成，剩余 {len(deduped)} 条新资源")
    return deduped


# ─────────────────────────────────────────────────────────────────────────────
# 4. classify() — 分类为 new_platform / new_activity / expired
# ─────────────────────────────────────────────────────────────────────────────
def classify(resources: list[Resource]) -> dict[str, list[Resource]]:
    """将资源分类。"""
    log.info(f"开始 classify，输入 {len(resources)} 条...")

    cache = _load_cache()
    cached_resources: list[dict] = cache.get("resources", [])

    # 已知平台（来自缓存 + markdown）
    md_known = _parse_md_platforms(MD_FILE)
    all_known: dict[str, Resource] = {}

    for entry in cached_resources + list(md_known.values()):
        domain = entry.get("domain", "")
        name = entry.get("name", "")
        if domain:
            all_known[domain] = Resource.from_dict(entry)
        if name:
            all_known[name.lower()] = Resource.from_dict(entry)

    now = datetime.now(timezone.utc)
    result: dict[str, list[Resource]] = {
        "new_platform": [],
        "new_activity": [],
        "expired": [],
        "verified": [],
    }

    for r in resources:
        is_known, platform_name = is_whitelisted(r.domain, r.name)

        if is_known:
            # 白名单平台 → new_activity
            r.is_known = True
            r.name = r.name or platform_name
            r.status = "new_activity"
            result["new_activity"].append(r)
        else:
            # 检查是否在已知平台中（非白名单）
            known_match = None
            for k, known_r in all_known.items():
                if _is_duplicate(r, known_r.to_dict()):
                    known_match = known_r
                    break

            if known_match:
                # 已存在 → 更新 last_verified，标记为 verified
                r.status = "verified"
                r.last_verified = now.isoformat()
                result["verified"].append(r)
            else:
                # 全新平台
                r.status = "new_platform"
                result["new_platform"].append(r)

    log.info(
        f"classify 完成: "
        f"new_platform={len(result['new_platform'])}, "
        f"new_activity={len(result['new_activity'])}, "
        f"verified={len(result['verified'])}"
    )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 5. format_feishu() — 格式化为飞书消息
# ─────────────────────────────────────────────────────────────────────────────
def format_feishu(classified: dict[str, list[Resource]]) -> str:
    """格式化飞书消息（新发现最多 5 条 + 新活动最多 3 条）。"""
    log.info("format_feishu: 生成飞书消息...")

    parts: list[str] = []
    new_platforms = classified.get("new_platform", [])[:5]
    new_activities = classified.get("new_activity", [])[:3]

    if not new_platforms and not new_activities:
        log.info("无新内容，跳过飞书消息生成")
        return ""

    if new_platforms:
        parts.append("🆕 新发现：")
        for r in new_platforms:
            models_str = ", ".join(r.models[:5]) if r.models else "见详情"
            tags_str = " ".join(r.tags) if r.tags else ""
            parts.append(f"• {r.name}")
            parts.append(f"  - 模型：{models_str}")
            parts.append(f"  - 额度：{r.offer or '见官网'}")
            parts.append(f"  - 地址：{r.url}")
            if tags_str:
                parts.append(f"  - 标签：{tags_str}")
            parts.append("")

    if new_activities:
        parts.append("🎉 新活动（已嫖平台）：")
        for r in new_activities:
            parts.append(f"• {r.name}")
            parts.append(f"  - 活动内容：{r.offer or r.raw_text[:80]}")
            parts.append("")

    msg = "\n".join(parts).rstrip()
    log.info(f"飞书消息已生成（{len(msg)} 字符）")
    return msg


# ─────────────────────────────────────────────────────────────────────────────
# 6. sync_ima() — 调用 ima_kb.py 同步到 IMA 知识库
# ─────────────────────────────────────────────────────────────────────────────
# IMA 知识库配置（来自设计文档 §6.1）
IMA_KB_CONFIGS = [
    {
        "name": "个人知识库",
        "kb_id": "RiAyZ6HYD-RRnH1UrNp0gOrHjq5d5nkYoudomp4p6Ek=",
        "folder_id": "folder_7474053199713640",
    },
    {
        "name": "共享知识库",
        "kb_id": "Ofo66mNFtzUO0O5_ifJNQiXe3un7O5vxzM0NWBBsf5M=",
        "folder_id": "folder_e06978dae3a1a1cbf7511c8db6e30137",
    },
]


def sync_ima(resources: list[Resource], dry_run: bool = False) -> dict[str, Any]:
    """
    同步 new_platform 状态的资源到 IMA 知识库。
    返回 {"synced": [...], "failed": [...]}
    """
    log.info("sync_ima: 开始同步到 IMA 知识库...")

    if dry_run:
        log.info("--dry-run 模式，跳过实际同步")
        return {"dry_run": True, "synced": [], "failed": []}

    new_platforms = [r for r in resources if r.status == "new_platform"]
    if not new_platforms:
        log.info("无 new_platform 资源需要同步")
        return {"synced": [], "failed": []}

    # 获取 IMA 凭证
    try:
        sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))
        from ima_kb import get_credentials, import_url, search_knowledge
        creds = get_credentials()
    except ImportError:
        log.error("无法导入 ima_kb.py，跳过 IMA 同步")
        return {"synced": [], "failed": [r.id for r in new_platforms],
                "error": "ima_kb import failed"}

    synced: list[str] = []
    failed: list[str] = []

    # 使用共享知识库（任务指定）
    kb_cfg = IMA_KB_CONFIGS[1]  # 共享知识库

    for r in new_platforms:
        if not r.url:
            log.warn(f"跳过（无 URL）: {r.name}")
            failed.append(r.id)
            continue

        # 去重检查：在 IMA 中搜索是否已存在
        try:
            found, _ = search_knowledge(r.name, kb_cfg["kb_id"], creds)
            if found and found.get("code") == 0:
                results = found.get("data", {}).get("note_infos", [])
                if any(r.name.lower() in n.get("title", "").lower() for n in results):
                    log.info(f"IMA 已存在，跳过: {r.name}")
                    synced.append(r.id)  # 标记为已同步（视为成功）
                    continue
        except Exception as exc:
            log.warn(f"IMA 搜索检查失败 ({r.name}): {exc}")

        # 调用 import_urls
        title = f"{r.name} — {r.offer[:50]}" if r.offer else r.name
        try:
            data, err = import_url(kb_cfg["kb_id"], [r.url], creds)
            if err:
                log.error(f"IMA 同步失败 ({r.name}): {err}")
                failed.append(r.id)
            elif data and data.get("code") == 0:
                log.info(f"✓ IMA 同步成功: {r.name}")
                synced.append(r.id)
            else:
                log.error(f"IMA 同步异常 ({r.name}): {data}")
                failed.append(r.id)
        except Exception as exc:
            log.error(f"IMA 同步异常 ({r.name}): {exc}")
            failed.append(r.id)

    log.info(f"sync_ima 完成: {len(synced)} 成功, {len(failed)} 失败")
    return {"synced": synced, "failed": failed}


# ─────────────────────────────────────────────────────────────────────────────
# 缓存管理
# ─────────────────────────────────────────────────────────────────────────────
def _load_cache() -> dict:
    """加载 JSON 缓存。"""
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_cache(cache: dict):
    """保存 JSON 缓存。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.debug(f"缓存已保存到 {CACHE_FILE}")


def _update_resource_cache(classified: dict[str, list[Resource]]):
    """将分类后的资源更新到缓存。"""
    cache = _load_cache()
    existing: dict[str, dict] = {r["id"]: r for r in cache.get("resources", [])}

    all_resources = (
        classified.get("new_platform", [])
        + classified.get("new_activity", [])
        + classified.get("verified", [])
        + classified.get("expired", [])
    )
    for r in all_resources:
        existing[r.id] = r.to_dict()

    cache["resources"] = list(existing.values())
    cache["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_cache(cache)
    log.info(f"缓存已更新（共 {len(existing)} 条资源）")


# ─────────────────────────────────────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────────────────────────────────────
def run_pipeline(
    raw_results: list[dict] | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """
    执行完整 pipeline:
      fetch → parse → dedup → classify → format_feishu → sync_ima

    如果提供了 raw_results（从 Hermes Agent 工具层获取），
    则跳过 fetch 步骤直接使用。
    """
    log.info("=" * 60)
    log.info("free_ai_resources pipeline 启动")
    log.info(f"dry_run={dry_run}, force={force}")
    log.info("=" * 60)

    # 1. fetch
    if raw_results is None:
        raw_results = fetch(force=force)
    else:
        log.info(f"使用外部传入的 {len(raw_results)} 条原始结果，跳过 fetch")

    # 2. parse
    resources = parse(raw_results)

    if not resources:
        log.warn("parse 结果为空，终止 pipeline")
        return {"error": "no resources parsed", "feishu_msg": ""}

    # 3. dedup
    resources = dedup(resources, force=force)

    if not resources:
        log.warn("去重后无新资源，终止 pipeline")
        return {"error": "no new resources after dedup", "feishu_msg": ""}

    # 4. classify
    classified = classify(resources)

    # 5. format_feishu
    feishu_msg = format_feishu(classified)

    # 6. sync_ima
    all_new = (
        classified.get("new_platform", [])
        + classified.get("new_activity", [])
        + classified.get("verified", [])
    )
    ima_result = sync_ima(all_new, dry_run=dry_run)

    # 更新缓存
    if not dry_run:
        _update_resource_cache(classified)

    # 输出飞书消息（到 stdout，方便外部捕获）
    if feishu_msg:
        print("\n" + "=" * 60)
        print("飞书消息:")
        print("=" * 60)
        print(feishu_msg)
        print("=" * 60 + "\n", flush=True)

    log.info("pipeline 完成")
    return {
        "classified": {k: len(v) for k, v in classified.items()},
        "feishu_msg": feishu_msg,
        "ima_result": ima_result,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI 入口
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="免费 AI 资源自动发现与推送",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=[
            "run", "fetch", "parse", "dedup", "classify",
            "format_feishu", "sync_ima",
        ],
        help="执行步骤（默认: run 全流程）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="不推送、不同步，只输出结果",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新爬取，忽略缓存",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细日志",
    )
    args = parser.parse_args()

    if args.verbose:
        global log
        log = Logger()

    dry_run = args.dry_run
    force = args.force

    # 单步执行
    if args.command == "fetch":
        fetch(force=force)
        return
    elif args.command == "parse":
        raw = fetch(force=force)
        parse(raw)
        return
    elif args.command == "dedup":
        raw = fetch(force=force)
        resources = parse(raw)
        dedup(resources, force=force)
        return
    elif args.command == "classify":
        raw = fetch(force=force)
        resources = parse(raw)
        resources = dedup(resources, force=force)
        classify(resources)
        return
    elif args.command == "format_feishu":
        raw = fetch(force=force)
        resources = parse(raw)
        resources = dedup(resources, force=force)
        classified = classify(resources)
        msg = format_feishu(classified)
        if msg:
            print(msg)
        return
    elif args.command == "sync_ima":
        raw = fetch(force=force)
        resources = parse(raw)
        resources = dedup(resources, force=force)
        classified = classify(resources)
        all_new = (
            classified.get("new_platform", [])
            + classified.get("new_activity", [])
            + classified.get("verified", [])
        )
        sync_ima(all_new, dry_run=dry_run)
        return

    # 默认 run 全流程
    run_pipeline(dry_run=dry_run, force=force)


if __name__ == "__main__":
    main()
