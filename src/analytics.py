"""
轻量使用统计模块 — 本地 JSONL 文件存储，零外部依赖。
追踪 session、查询事件，支持 DAU/WAU/检索命中率/用户使用次数/地址等指标。
"""

import os
import json
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANALYTICS_DIR = os.path.join(BASE_DIR, "data", "analytics")
SESSIONS_FILE = os.path.join(ANALYTICS_DIR, "sessions.jsonl")
EVENTS_FILE = os.path.join(ANALYTICS_DIR, "events.jsonl")


def _ensure_dir():
    os.makedirs(ANALYTICS_DIR, exist_ok=True)


def _append_jsonl(path: str, record: dict):
    _ensure_dir()
    record["_t"] = datetime.now().isoformat()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_jsonl(path: str) -> list:
    if not os.path.exists(path):
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


# ==================== 用户识别 ====================

def _get_client_ip() -> str:
    """尝试从 Streamlit 上下文获取客户端 IP。"""
    try:
        import streamlit as st
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
        if ctx:
            # 尝试从请求头获取真实 IP
            headers = getattr(ctx, 'request_headers', None) or {}
        else:
            headers = {}
    except Exception:
        headers = {}

    for key in ("X-Forwarded-For", "X-Real-IP", "Remote-Addr"):
        val = headers.get(key, "")
        if val:
            return val.split(",")[0].strip()
    return ""


def _fingerprint() -> str:
    """基于 session_id 生成匿名指纹。"""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
        if ctx and ctx.session_id:
            raw = ctx.session_id
        else:
            raw = str(uuid.uuid4())
    except Exception:
        raw = str(uuid.uuid4())
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ==================== Session 追踪 ====================

def start_session() -> str:
    """开始一个新 session，返回 session_id。"""
    session_id = str(uuid.uuid4())[:8]
    ip = _get_client_ip()
    _append_jsonl(SESSIONS_FILE, {
        "session_id": session_id,
        "fingerprint": _fingerprint(),
        "ip": ip,
        "event": "start",
    })
    return session_id


# ==================== 查询事件 ====================

def track_query(session_id: str, question: str, n_results: int,
                daily_context_used: bool = False):
    """记录一次用户查询。

    Args:
        session_id: 当前 session
        question: 用户问题原文
        n_results: RAG 检索返回的结果数（0 表示未命中）
        daily_context_used: 是否使用了每日文献筛选
    """
    fp = _fingerprint()
    ip = _get_client_ip()
    _append_jsonl(EVENTS_FILE, {
        "session_id": session_id,
        "fingerprint": fp,
        "ip": ip,
        "event": "query",
        "question_preview": question[:120],
        "question_len": len(question),
        "n_results": n_results,
        "has_results": n_results > 0,
        "daily_context_used": daily_context_used,
    })


# ==================== 指标计算 ====================

def _events() -> list:
    return _read_jsonl(EVENTS_FILE)


def _sessions() -> list:
    return _read_jsonl(SESSIONS_FILE)


def get_dau(date: Optional[datetime] = None) -> int:
    """某天的独立用户数（按 fingerprint 去重）。"""
    if date is None:
        date = datetime.now()
    date_str = date.strftime("%Y-%m-%d")
    fps = set()
    for e in _events():
        if e.get("_t", "").startswith(date_str):
            fp = e.get("fingerprint", "")
            if fp:
                fps.add(fp)
    return len(fps)


def get_daily_queries(date: Optional[datetime] = None) -> int:
    """某天的查询总数。"""
    if date is None:
        date = datetime.now()
    date_str = date.strftime("%Y-%m-%d")
    return sum(1 for e in _events()
               if e.get("event") == "query"
               and e.get("_t", "").startswith(date_str))


def get_wau() -> int:
    """过去7天的独立用户数。"""
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    fps = set()
    for e in _events():
        if e.get("_t", "") >= cutoff:
            fp = e.get("fingerprint", "")
            if fp:
                fps.add(fp)
    return len(fps)


def get_weekly_queries() -> int:
    """过去7天的查询总数。"""
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    return sum(1 for e in _events()
               if e.get("event") == "query"
               and e.get("_t", "") >= cutoff)


def get_search_hit_rate() -> float:
    """检索命中率：有结果的查询 / 总查询（全部历史）。"""
    queries = [e for e in _events() if e.get("event") == "query"]
    if not queries:
        return 0.0
    hits = sum(1 for e in queries if e.get("has_results", False))
    return round(hits / len(queries) * 100, 1)


def get_avg_queries_per_session() -> float:
    """平均每 session 查询数（全部历史）。"""
    queries_by_session = {}
    for e in _events():
        if e.get("event") != "query":
            continue
        sid = e.get("session_id", "")
        queries_by_session[sid] = queries_by_session.get(sid, 0) + 1
    if not queries_by_session:
        return 0.0
    return round(sum(queries_by_session.values()) / len(queries_by_session), 1)


# ==================== 用户使用次数 & 地址 ====================

def get_user_usage() -> list[dict]:
    """按用户（fingerprint）统计累计使用次数和最近 IP，按次数降序排列。"""
    users: dict[str, dict] = {}
    for e in _events():
        if e.get("event") != "query":
            continue
        fp = e.get("fingerprint", "")
        if not fp:
            continue
        if fp not in users:
            users[fp] = {
                "fingerprint": fp,
                "total_queries": 0,
                "last_ip": "",
                "first_seen": e.get("_t", ""),
                "last_seen": e.get("_t", ""),
            }
        users[fp]["total_queries"] += 1
        ip = e.get("ip", "")
        if ip:
            users[fp]["last_ip"] = ip
        users[fp]["last_seen"] = e.get("_t", "")
    return sorted(users.values(), key=lambda x: x["total_queries"], reverse=True)


def get_recent_ips() -> list[dict]:
    """近7天活跃用户的 IP 和地址信息。"""
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    seen = {}
    for e in _events():
        if e.get("event") != "query":
            continue
        if e.get("_t", "") < cutoff:
            continue
        fp = e.get("fingerprint", "")
        ip = e.get("ip", "")
        if fp and ip and fp not in seen:
            seen[fp] = {"fingerprint": fp, "ip": ip}
    for s in _sessions():
        if s.get("_t", "") < cutoff:
            continue
        fp = s.get("fingerprint", "")
        ip = s.get("ip", "")
        if fp and ip and fp not in seen:
            seen[fp] = {"fingerprint": fp, "ip": ip}
    return list(seen.values())


# ==================== 汇总面板 ====================

def get_stats_summary() -> dict:
    """返回管理面板所需的全部指标。"""
    users = get_user_usage()
    recent_ips = get_recent_ips()
    return {
        "dau": get_dau(),
        "daily_queries": get_daily_queries(),
        "wau": get_wau(),
        "weekly_queries": get_weekly_queries(),
        "search_hit_rate": get_search_hit_rate(),
        "avg_q_per_session": get_avg_queries_per_session(),
        "total_queries_all_time": sum(u["total_queries"] for u in users),
        "total_users_all_time": len(users),
        "top_users": users[:10],
        "recent_ips": recent_ips,
    }
