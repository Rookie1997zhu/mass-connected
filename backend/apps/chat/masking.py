import re

# 联系方式脱敏：软提示场景下替换展示正文，原文另行保存供纠纷审计
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{3,4}[\s-]?\d{4}(?!\d)"
)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_URL_RE = re.compile(r"https?://[^\s]+|www\.[^\s]+", re.IGNORECASE)
_IM_RE = re.compile(
    r"(?:微信|wechat|wx|카카오|kakao|kakaotalk|텔레그램|telegram|whatsapp|line)\s*[:：]?\s*[A-Za-z0-9_\-.]{3,}",
    re.IGNORECASE,
)

MASK = "***"


def mask_contact_info(text: str) -> tuple[str, bool]:
    """返回 (脱敏正文, 是否触发脱敏)。"""
    if not text:
        return "", False
    original = text
    masked = _EMAIL_RE.sub(MASK, original)
    masked = _URL_RE.sub(MASK, masked)
    masked = _IM_RE.sub(MASK, masked)
    masked = _PHONE_RE.sub(MASK, masked)
    return masked, masked != original
