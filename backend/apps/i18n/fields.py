from django.db import models


class I18nJSONField(models.JSONField):
    """Multilingual JSON field: {"ko": "", "zh": "", "en": "", "ja": ""}."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("default", dict)
        super().__init__(*args, **kwargs)


def resolve_i18n(value, lang="ko"):
    if not isinstance(value, dict):
        return value or ""
    return value.get(lang) or value.get("ko") or next(iter(value.values()), "")
