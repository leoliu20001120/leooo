"""Session 管理 — 内存存储（demo 用途，生产环境替换为 Redis）"""
import time
from typing import Optional

_sessions: dict[str, dict] = {}


def create_session(user_id: str) -> str:
    """创建会话"""
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
