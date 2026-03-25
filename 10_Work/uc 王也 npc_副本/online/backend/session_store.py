"""Session 管理 — 内存存储（demo 用途，生产环境替换为 Redis）"""
import time
from typing import Optional

_sessions: dict[str, dict] = {}

# 会话过期时间：2小时
SESSION_TTL = 2 * 60 * 60
# 最大会话数
MAX_SESSIONS = 1000


def _cleanup_expired():
    """清理过期会话"""
    now = time.time()
    expired = [sid for sid, s in _sessions.items() if now - s.get("created_at", 0) > SESSION_TTL]
    for sid in expired:
        del _sessions[sid]
    # 如果仍然超过最大数量，按创建时间删除最早的
    if len(_sessions) > MAX_SESSIONS:
        sorted_sessions = sorted(_sessions.items(), key=lambda x: x[1].get("created_at", 0))
        for sid, _ in sorted_sessions[:len(_sessions) - MAX_SESSIONS]:
            del _sessions[sid]


def create_session(user_id: str) -> str:
    """创建会话"""
    _cleanup_expired()
    session_id = f"sess_{int(time.time() * 1000)}_{hash(user_id) % 10000:04d}"
    _sessions[session_id] = {
        "user_id": user_id,
        "created_at": time.time(),
        "fortune_data": None,      # STEP 1 结果
        "chat_history": [],        # STEP 2 对话历史 [{round, choice, ai_reply}]
        "user_choices": [],        # 用户选择列表 ["A", "B", "free text", ...]
        "report_data": None,       # STEP 3 结果
    }
    return session_id


def get_session(session_id: str) -> Optional[dict]:
    """获取会话"""
    return _sessions.get(session_id)


def update_session(session_id: str, **kwargs):
    """更新会话字段"""
    if session_id in _sessions:
        _sessions[session_id].update(kwargs)


def add_chat_round(session_id: str, round_index: int, choice: str, ai_reply: str):
    """记录一轮对话"""
    sess = _sessions.get(session_id)
    if sess:
        sess["chat_history"].append({
            "round": round_index,
            "choice": choice,
            "ai_reply": ai_reply,
        })
        sess["user_choices"].append(choice)
