"""LLM 客户端 — 封装 OpenAI 兼容接口"""
from openai import AsyncOpenAI
from config import OPENAI_API_KEY, OPENAI_BASE_URL, MODEL_NAME

client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
)


async def chat_completion(messages: list[dict], temperature: float = 0.8, max_tokens: int = 500) -> str:
    """非流式调用，返回完整文本"""
    resp = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()


async def chat_completion_stream(messages: list[dict], temperature: float = 0.8, max_tokens: int = 800):
    """流式调用，yield 每个 delta 文本片段"""
    stream = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content
