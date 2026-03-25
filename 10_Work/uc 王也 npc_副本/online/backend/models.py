"""Pydantic 数据模型 — 炁脉鉴定系统"""
from pydantic import BaseModel, Field
from typing import Optional


# ==================== STEP 1: 炁脉鉴定 ====================
class FortuneRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=50, description="用户ID/网名/姓名")


class QiAnalysisResult(BaseModel):
    """单个字符的炁脉分析结果"""
    char: str
    qi_scores: dict[str, float]   # 6维分数 {fenghou: 0.3, qiti: 0.1, ...}
    method: str                   # char/alpha/num/unicode
    detail: str


class QiAnalysis(BaseModel):
    """完整炁脉分析"""
    char_results: list[QiAnalysisResult]
    qi_totals: dict[str, float]         # 6维总分
    primary_qi: str                     # 主炁脉（英文key）
    secondary_qi: Optional[str] = None  # 暗合属性
    potential_grade: str                # 甲等·破格 / 乙等·上品 / 丙等·良才 / 丁等·待觉醒
    balance: int                        # 平衡度 0-100


class FortuneResponse(BaseModel):
    """炁脉鉴定结果"""
    session_id: str
    user_id: str
    qi_type: str              # 主炁脉中文名
    qi_type_key: str          # 英文key
    qi_emoji: str
    aligned_character: str    # 暗合角色
    potential_grade: str      # 潜力评级
    fortune_score: int        # 命数分
    abnormal_star: int        # 异人潜质星级
    combat_star: int          # 格斗直觉星级
    qi_analysis: QiAnalysis
    ai_comment: str           # LLM 生成的王也评语
    tags: list[str]           # 2-3个标签


# ==================== STEP 2: 问诊（5轮） ====================
class ChatRequest(BaseModel):
    session_id: str
    round_index: int           # 0-4 (5轮)
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
    personality_tags: list[str]


class ReportResponse(BaseModel):
    report_id: str
    user_name: str
    fighting_profile: FightingProfile
    alien_personality: AlienPersonality
    deep_comment: str
    destiny_prophecy: str
    share_summary: str
    first_impression: str      # 批命文本
    qi_type: str               # 主炁脉中文名
    qi_aligned_char: str       # 暗合角色
