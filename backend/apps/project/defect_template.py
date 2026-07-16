"""不良报告 Word 模板（正式版 docx）。"""

from pathlib import Path

_TEMPLATE_PATH = Path(__file__).resolve().parent / "assets" / "defect_report_template.docx"


def get_defect_report_template_path() -> Path:
    if not _TEMPLATE_PATH.is_file():
        raise FileNotFoundError(f"defect report template missing: {_TEMPLATE_PATH}")
    return _TEMPLATE_PATH


def read_defect_report_template_bytes() -> bytes:
    return get_defect_report_template_path().read_bytes()
