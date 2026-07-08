import math
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

def _require_ezdxf():
    try:
        import ezdxf
    except ImportError as exc:
        raise DielineImportError("DXF 解析依赖未安装，请重建 backend 镜像或执行 pip install ezdxf") from exc
    return ezdxf


def _require_shapely_linestring():
    try:
        from shapely.geometry import LineString
    except ImportError as exc:
        raise DielineImportError("几何依赖未安装，请重建 backend 镜像或执行 pip install shapely") from exc
    return LineString


def _require_svgpathtools():
    try:
        from svgpathtools import Line, parse_path
    except ImportError as exc:
        raise DielineImportError("SVG 解析依赖未安装，请重建 backend 镜像或执行 pip install svgpathtools") from exc
    return Line, parse_path


SUPPORTED_PARSE_FORMATS = {"dxf", "svg"}
ATTACHMENT_ONLY_FORMATS = {"ai", "pdf"}
LINE_ROLE_DEFAULT = "cut"

ROLE_KEYWORDS = {
    "cut": ("cut", "knife", "die", "dieline", "trim", "outline", "contour", "刀", "割", "切"),
    "crease": ("crease", "fold", "score", "creasing", "折", "压", "壓", "摺"),
    "bleed": ("bleed", "safe", "margin", "出血"),
    "dimension": ("dim", "dimension", "measure", "尺寸", "标注", "標註"),
    "ignore": ("ignore", "hidden", "note", "text", "annotation", "辅助", "輔助"),
}

COLOR_ROLE_MAP = {
    "blue": "cut",
    "#0000ff": "cut",
    "#2563eb": "cut",
    "rgb(0,0,255)": "cut",
    "rgb(0, 0, 255)": "cut",
    "red": "crease",
    "#ff0000": "crease",
    "#ef4444": "crease",
    "rgb(255,0,0)": "crease",
    "rgb(255, 0, 0)": "crease",
    "green": "bleed",
    "#00ff00": "bleed",
    "#22c55e": "bleed",
    "rgb(0,255,0)": "bleed",
    "rgb(0, 255, 0)": "bleed",
}

DXF_COLOR_ROLE_MAP = {
    "1": "crease",  # red
    "3": "bleed",   # green
    "5": "cut",     # blue
}


class DielineImportError(ValueError):
    pass


def source_format_from_name(name):
    suffix = Path(name or "").suffix.lower().lstrip(".")
    return suffix


def _entity_id(prefix, index):
    return f"{prefix}_{index:05d}"


def _line_bbox(x1, y1, x2, y2):
    return {
        "min_x": min(x1, x2),
        "min_y": min(y1, y2),
        "max_x": max(x1, x2),
        "max_y": max(y1, y2),
    }


def _merge_bbox(current, bbox):
    if not current:
        return dict(bbox)
    return {
        "min_x": min(current["min_x"], bbox["min_x"]),
        "min_y": min(current["min_y"], bbox["min_y"]),
        "max_x": max(current["max_x"], bbox["max_x"]),
        "max_y": max(current["max_y"], bbox["max_y"]),
    }


def _normalize_token(value):
    return str(value or "").strip().lower().replace(" ", "")


def _role_from_keywords(value):
    text = str(value or "").lower()
    for role, keywords in ROLE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return role
    return None


def _hex_to_rgb(token):
    match = re.fullmatch(r"#?([0-9a-f]{3}|[0-9a-f]{6})", token or "")
    if not match:
        return None
    value = match.group(1)
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def _role_from_color(color):
    """把颜色映射为线型；支持标准色名、精确 hex 与近似主色判断。"""
    token = _normalize_token(color)
    if not token or token == "none":
        return None
    if token in COLOR_ROLE_MAP:
        return COLOR_ROLE_MAP[token]
    if token in DXF_COLOR_ROLE_MAP:
        return DXF_COLOR_ROLE_MAP[token]
    rgb = _hex_to_rgb(token)
    if not rgb:
        return None
    red, green, blue = rgb
    high, low = max(rgb), min(rgb)
    if high - low < 40:
        # 近似黑/白/灰：无法据颜色判定线型
        return None
    if red == high:
        return "crease"  # 红 → 压折线
    if blue == high:
        return "cut"  # 蓝 → 割线
    if green == high:
        return "bleed"  # 绿 → 出血线
    return None


def _is_zero_width(stroke_width):
    token = _normalize_token(stroke_width).rstrip("px").rstrip("pt")
    if not token:
        return False
    try:
        return float(token) <= 0
    except ValueError:
        return False


def _infer_line_role(layer="", color="", linetype="", stroke_width=""):
    role = _role_from_keywords(layer)
    if role:
        return role, 0.96, f"layer:{layer}"

    role = _role_from_keywords(linetype)
    if role:
        return role, 0.9, f"linetype:{linetype}"

    if _is_zero_width(stroke_width):
        return "ignore", 0.8, f"stroke-width:{stroke_width}"

    linetype_token = _normalize_token(linetype)
    if linetype_token and any(token in linetype_token for token in ("dash", "dashed", "hidden", "center")):
        return "crease", 0.78, f"linetype:{linetype}"

    role = _role_from_color(color)
    if role:
        return role, 0.86, f"color:{color}"

    return LINE_ROLE_DEFAULT, 0.45, "default"


def _segment(entity_id, x1, y1, x2, y2, role=None, layer="", color="", linetype="", stroke_width=""):
    LineString = _require_shapely_linestring()
    geom = LineString([(float(x1), float(y1)), (float(x2), float(y2))])
    inferred_role, confidence, reason = _infer_line_role(
        layer=layer, color=color, linetype=linetype, stroke_width=stroke_width
    )
    final_role = role or inferred_role
    return {
        "entity_id": entity_id,
        "type": "line",
        "role": final_role,
        "role_confidence": 1.0 if role else confidence,
        "role_reason": "explicit" if role else reason,
        "x1": round(float(x1), 4),
        "y1": round(float(y1), 4),
        "x2": round(float(x2), 4),
        "y2": round(float(y2), 4),
        "length": round(float(geom.length), 4),
        "layer": layer or "",
        "color": str(color or ""),
        "linetype": linetype or "",
        "bbox": _line_bbox(float(x1), float(y1), float(x2), float(y2)),
    }


def _geometry_payload(source_format, entities):
    bbox = {}
    for item in entities:
        bbox = _merge_bbox(bbox, item["bbox"])
    bbox = bbox or {"min_x": 0, "min_y": 0, "max_x": 0, "max_y": 0}
    return {
        "schema_version": 1,
        "source_format": source_format,
        "unit": "mm",
        "bbox": bbox,
        "width": round(bbox["max_x"] - bbox["min_x"], 4),
        "height": round(bbox["max_y"] - bbox["min_y"], 4),
        "entities": entities,
    }


def parse_dxf(path):
    ezdxf = _require_ezdxf()
    try:
        doc = ezdxf.readfile(path)
    except Exception as exc:
        raise DielineImportError(f"DXF 解析失败：{exc}") from exc

    entities = []
    index = 1
    for entity in doc.modelspace():
        kind = entity.dxftype()
        layer = entity.dxf.layer if entity.dxf.hasattr("layer") else ""
        color = entity.dxf.color if entity.dxf.hasattr("color") else ""
        linetype = entity.dxf.linetype if entity.dxf.hasattr("linetype") else ""
        if kind == "LINE":
            start = entity.dxf.start
            end = entity.dxf.end
            entities.append(_segment(_entity_id("dxf", index), start.x, start.y, end.x, end.y, layer=layer, color=color, linetype=linetype))
            index += 1
        elif kind in {"LWPOLYLINE", "POLYLINE"}:
            points = []
            try:
                points = [(point[0], point[1]) for point in entity.get_points()]
            except AttributeError:
                points = [(vertex.dxf.location.x, vertex.dxf.location.y) for vertex in entity.vertices]
            for start, end in zip(points, points[1:]):
                entities.append(_segment(_entity_id("dxf", index), start[0], start[1], end[0], end[1], layer=layer, color=color, linetype=linetype))
                index += 1
            if getattr(entity, "closed", False) and len(points) > 2:
                start, end = points[-1], points[0]
                entities.append(_segment(_entity_id("dxf", index), start[0], start[1], end[0], end[1], layer=layer, color=color, linetype=linetype))
                index += 1
    if not entities:
        raise DielineImportError("DXF 中没有可解析的 LINE/POLYLINE 线段")
    return _geometry_payload("dxf", entities)


def _float_attr(node, name, default=0):
    try:
        return float(node.attrib.get(name, default))
    except (TypeError, ValueError):
        return float(default)


def _parse_points(value):
    cleaned = (value or "").replace(",", " ").split()
    points = []
    for index in range(0, len(cleaned) - 1, 2):
        try:
            points.append((float(cleaned[index]), float(cleaned[index + 1])))
        except ValueError:
            continue
    return points


def _tag(node):
    return node.tag.split("}", 1)[-1].lower()


def _parse_style(style):
    result = {}
    for part in (style or "").split(";"):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        result[key.strip()] = value.strip()
    return result


def _parse_svg_styles(root):
    """解析 SVG 内 <style> 的 CSS 类，返回 {class_name: {prop: value}}。"""
    class_styles = {}
    for node in root.iter():
        if _tag(node) != "style" or not node.text:
            continue
        for selectors, body in re.findall(r"([^{}]+)\{([^}]*)\}", node.text):
            props = _parse_style(body)
            for selector in selectors.split(","):
                selector = selector.strip()
                if selector.startswith("."):
                    bucket = class_styles.setdefault(selector[1:], {})
                    bucket.update({k: v for k, v in props.items() if v})
    return class_styles


def _svg_meta(node, inherited=None, class_styles=None):
    inherited = inherited or {}
    class_styles = class_styles or {}
    style = _parse_style(node.attrib.get("style", ""))
    class_stroke = ""
    class_dash = ""
    class_width = ""
    for cls in (node.attrib.get("class", "") or "").split():
        bucket = class_styles.get(cls)
        if not bucket:
            continue
        class_stroke = bucket.get("stroke", class_stroke) or class_stroke
        class_dash = bucket.get("stroke-dasharray", class_dash) or class_dash
        class_width = bucket.get("stroke-width", class_width) or class_width
    return {
        "stroke": node.attrib.get("stroke") or style.get("stroke") or class_stroke or inherited.get("stroke", ""),
        "linetype": node.attrib.get("stroke-dasharray") or style.get("stroke-dasharray") or class_dash or inherited.get("linetype", ""),
        "stroke_width": node.attrib.get("stroke-width") or style.get("stroke-width") or class_width or inherited.get("stroke_width", ""),
        "layer": node.attrib.get("id") or node.attrib.get("class") or inherited.get("layer", ""),
    }


def parse_svg(path):
    Line, parse_path = _require_svgpathtools()
    try:
        root = ET.parse(path).getroot()
    except Exception as exc:
        raise DielineImportError(f"SVG 解析失败：{exc}") from exc

    class_styles = _parse_svg_styles(root)
    entities = []
    index = 1

    def walk(node, inherited=None):
        nonlocal index
        meta = _svg_meta(node, inherited, class_styles)
        tag = _tag(node)
        layer = meta["layer"]
        color = meta["stroke"]
        linetype = meta["linetype"]
        stroke_width = meta["stroke_width"]
        if tag == "line":
            entities.append(_segment(_entity_id("svg", index), _float_attr(node, "x1"), _float_attr(node, "y1"), _float_attr(node, "x2"), _float_attr(node, "y2"), layer=layer, color=color, linetype=linetype, stroke_width=stroke_width))
            index += 1
        elif tag in {"polyline", "polygon"}:
            points = _parse_points(node.attrib.get("points"))
            pairs = list(zip(points, points[1:]))
            if tag == "polygon" and len(points) > 2:
                pairs.append((points[-1], points[0]))
            for start, end in pairs:
                entities.append(_segment(_entity_id("svg", index), start[0], start[1], end[0], end[1], layer=layer, color=color, linetype=linetype, stroke_width=stroke_width))
                index += 1
        elif tag == "path" and node.attrib.get("d"):
            try:
                path_data = parse_path(node.attrib["d"])
            except Exception:
                path_data = []
            for piece in path_data:
                if isinstance(piece, Line):
                    entities.append(_segment(_entity_id("svg", index), piece.start.real, piece.start.imag, piece.end.real, piece.end.imag, layer=layer, color=color, linetype=linetype, stroke_width=stroke_width))
                    index += 1
                else:
                    steps = max(4, min(24, math.ceil(piece.length(error=1e-3) / 25)))
                    prev = piece.point(0)
                    for step in range(1, steps + 1):
                        current = piece.point(step / steps)
                        entities.append(_segment(_entity_id("svg", index), prev.real, prev.imag, current.real, current.imag, layer=layer, color=color, linetype=linetype, stroke_width=stroke_width))
                        index += 1
                        prev = current
        for child in list(node):
            walk(child, meta)

    walk(root)
    if not entities:
        raise DielineImportError("SVG 中没有可解析的 line/polyline/path 线段")
    return _geometry_payload("svg", entities)


def parse_uploaded_dieline(upload, source_format):
    source_format = (source_format or "").lower()
    if source_format in ATTACHMENT_ONLY_FORMATS:
        raise DielineImportError("AI/PDF 可保存为附件，但需要 DXF/SVG 才能参数化解析")
    if source_format not in SUPPORTED_PARSE_FORMATS:
        raise DielineImportError("仅支持 DXF/SVG 参数化解析")

    suffix = f".{source_format}"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            for chunk in upload.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name
        if source_format == "dxf":
            return parse_dxf(tmp_path)
        return parse_svg(tmp_path)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def default_mapping_schema(parsed_geometry, base_dimensions):
    entity_roles = {
        entity["entity_id"]: entity.get("role", LINE_ROLE_DEFAULT)
        for entity in parsed_geometry.get("entities", [])
    }
    bbox = parsed_geometry.get("bbox") or {}
    return {
        "schema_version": 1,
        "mapping_mode": "orthogonal_scale",
        "base_dimensions": base_dimensions or {},
        "dimension_refs": {
            "length": {"axis": "x", "from": bbox.get("min_x", 0), "to": bbox.get("max_x", 0)},
            "height": {"axis": "y", "from": bbox.get("min_y", 0), "to": bbox.get("max_y", 0)},
        },
        "entity_roles": entity_roles,
        "transform_rules": {"x": "length", "y": "height"},
    }


def render_parametric_dieline(asset, dimensions):
    parsed = asset.parsed_geometry or {}
    mapping = asset.mapping_schema or {}
    base = mapping.get("base_dimensions") or asset.base_dimensions or {}
    entities = parsed.get("entities") or []
    if not entities:
        raise DielineImportError("资产没有可重算的解析线段")

    base_length = float(base.get("length") or parsed.get("width") or 1)
    base_height = float(base.get("height") or parsed.get("height") or 1)
    target_length = float(dimensions.get("length") or base_length)
    target_height = float(dimensions.get("height") or base_height)
    bbox = parsed.get("bbox") or {"min_x": 0, "min_y": 0}
    origin_x = float(bbox.get("min_x", 0))
    origin_y = float(bbox.get("min_y", 0))
    scale_x = target_length / base_length if base_length else 1
    scale_y = target_height / base_height if base_height else 1
    entity_roles = mapping.get("entity_roles") or {}

    result = []
    for entity in entities:
        role = entity_roles.get(entity["entity_id"], entity.get("role", LINE_ROLE_DEFAULT))
        if role == "ignore":
            continue
        x1 = origin_x + (float(entity["x1"]) - origin_x) * scale_x
        y1 = origin_y + (float(entity["y1"]) - origin_y) * scale_y
        x2 = origin_x + (float(entity["x2"]) - origin_x) * scale_x
        y2 = origin_y + (float(entity["y2"]) - origin_y) * scale_y
        result.append(_segment(entity["entity_id"], x1, y1, x2, y2, role=role, layer=entity.get("layer", ""), color=entity.get("color", ""), linetype=entity.get("linetype", "")))

    geometry = _geometry_payload(parsed.get("source_format", asset.source_format), result)
    geometry["base_dimensions"] = base
    geometry["target_dimensions"] = dimensions
    geometry["area_m2"] = round((geometry["width"] * geometry["height"]) / 1_000_000, 6)
    return geometry
