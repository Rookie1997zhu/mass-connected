"""FEFCO 标准盒型库（分类 + 盒型模板元数据）。"""

FEFCO_CATEGORIES = [
    {
        "code": "0100",
        "name_key": "fefcoCat0100",
        "desc_key": "fefcoCat0100Desc",
        "sort_order": 10,
    },
    {
        "code": "0200",
        "name_key": "fefcoCat0200",
        "desc_key": "fefcoCat0200Desc",
        "sort_order": 20,
    },
    {
        "code": "0300",
        "name_key": "fefcoCat0300",
        "desc_key": "fefcoCat0300Desc",
        "sort_order": 30,
    },
    {
        "code": "0400",
        "name_key": "fefcoCat0400",
        "desc_key": "fefcoCat0400Desc",
        "sort_order": 40,
    },
    {
        "code": "0500",
        "name_key": "fefcoCat0500",
        "desc_key": "fefcoCat0500Desc",
        "sort_order": 50,
    },
    {
        "code": "0600",
        "name_key": "fefcoCat0600",
        "desc_key": "fefcoCat0600Desc",
        "sort_order": 60,
    },
    {
        "code": "0700",
        "name_key": "fefcoCat0700",
        "desc_key": "fefcoCat0700Desc",
        "sort_order": 70,
    },
    {
        "code": "0800",
        "name_key": "fefcoCat0800",
        "desc_key": "fefcoCat0800Desc",
        "sort_order": 80,
    },
    {
        "code": "0900",
        "name_key": "fefcoCat0900",
        "desc_key": "fefcoCat0900Desc",
        "sort_order": 90,
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
    {
        "code": "0301",
        "category_code": "0300",
        "name_key": "fefcoBox0301",
        "desc_key": "fefcoBox0301Desc",
        "algorithm_key": "telescope",
        "priority": "P1",
        "quote_enabled": False,
        "preview_enabled": False,
        "inputs": ["length_mm", "width_mm", "height_mm", "thickness_mm"],
        "sort_order": 5,
    },
    {
        "code": "0501",
        "category_code": "0500",
        "name_key": "fefcoBox0501",
        "desc_key": "fefcoBox0501Desc",
        "algorithm_key": "slide_sleeve",
        "priority": "P1",
        "quote_enabled": False,
        "preview_enabled": False,
        "inputs": ["length_mm", "width_mm", "height_mm", "thickness_mm"],
        "sort_order": 6,
    },
    {
        "code": "0502",
        "category_code": "0500",
        "name_key": "fefcoBox0502",
        "desc_key": "fefcoBox0502Desc",
        "algorithm_key": "slide_drawer",
        "priority": "P1",
        "quote_enabled": False,
        "preview_enabled": False,
        "inputs": ["length_mm", "width_mm", "height_mm", "thickness_mm"],
        "sort_order": 7,
    },
    {
        "code": "0904",
        "category_code": "0900",
        "name_key": "fefcoBox0904",
        "desc_key": "fefcoBox0904Desc",
        "algorithm_key": "cross_partition",
        "priority": "P1",
        "quote_enabled": False,
        "preview_enabled": False,
        "inputs": ["length_mm", "width_mm", "height_mm", "thickness_mm"],
        "sort_order": 8,
    },
]

_BOX_BY_CODE = {item["code"]: item for item in FEFCO_BOX_TEMPLATES}


def get_box_template(box_code):
    return _BOX_BY_CODE.get(str(box_code or "").strip())


def build_fefco_catalog():
    categories = sorted(FEFCO_CATEGORIES, key=lambda item: item["sort_order"])
    templates = sorted(FEFCO_BOX_TEMPLATES, key=lambda item: item["sort_order"])
    by_category = {}
    for template in templates:
        by_category.setdefault(template["category_code"], []).append(template)
    return {
        "categories": categories,
        "templates": templates,
        "by_category": by_category,
    }
