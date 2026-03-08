import pytest
from law.utils.text import normalize_whitespace, clean_html_text

def test_normalize_whitespace():
    assert normalize_whitespace("  hello  \n\n\nworld  ") == "hello\n\nworld"
    assert normalize_whitespace("line1\r\nline2\rline3") == "line1\nline2\nline3"
    # normalize_whitespace now preserves leading spaces on subsequent lines
    assert normalize_whitespace("line1\n  line2") == "line1\n  line2"

def test_clean_html_text_basic():
    text = "제1조(목적) 이 법은 ... "
    assert clean_html_text(text) == "제1조(목적) 이 법은 ..."

def test_clean_html_text_with_hierarchy():
    text = """
    제1조(목적)
    이 법은 ...
    ① 이 항은 ...
    1. 이 호는 ...
    가. 이 목은 ...
    """
    # Note: clean_html_text indents items and points
    cleaned = clean_html_text(text)
    assert "제1조(목적)" in cleaned
    assert "① 이 항은 ..." in cleaned
    assert "  1. 이 호는 ..." in cleaned  # Indented
    assert "    가. 이 목은 ..." in cleaned # More indented

def test_clean_html_text_flowing():
    # Fragmented text should be joined, including the article header title if follow-on
    text = """
    제1조(목적)
    본 법은 국가의
    안녕과 질서를
    유지함을 목적으로 한다.
    """
    cleaned = clean_html_text(text)
    # RAG Optimization: Flow non-structural following text into the header line
    assert cleaned == "제1조(목적) 본 법은 국가의 안녕과 질서를 유지함을 목적으로 한다."

def test_clean_html_text_connector_logic():
    # Lines ending with connectors like '법', '령' should flow even if next line looks like a marker (unless article header)
    text = """
    이 사항은 형사소송
    법
    1. 관련 조항 ...
    """
    cleaned = clean_html_text(text)
    # Since '법' is a connector, '1. 관련 조항 ...' might be flowed if not careful, 
    # but the logic says 'unless it's a clear Article Header'. 
    # Actually, current logic in text.py:
    # is_connector = re.search(r'(법|령|칙|항|호|목|절|장|편|관|등)$', prev_line)
    # if is_connector and not is_article_header: flowed_lines[-1] = f"{prev_line} {line}"
    
    # Let's check if '1. 관련 조항' is flowed.
    assert "형사소송 법 1. 관련 조항 ..." in cleaned

def test_clean_html_text_article_header_not_flowed():
    text = """
    관련된
    형법
    제1조(목적)
    """
    cleaned = clean_html_text(text)
    # '형법' ends with '법', but '제1조(목적)' is an article header, so it should NOT be flowed.
    lines = cleaned.split("\n")
    assert "제1조(목적)" in lines[-1]
    assert "형법 제1조" not in cleaned

def test_clean_html_text_special_markers():
    text = "【제1장】\n[부칙]\n※ 참고사항"
    cleaned = clean_html_text(text)
    assert "【제1장】" in cleaned
    assert "[부칙]" in cleaned
    assert "※ 참고사항" in cleaned
    assert len(cleaned.split("\n")) == 3
