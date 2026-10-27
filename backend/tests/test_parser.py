"""简历与文档解析器测试。"""

from __future__ import annotations

import io

import docx
from pypdf import PdfWriter

from app.services.parser import parse_document


def _make_docx(paragraphs: list[str]) -> bytes:
    document = docx.Document()
    for text in paragraphs:
        document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _make_blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_docx_parsed() -> None:
    result = parse_document("简历.docx", _make_docx(["张三", "五年后端经验"]))
    assert result.ok
    assert "张三" in result.text
    assert "五年后端经验" in result.text


def test_txt_parsed() -> None:
    result = parse_document("resume.txt", "五年 Python 经验\n熟悉 FastAPI".encode())
    assert result.ok
    assert "FastAPI" in result.text


def test_md_parsed() -> None:
    result = parse_document("notes.md", "# 标题\n内容".encode())
    assert result.ok


def test_blank_pdf_reports_empty_text() -> None:
    result = parse_document("empty.pdf", _make_blank_pdf())
    assert not result.ok
    assert result.reason == "未能从文件中提取到有效文本"


def test_broken_pdf_reports_damage() -> None:
    result = parse_document("broken.pdf", b"this is not a pdf")
    assert not result.ok
    assert result.reason == "文件损坏或不是有效的 PDF"


def test_non_utf8_text_reports_encoding_error() -> None:
    result = parse_document("legacy.txt", "中文".encode("gbk"))
    assert not result.ok
    assert result.reason == "文本文件不是有效的 UTF-8 编码"


def test_unsupported_extension() -> None:
    result = parse_document("virus.exe", b"binary")
    assert not result.ok
    assert result.reason == "不支持的文件格式"
