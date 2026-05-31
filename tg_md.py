"""把模型输出的标准 Markdown 转换成 Telegram MarkdownV2。

主要做这几件事:
1. 保留并转义代码块 ```...``` 和行内代码 `...`(块内不转义其它特殊字符)
2. 把 # 标题降级为 *加粗*(Telegram 不支持标题)
3. 把 - / * 列表项替换为 • 项目符号
4. **加粗** 保持(MarkdownV2 用 *单星* 表示加粗,所以 ** 转换成 *)
5. *斜体* / _斜体_ 保留 _ 形式
6. 链接 [text](url) 保留
7. 把所有 MarkdownV2 必须转义的字符转义掉(在不影响上述格式的前提下)

参考: https://core.telegram.org/bots/api#markdownv2-style
"""
from __future__ import annotations

import re

# MarkdownV2 必须转义的字符
# _ * [ ] ( ) ~ ` > # + - = | { } . !
_MDV2_SPECIAL = r"_*[]()~`>#+-=|{}.!"


def _escape_mdv2(text: str) -> str:
    """转义 MarkdownV2 全部特殊字符(供纯文本段使用)。"""
    return "".join("\\" + c if c in _MDV2_SPECIAL else c for c in text)


def _escape_mdv2_keep(text: str, keep: str) -> str:
    """转义 MarkdownV2 特殊字符,但保留 keep 里指定的字符不转义。"""
    return "".join(
        "\\" + c if (c in _MDV2_SPECIAL and c not in keep) else c for c in text
    )


def _escape_url(url: str) -> str:
    """链接 URL 内只需要转义 ) 和 \\(MarkdownV2 规则)。"""
    return url.replace("\\", "\\\\").replace(")", "\\)")


def _escape_code(text: str) -> str:
    """代码块/行内代码内部:只需要转义 ` 和 \\。"""
    return text.replace("\\", "\\\\").replace("`", "\\`")


# 占位符前缀,用来"挖空"代码段,转义阶段不会处理它们
_PH_PREFIX = "\x00PH"
_PH_SUFFIX = "\x00"


def to_telegram_mdv2(text: str) -> str:
    """把通用 Markdown 文本转成 Telegram MarkdownV2 安全格式。"""
    # 1) 抽出代码块和行内代码,占位
    placeholders: list[str] = []

    def _stash(rendered: str) -> str:
        idx = len(placeholders)
        placeholders.append(rendered)
        return f"{_PH_PREFIX}{idx}{_PH_SUFFIX}"

    # 1a) ```lang\n...\n``` 块
    def _fence_repl(m: re.Match) -> str:
        lang = (m.group(1) or "").strip()
        body = m.group(2) or ""
        # MarkdownV2 代码块: ```lang\ncode\n```
        # lang 部分按 MarkdownV2 自身的规则,通常只用字母数字,但保险起见也转义代码字符
        rendered = "```" + lang + "\n" + _escape_code(body) + "\n```"
        return _stash(rendered)

    text = re.sub(
        r"```([^\n`]*)\n([\s\S]*?)```",
        _fence_repl,
        text,
    )

    # 1b) `inline code`(不跨行)
    def _inline_repl(m: re.Match) -> str:
        body = m.group(1)
        rendered = "`" + _escape_code(body) + "`"
        return _stash(rendered)

    text = re.sub(r"`([^`\n]+)`", _inline_repl, text)

    # 2) 处理结构(在还没转义的纯文本上做)
    out_lines: list[str] = []
    for raw_line in text.split("\n"):
        line = raw_line

        # 2a) 标题: # ~ ###### → 加粗 (Telegram 没有标题)
        m = re.match(r"^(\s*)(#{1,6})\s+(.*)$", line)
        if m:
            indent = m.group(1)
            content = m.group(3).rstrip()
            out_lines.append(indent + _convert_inline(content, bold=True))
            continue

        # 2b) 引用: > xxx → 直接保留 > 但要转义后面文本
        m = re.match(r"^(\s*)>\s?(.*)$", line)
        if m:
            indent = m.group(1)
            body = m.group(2)
            out_lines.append(indent + ">" + _convert_inline(body))
            continue

        # 2c) 无序列表: - / * / + → •
        m = re.match(r"^(\s*)[-*+]\s+(.*)$", line)
        if m:
            indent = m.group(1)
            body = m.group(2)
            # • 是普通字符,不需要转义
            out_lines.append(indent + "• " + _convert_inline(body))
            continue

        # 2d) 有序列表: 1. 2. ...保留数字,转义点
        m = re.match(r"^(\s*)(\d+)\.\s+(.*)$", line)
        if m:
            indent, num, body = m.group(1), m.group(2), m.group(3)
            out_lines.append(indent + num + "\\. " + _convert_inline(body))
            continue

        # 2e) 普通行
        out_lines.append(_convert_inline(line))

    rendered = "\n".join(out_lines)

    # 3) 把占位符替换回去(代码块原样保留)
    def _restore(m: re.Match) -> str:
        return placeholders[int(m.group(1))]

    rendered = re.sub(
        rf"{re.escape(_PH_PREFIX)}(\d+){re.escape(_PH_SUFFIX)}",
        _restore,
        rendered,
    )

    return rendered


def _convert_inline(text: str, bold: bool = False) -> str:
    """处理一行内的: **加粗**、*斜体*/_斜体_、[文本](链接)、其余字符转义。

    bold=True 表示整行作为加粗输出(标题用)。
    """
    # 把链接、加粗、斜体抽出来占位,普通文本部分单独转义
    parts: list[tuple[str, str]] = []  # (type, content)

    pattern = re.compile(
        r"(?P<bold>\*\*([^*\n]+?)\*\*)"
        r"|(?P<link>\[([^\]\n]+)\]\(([^)\n]+)\))"
        r"|(?P<italic>(?<![A-Za-z0-9])_([^_\n]+?)_(?![A-Za-z0-9]))",
    )

    last = 0
    pieces: list[str] = []
    for m in pattern.finditer(text):
        if m.start() > last:
            pieces.append(_escape_mdv2(text[last:m.start()]))
        if m.group("bold") is not None:
            inner = m.group(2)
            pieces.append("*" + _escape_mdv2(inner) + "*")
        elif m.group("link") is not None:
            label = m.group(4)
            url = m.group(5)
            pieces.append("[" + _escape_mdv2(label) + "](" + _escape_url(url) + ")")
        elif m.group("italic") is not None:
            inner = m.group(7)
            pieces.append("_" + _escape_mdv2(inner) + "_")
        last = m.end()
    if last < len(text):
        pieces.append(_escape_mdv2(text[last:]))

    body = "".join(pieces)
    if bold and body.strip():
        # 用 *...* 包整行(注意空字符串不要包)
        body = "*" + body + "*"
    return body
