from law.utils.text import clean_html_text

text = """
    제1조(목적)
    이 법은 ...
    ① 이 항은 ...
    1. 이 호는 ...
    가. 이 목은 ...
"""
cleaned = clean_html_text(text)
print("Cleaned text output:")
print("-" * 20)
print(cleaned)
print("-" * 20)
print(f"Lines count: {len(cleaned.split("\n"))}")
for i, line in enumerate(cleaned.split("\n")):
    print(f"Line {i}: {repr(line)}")
