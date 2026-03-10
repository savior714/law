import sys
import re
from bs4 import BeautifulSoup
# Mocking dependencies for unit test
def clean_html_text(txt): return ' '.join(txt.split())

# Pasting the extraction logic from scourt_precedent.py
def _extract_section_html(html: str, markers: str | list[str]) -> str | None:
    if not html: return None
    soup = BeautifulSoup(html, 'lxml')
    full = clean_html_text(soup.get_text('\n'))
    if isinstance(markers, str): markers = [markers]
    for marker in markers:
        spaced_marker = '\\s*'.join(list(marker))
        patterns = [
            rf'[【\[(]\s*{spaced_marker}\s*[】\])]\s*(.*?)(?=[【\[(][^】\])]+[】\])]|$)',
            rf'(?:^|\n)\s*{spaced_marker}\s*(?::|\n)\s*(.*?)(?=\n\s*(?:【|\[|[가-하]\.|\d+\.|$))',
        ]
        for pat in patterns:
            m = re.search(pat, full, re.IGNORECASE | re.DOTALL)
            if m:
                content = m.group(1).strip()
                if content: return content
    return None

# Test cases
test_html_1 = '''
<div>
  【 판시사항 】
  피고인의 행위가 정당방위에 해당하는지 여부(적극)
  【 판결요지 】
  이 사건 피고인의 행위는... (중략) ... 정당방위에 해당한다.
  【 전 문 】
  피고인: 홍길동
  내용...
</div>
'''

test_html_2 = '''
<div>
  [결정사항]
  이 사건을 소년부에 송치한다.
  [결정요지]
  피고인이 소년이므로...
  [결정]
  주문과 같이 결정한다.
</div>
'''

print('--- Test 1 (Standard) ---')
print(f'Holding: {_extract_section_html(test_html_1, "판시사항")}')
print(f'Summary: {_extract_section_html(test_html_1, "판결요지")}')

print('\n--- Test 2 (Decision Case) ---')
print(f'Holding: {_extract_section_html(test_html_2, ["판시사항", "결정사항"])}')
print(f'Summary: {_extract_section_html(test_html_2, ["판결요지", "결정요지"])}')
print(f'Decision: {_extract_section_html(test_html_2, ["판결", "결정"])}')