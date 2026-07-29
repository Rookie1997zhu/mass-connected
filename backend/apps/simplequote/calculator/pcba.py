"""PCBA SMT/DIP 计分制加工费计算。"""

from apps.simplequote.calculator.utils import _int, _round4, _to_number


def _calc_sum(inputs, params, items):
    breakdown = []
    total = 0
    for key, label in items:
        include = inputs.get(key, True)
        if include:
            amount = round(params.get(key, 0))
            breakdown.append({"label": label, "amount": amount})
            total += amount
    return {"unit_price": total, "mold_fee": 0, "quantity": 1, "total": total, "breakdown": breakdown}


def _match_score(package, tech, tables):
    scores = (tables or {}).get("component_scores") or []
    pkg = str(package or "").upper().strip()
    tech = str(tech or "smt").lower()
    for row in scores:
        if str(row.get("tech", "")).lower() == tech and str(row.get("package", "")).upper() == pkg:
            return _to_number(row.get("score"), 0), False
    return None, True


def calc_pcba(inputs, params, tables=None):
    """PCBA SMT/DIP 计分制加工费（RMB），展示 KRW。"""
    components = inputs.get("components") or []
    pcb_qty = max(1, _int(inputs.get("pcb_quantity"), 1))
    array_count = max(1, _int(inputs.get("array_count"), 1))

    smt_price = params.get("smt_score_price", 0.01)
    dip_price = params.get("dip_score_price", 0.03)
    default_smt = params.get("default_smt_score", 2)
    default_dip = params.get("default_dip_score", 2)

    smt_total = 0
    dip_total = 0
    line_items = []
    warnings = []

    for comp in components:
        qty = max(1, _int(comp.get("qty"), 1))
        tech = str(comp.get("tech", "smt")).lower()
        package = comp.get("package", "")
        score, used_default = _match_score(package, tech, tables)
        if score is None:
            score = default_smt if tech == "smt" else default_dip
            used_default = True
        if used_default:
            warnings.append(f"{package}({tech}) 使用默认计分 {score}")

        unit_price = smt_price if tech == "smt" else dip_price
        line_fee = score * unit_price * qty
        if tech == "smt":
            smt_total += line_fee
        else:
            dip_total += line_fee
        line_items.append(
            {
                "package": package,
                "tech": tech,
                "qty": qty,
                "score": score,
                "fee_rmb": _round4(line_fee),
            }
        )

    mask_fee = params.get("mask_fee", 150)
    test_fee = params.get("smt_test_fee", 0.3) * pcb_qty
    pack_fee = params.get("packaging_fee", 0.3) * array_count
    fixed_total = mask_fee + test_fee + pack_fee
    process_total = smt_total + dip_total
    total_rmb = _round4(fixed_total + process_total)
    rmb_to_krw = params.get("rmb_to_krw", 226)
    total_krw = round(total_rmb * rmb_to_krw)

    breakdown = [
        {"label": "钢网 / METAL MASK", "amount": round(mask_fee)},
        {"label": "SMT 测试费 / SMT test", "amount": round(test_fee)},
        {"label": "包装费 / Packaging", "amount": round(pack_fee)},
        {"label": "SMT 加工费 / SMT labor", "amount": round(smt_total)},
        {"label": "DIP 加工费 / DIP labor", "amount": round(dip_total)},
    ]

    return {
        "currency": "CNY",
        "pcb_quantity": pcb_qty,
        "array_count": array_count,
        "smt_total_rmb": _round4(smt_total),
        "dip_total_rmb": _round4(dip_total),
        "fixed_total_rmb": _round4(fixed_total),
        "line_items": line_items,
        "warnings": warnings,
        "excludes": ["元器件物料费", "开机费", "小批量工艺费"],
        "rmb_to_krw": rmb_to_krw,
        "total_krw": total_krw,
        "mold_fee": 0,
        "quantity": pcb_qty,
        "total": round(total_rmb),
        "breakdown": breakdown,
    }
