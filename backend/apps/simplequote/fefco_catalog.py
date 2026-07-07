"""FEFCO 标准盒型库（分类 + 盒型模板元数据）。"""

FEFCO_CATEGORIES = [
    {
        "code": "0200",
        "name_key": "fefcoCat0200",
        "desc_key": "fefcoCat0200Desc",
        "sort_order": 20,
    },
    {
        "code": "0400",
        "name_key": "fefcoCat0400",
        "desc_key": "fefcoCat0400Desc",
        "sort_order": 40,
    },
    {
        "code": "0700",
        "name_key": "fefcoCat0700",
        "desc_key": "fefcoCat0700Desc",
        "sort_order": 70,
    },
]

FEFCO_BOX_TEMPLATES = [
    {
        "code": "0201",
        "category_code": "0200",
        "name_key": "fefcoBox0201",
        "desc_key": "fefcoBox0201Desc",
        "algorithm_key": "slotted_rsc",
        "priority": "P0",
        "quote_enabled": True,
        "preview_enabled": True,
        "inputs": ["length_mm", "width_mm", "height_mm", "thickness_mm"],
        "sort_order": 1,
    },
    {
        "code": "0427",
        "category_code": "0400",
        "name_key": "fefcoBox0427",
        "desc_key": "fefcoBox0427Desc",
        "algorithm_key": "mailer_folder",
        "priority": "P0",
        "quote_enabled": True,
        "preview_enabled": True,
        "inputs": ["length_mm", "width_mm", "height_mm", "thickness_mm"],
        "sort_order": 2,
    },
    {
        "code": "0713",
        "category_code": "0700",
        "name_key": "fefcoBox0713",
        "desc_key": "fefcoBox0713Desc",
        "algorithm_key": "tuck_end",
        "priority": "P0",
        "quote_enabled": True,
        "preview_enabled": True,
        "inputs": ["length_mm", "width_mm", "height_mm", "thickness_mm"],
        "sort_order": 3,
    },
    {
        "code": "0716",
        "category_code": "0700",
        "name_key": "fefcoBox0716",
        "desc_key": "fefcoBox0716Desc",
        "algorithm_key": "auto_lock_bottom",
        "priority": "P0",
        "quote_enabled": True,
        "preview_enabled": True,
        "inputs": ["length_mm", "width_mm", "height_mm", "thickness_mm"],
        "sort_order": 4,
    },
]

_BOX_BY_CODE = {item["code"]: item for item in FEFCO_BOX_TEMPLATES}


def get_box_template(box_code):
    return _BOX_BY_CODE.get(str(box_code or "").strip())


def build_fefco_catalog():
    templates = sorted(FEFCO_BOX_TEMPLATES, key=lambda item: item["sort_order"])
    by_category = {}
    for template in templates:
        by_category.setdefault(template["category_code"], []).append(template)
    category_codes = set(by_category.keys())
    categories = sorted(
        [c for c in FEFCO_CATEGORIES if c["code"] in category_codes],
        key=lambda item: item["sort_order"],
    )
    return {
        "categories": categories,
        "templates": templates,
        "by_category": by_category,
    }
