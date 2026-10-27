"""简历与知识库文档解析：提取纯文本。

只负责把文件内容变成可供大模型阅读的文本，不保留版式。
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import docx
from pypdf import PdfReader


@dataclass(frozen=True)
class ParseResult:
    """解析结果：ok 为 False 时 reason 说明原因。"""

    ok: bool
    text: str
    reason: str | None = None


def parse_pdf(content: bytes) -> ParseResult:
    try:
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            return ParseResult(False, "", "文件已加密，无法解析")
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception:  # noqa: BLE001 - 任何第三方解析异常都归一为解析失败
        return ParseResult(False, "", "文件损坏或不是有效的 PDF")
    return _finish("\n".join(pages))


def parse_docx(content: bytes) -> ParseResult:
    try:
        document = docx.Document(io.BytesIO(content))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    except Exception:  # noqa: BLE001
        return ParseResult(False, "", "文件损坏或不是有效的 DOCX")
    return _finish(text)


def parse_text(content: bytes) -> ParseResult:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return ParseResult(False, "", "文本文件不是有效的 UTF-8 编码")
    return _finish(text)


def parse_document(filename: str, content: bytes) -> ParseResult:
    """按扩展名分发解析；返回失败原因供上层生成错误响应。"""
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    suffix = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if suffix == "pdf":
        return parse_pdf(content)
    if suffix == "docx":
        return parse_docx(content)
    if suffix in {"txt", "md"}:
        return parse_text(content)
    return ParseResult(False, "", "不支持的文件格式")


def _finish(text: str) -> ParseResult:
    cleaned = text.strip()
    if not cleaned:
        return ParseResult(False, "", "未能从文件中提取到有效文本")
    return ParseResult(True, cleaned)
