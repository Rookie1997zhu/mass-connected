"""本地轻量校验 Markdown → HTML（无需 Django）。"""

from markdown_html import markdown_to_html


def test_markdown_basic():
    html = markdown_to_html("# 标题\n\n段落 **粗**\n\n- a\n- b")
    assert "<h1>" in html
    assert "<strong>粗</strong>" in html
    assert "<li>a</li>" in html


if __name__ == "__main__":
    test_markdown_basic()
    print("ok")
