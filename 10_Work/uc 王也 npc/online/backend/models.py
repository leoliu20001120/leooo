"""Pydantic 数据模型"""
from pydantic import BaseModel, Field
from typing import Optional


# ==================== STEP 1: 批命 ====================
class FortuneRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=50, description="用户ID/网名/姓名")


class WuxingResult(BaseModel):
    char: str
    element: str  # 金/木/水/火/土
    method: str   # char/alpha/num/stroke/code
    detail: str


class WuxingAnalysis(BaseModel):
    char_results: list[WuxingResult]
    wuxing_count: dict[str, int]
    primary: str        # 主五行
    secondary: Optional[str] = None  # 辅五行
    balance: int        # 平衡度 0-100


class FortuneResponse(BaseModel):
    session_id: str
    user_id: str
    element: str               # 主五行
    element_emoji: str
    personality_tag: str       # 人格标签
    fortune_score: int         # 命数分
    abnormal_star: int         # 异人潜质星级
    combat_star: int           # 格斗直觉星级
    wuxing_analysis: WuxingAnalysis
    ai_comment: str            # LLM 生成的王也评语
    tags: list[str]            # 2-3个标签


# ==================== STEP 2: 问诊 ====================
class ChatRequest(BaseModel):
    session_id: str
    round_index: int           # 0-3 (3+1模式)
    choice: str                # "A" / "B" / 用户自由输入文本


class ChatResponse(BaseModel):
    """非 SSE 模式下的回复"""
    session_id: str
    round_index: int
    ai_reply: str
    next_round: Optional[int] = None  # None 表示对话完成
    is_final: bool = False


# ==================== STEP 3: 报告 ====================
class ReportRequest(BaseModel):
    session_id: str


class Dimension(BaseModel):
    name: str
    score: int
    label: str
    color: str


class FightingProfile(BaseModel):
    style: str
    style_desc: str
    dimensions: list[Dimension]
    tags: list[str]


class AlienPersonality(BaseModel):
    faction: str
    master: str
    ability: str
    partner: str
    enemy: str
    master_reason: str = ""
    partner_reason: str = ""
    enemy_reason: str = ""
    personality_tags: list[str]


class ReportResponse(BaseModel):
    report_id: str
    user_name: str
    fighting_profile: FightingProfile
    alien_personality: AlienPersonality
    deep_comment: str
    destiny_prophecy: str
    share_summary: str
    first_impression: str   # 批命文本
