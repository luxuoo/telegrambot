"""小米 MiMo 大模型客户端 (OpenAI 兼容协议)。

只依赖 httpx,base_url 可以指向:
- 硅基流动等托管服务
- 自建 vLLM / Ollama
"""
from __future__ import annotations

import logging
import os
from collections import defaultdict, deque
from typing import Deque, Dict, List

import httpx

logger = logging.getLogger(__name__)


def _today_str() -> str:
    """返回 'Tuesday, December 16, 2025' 风格的日期字符串(英文,与官方 system prompt 一致)。"""
    from datetime import datetime
    return datetime.now().strftime("%A, %B %d, %Y")


def _build_system_prompt() -> str:
    """构造贴近官方风格的 system prompt,带当天日期。"""
    return (
        "You are MiMo, an AI assistant developed by Xiaomi. "
        f"Today is date: {_today_str()}. Your knowledge cutoff date is December 2024.\n"
        "You are now deployed in a Telegram bot called '好玩 Bot'. "
        "请用中文与用户交流,语气活泼、简洁,默认回答控制在 3 句话以内,除非用户要求详细说明。"
        "不要假装自己是 ChatGPT 或其它模型。"
    )


class MimoClient:
    """小米 MiMo 聊天客户端,自带按 chat_id 隔离的多轮上下文。

    支持两种鉴权/字段风格:
    - "xiaomi"(默认):小米官方 API,鉴权头 `api-key: xxx`,字段 `max_completion_tokens`
    - "openai":标准 OpenAI 兼容协议,`Authorization: Bearer xxx`,字段 `max_tokens`
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        history_turns: int = 8,
        timeout: float = 60.0,
        auth_style: str = "xiaomi",
        proxy: str | None = None,
    ) -> None:
        self.api_key = (api_key or "").strip()
        if not self.api_key:
            logger.warning(
                "MIMO_API_KEY 为空!如果你用的是托管服务(小米官方/硅基流动等),"
                "几乎必然会被拒(401)。仅本地 vLLM/Ollama 可以留空。"
            )
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.history_turns = history_turns  # 保留多少轮 user/assistant 对(每轮 2 条)
        self.timeout = timeout
        self.auth_style = auth_style.lower().strip() or "xiaomi"
        if self.auth_style not in ("xiaomi", "openai"):
            logger.warning("未知 MIMO_AUTH_STYLE=%s,回退到 xiaomi", self.auth_style)
            self.auth_style = "xiaomi"
        self.proxy = proxy or None
        if self.proxy:
            logger.info("MiMo 走代理: %s", self.proxy)

        # 每个 chat_id 一个上下文队列(双端队列方便丢旧消息)
        # 队列里只放 user/assistant,system 单独拼接
        self._history: Dict[int, Deque[Dict[str, str]]] = defaultdict(
            lambda: deque(maxlen=history_turns * 2)
        )

    # ---------- 对外接口 ----------
    async def chat(self, chat_id: int, user_text: str) -> str:
        """发起一次对话,返回模型回复并自动维护上下文。"""
        history = self._history[chat_id]
        messages: List[Dict[str, str]] = [{"role": "system", "content": _build_system_prompt()}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_text})

        reply = await self._call(messages)

        # 成功才落库,否则不污染上下文
        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": reply})
        return reply

    def reset(self, chat_id: int) -> None:
        self._history.pop(chat_id, None)

    def history_size(self, chat_id: int) -> int:
        return len(self._history.get(chat_id, []))

    # ---------- 内部 ----------
    async def _call(self, messages: List[Dict[str, str]]) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        payload: Dict = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "stream": False,
        }
        # 按风格分别设置鉴权头和 token 字段
        if self.auth_style == "xiaomi":
            if self.api_key:
                headers["api-key"] = self.api_key
            payload["max_completion_tokens"] = self.max_tokens
        else:  # openai
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            payload["max_tokens"] = self.max_tokens

        try:
            async with httpx.AsyncClient(timeout=self.timeout, proxy=self.proxy) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            code = e.response.status_code
            body = e.response.text[:300]
            logger.warning("MiMo HTTP %s: %s", code, body)
            if code == 401:
                raise RuntimeError("API Key 无效或为空,请检查 .env 里的 MIMO_API_KEY")
            if code == 403:
                raise RuntimeError("访问被拒(403),可能是 Key 没权限或额度用完")
            if code == 404:
                raise RuntimeError(f"模型 {self.model!r} 不存在,检查 MIMO_MODEL 配置")
            if code == 429:
                raise RuntimeError("请求太频繁了,稍后再试")
            raise RuntimeError(f"模型接口报错 ({code}),稍后再试")
        except httpx.RequestError as e:
            logger.warning("MiMo network error: %s", e)
            raise RuntimeError("连不上模型服务,检查 MIMO_BASE_URL 是否能访问")

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            logger.warning("MiMo bad response: %s, raw=%s", e, str(data)[:300])
            raise RuntimeError("模型返回格式不对")

        # 一些推理模型会带 <think>...</think>,先剥掉
        return _strip_think(content).strip()


def _strip_think(text: str) -> str:
    """剥掉 <think>...</think> 这种推理过程标签(MiMo-RL 可能会输出)。"""
    if "<think>" not in text:
        return text
    # 把所有 <think>...</think> 段去掉,可能多段
    out = []
    i = 0
    while i < len(text):
        start = text.find("<think>", i)
        if start == -1:
            out.append(text[i:])
            break
        out.append(text[i:start])
        end = text.find("</think>", start)
        if end == -1:  # 没闭合,丢弃后面
            break
        i = end + len("</think>")
    return "".join(out)


def from_env() -> MimoClient | None:
    """从环境变量构造 client;关键配置缺失则返回 None。"""
    base_url = os.getenv("MIMO_BASE_URL", "").strip()
    model = os.getenv("MIMO_MODEL", "").strip()
    if not base_url or not model:
        return None

    return MimoClient(
        api_key=os.getenv("MIMO_API_KEY", "").strip(),
        base_url=base_url,
        model=model,
        temperature=float(os.getenv("MIMO_TEMPERATURE", "0.7")),
        max_tokens=int(os.getenv("MIMO_MAX_TOKENS", "1024")),
        history_turns=int(os.getenv("MIMO_HISTORY_TURNS", "8")),
        auth_style=os.getenv("MIMO_AUTH_STYLE", "xiaomi"),
        proxy=os.getenv("MIMO_PROXY", "").strip() or None,
    )
