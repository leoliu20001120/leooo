"""
异人体检站 — 在线版后端主服务
架构: FastAPI + 3 个 Sub-Agent（批命师/问诊师/出报师）
"""
import json
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
from sse_starlette.sse import EventSourceResponse

from config import HOST, PORT
from models import (
    FortuneRequest, FortuneResponse,
    ChatRequest, ChatResponse,
    ReportRequest, ReportResponse,
)
from session_store import create_session, get_session, update_session, add_chat_round
from agent_fortune import run_fortune
from agent_chat import generate_reply, generate_reply_stream, get_round_config, TOTAL_ROUNDS, CHAT_ROUNDS
from agent_report import run_report

app = FastAPI(title="异人体检站 API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件：前端
app.mount("/static", StaticFiles(directory="../frontend"), name="frontend")


@app.get("/")
async def index():
    """首页 → 前端"""
    return FileResponse("../frontend/index.html")


# ==================== API: STEP 1 批命 ====================
@app.post("/api/fortune", response_model=FortuneResponse)
async def api_fortune(req: FortuneRequest):
    """Sub-Agent 1: 批命师 — 分析 ID 五行 + 生成王也评语"""
    # 创建会话
    session_id = create_session(req.user_id)

    # 执行批命
    result = await run_fortune(req.user_id)
    result.session_id = session_id

    # 保存到会话
    update_session(session_id, fortune_data={
        "element": result.element,
        "personality_tag": result.personality_tag,
        "fortune_score": result.fortune_score,
        "ai_comment": result.ai_comment,
        "tags": result.tags,
    })

    return result


# ==================== API: STEP 2 问诊（对话） ====================
@app.get("/api/chat/rounds")
async def api_chat_rounds():
    """获取所有对话轮次配置（前端用）"""
    rounds = []
    for r in CHAT_ROUNDS:
        rounds.append({
            "round": r["round"],
            "title": r["title"],
            "ai_question": r["ai_question"],
            "story_context": r.get("story_context"),
            "options": r.get("options", []),
            "has_free_input": r.get("has_free_input", False),
            "is_final": r.get("is_final", False),
        })
    return {"total_rounds": TOTAL_ROUNDS, "rounds": rounds}


@app.post("/api/chat", response_model=ChatResponse)
async def api_chat(req: ChatRequest):
    """Sub-Agent 2: 问诊师 — 非流式回复"""
    sess = get_session(req.session_id)
    if not sess:
        raise HTTPException(404, "会话不存在")
    if req.round_index >= TOTAL_ROUNDS:
        raise HTTPException(400, "对话已结束")

    fortune_data = sess.get("fortune_data", {})

    reply = await generate_reply(
        round_index=req.round_index,
        choice=req.choice,
        user_id=sess["user_id"],
        fortune_primary=fortune_data.get("element", "火"),
        chat_history=sess["chat_history"],
    )

    # 保存对话记录
    add_chat_round(req.session_id, req.round_index, req.choice, reply)

    is_final = req.round_index >= TOTAL_ROUNDS - 1
    return ChatResponse(
        session_id=req.session_id,
        round_index=req.round_index,
        ai_reply=reply,
        next_round=None if is_final else req.round_index + 1,
        is_final=is_final,
    )


@app.post("/api/chat/stream")
async def api_chat_stream(req: ChatRequest):
    """Sub-Agent 2: 问诊师 — SSE 流式回复"""
    sess = get_session(req.session_id)
    if not sess:
        raise HTTPException(404, "会话不存在")

    fortune_data = sess.get("fortune_data", {})

    async def event_generator():
        full_reply = ""
        async for token in generate_reply_stream(
            round_index=req.round_index,
            choice=req.choice,
            user_id=sess["user_id"],
            fortune_primary=fortune_data.get("element", "火"),
            chat_history=sess["chat_history"],
        ):
            full_reply += token
            yield {"event": "token", "data": json.dumps({"text": token}, ensure_ascii=False)}

        # 流结束后保存
        add_chat_round(req.session_id, req.round_index, req.choice, full_reply)

        is_final = req.round_index >= TOTAL_ROUNDS - 1
        yield {
            "event": "done",
            "data": json.dumps({
                "full_text": full_reply,
                "next_round": None if is_final else req.round_index + 1,
                "is_final": is_final,
            }, ensure_ascii=False)
        }

    return EventSourceResponse(event_generator())


# ==================== API: STEP 3 出报告 ====================
@app.post("/api/report", response_model=ReportResponse)
async def api_report(req: ReportRequest):
    """Sub-Agent 3: 出报师 — 生成完整体检报告"""
    sess = get_session(req.session_id)
    if not sess:
        raise HTTPException(404, "会话不存在")
    if not sess.get("fortune_data"):
        raise HTTPException(400, "请先完成批命（STEP 1）")
    if len(sess.get("user_choices", [])) < TOTAL_ROUNDS:
        raise HTTPException(400, f"请先完成全部 {TOTAL_ROUNDS} 轮对话")

    report = await run_report(sess)

    update_session(req.session_id, report_data=report.model_dump())
    return report


# ==================== 健康检查 ====================
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "异人体检站 v1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=int(PORT), reload=True)
