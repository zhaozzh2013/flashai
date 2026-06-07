"""轻量级 Markdown -> HTML 转换器。
覆盖:标题、粗体、斜体、行内代码、代码块、列表、引用、链接、水平线、段落。
不依赖外部库;只输出安全的 HTML(已 HTML 转义)。
"""
import re
from html import escape

_CODE_MONO = (
    "ui-monospace, SFMono-Regular, Menlo, Consolas, "
    "'Liberation Mono', 'Cascadia Code', monospace"
)


def _inline(text: str) -> str:
    """处理行内的:粗体 / 斜体 / 行内代码 / 链接。
    顺序很重要:先匹配行内代码(把内容保护起来),再做其他替换。"""
    # 1) 行内代码:把内容里的特殊字符原样保留
    code_tokens: list[str] = []

    def _code_repl(m: re.Match) -> str:
        code_tokens.append(m.group(1))
        return f"\x00CODE{len(code_tokens) - 1}\x00"

    text = re.sub(r"`([^`\n]+)`", _code_repl, text)
    # 2) HTML 转义
    text = escape(text, quote=False)
    # 3) 链接 [text](url)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)\s]+)\)",
        lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>',
        text,
    )
    # 4) 粗体 **...**(非贪婪,中间不跨行)
    text = re.sub(r"\*\*([^*\n]+)\*\*", r"<b>\1</b>", text)
    # 5) 斜体 *...*(非贪婪,中间不跨行,且不会被 ** 误伤)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", text)
    # 6) 把代码占位符替换回 HTML(用 pre-style 的 <code>)
    for i, c in enumerate(code_tokens):
        text = text.replace(
            f"\x00CODE{i}\x00",
            f'<code style="background:#2a2b30;border-radius:3px;'
            f'padding:1px 5px;font-family:{_CODE_MONO};'
            f'font-size:13px;">{escape(c)}</code>',
        )
    return text


def render(md: str) -> str:
    """把一段 Markdown 文本转成 HTML(给 QTextEdit.insertHtml 用)。"""
    if not md:
        return ""

    lines = md.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []

    in_code = False
    code_buf: list[str] = []
    list_stack: list[str] = []  # 'ul' / 'ol'

    def close_lists() -> None:
        while list_stack:
            out.append(f"</{list_stack.pop()}>")

    i = 0
    while i < len(lines):
        line = lines[i]

        # ``` 围栏代码块
        if line.strip().startswith("```"):
            if not in_code:
                # 进入代码块
                close_lists()
                in_code = True
                code_buf = []
                i += 1
                continue
            else:
                # 结束代码块
                code = escape("\n".join(code_buf))
                out.append(
                    f'<pre style="background:#15161a;border:1px solid #2a2b30;'
                    f'border-radius:5px;padding:10px 12px;margin:6px 0;'
                    f'font-family:{_CODE_MONO};font-size:13px;'
                    f'color:#cdd6f4;white-space:pre;overflow-x:auto;">'
                    f"{code}</pre>"
                )
                in_code = False
                i += 1
                continue

        if in_code:
            code_buf.append(line)
            i += 1
            continue

        stripped = line.strip()

        # 空行 -> 段落分隔
        if not stripped:
            close_lists()
            out.append("<br/>")
            i += 1
            continue

        # 水平线
        if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", stripped):
            close_lists()
            out.append('<hr style="border:none;border-top:1px solid #2a2b30;margin:8px 0;"/>')
            i += 1
            continue

        # 标题
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            close_lists()
            level = len(m.group(1))
            size = {1: 20, 2: 17, 3: 15, 4: 14, 5: 13, 6: 13}.get(level, 14)
            content = _inline(m.group(2))
            out.append(
                f'<p style="margin:8px 0 4px 0;color:#ffffff;'
                f'font-size:{size}px;font-weight:700;">{content}</p>'
            )
            i += 1
            continue

        # 引用
        m = re.match(r"^>\s?(.*)$", stripped)
        if m:
            close_lists()
            content = _inline(m.group(1))
            out.append(
                f'<blockquote style="margin:4px 0;padding:2px 10px;'
                f'border-left:3px solid #5a6480;color:#b6bac1;">{content}</blockquote>'
            )
            i += 1
            continue

        # 无序列表
        m = re.match(r"^[-*+]\s+(.*)$", stripped)
        if m:
            if list_stack and list_stack[-1] != "ul":
                out.append(f"</{list_stack.pop()}>")
            if not list_stack:
                out.append('<ul style="margin:4px 0 4px 0;padding-left:22px;color:#d6d6d6;">')
                list_stack.append("ul")
            out.append(f"<li>{_inline(m.group(1))}</li>")
            i += 1
            continue

        # 有序列表
        m = re.match(r"^\d+[.)]\s+(.*)$", stripped)
        if m:
            if list_stack and list_stack[-1] != "ol":
                out.append(f"</{list_stack.pop()}>")
            if not list_stack:
                out.append('<ol style="margin:4px 0 4px 0;padding-left:22px;color:#d6d6d6;">')
                list_stack.append("ol")
            out.append(f"<li>{_inline(m.group(1))}</li>")
            i += 1
            continue

        # 普通段落:把连续的普通行合并
        para = [stripped]
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            nxt_strip = nxt.strip()
            if (
                not nxt_strip
                or nxt_strip.startswith(("#", ">", "```", "-", "*", "+"))
                or re.match(r"^\d+[.)]\s+", nxt_strip)
                or re.fullmatch(r"-{3,}|\*{3,}|_{3,}", nxt_strip)
            ):
                break
            para.append(nxt_strip)
            j += 1
        close_lists()
        out.append(
            f'<p style="margin:4px 0;line-height:1.7;">{_inline(" ".join(para))}</p>'
        )
        i = j

    close_lists()
    if in_code:
        # 没闭合的代码块,当文本输出
        code = escape("\n".join(code_buf))
        out.append(
            f'<pre style="background:#15161a;border:1px solid #2a2b30;'
            f'border-radius:5px;padding:10px 12px;margin:6px 0;'
            f'font-family:{_CODE_MONO};font-size:13px;'
            f'color:#cdd6f4;white-space:pre;overflow-x:auto;">'
            f"{code}</pre>"
        )

    return "".join(out)
