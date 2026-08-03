"""STP/STEP 几何解析服务（基于 OpenCASCADE / cadquery-ocp）。

阶段 A：由 3D 文件计算体积、包围盒、表面积，供报价表单回填重量与尺寸。
阶段 B：倒扣(undercut)启发式分析，推断主拔模方向与滑块建议数（建议值，需人工确认）。
阶段 C：基于几何特征的低置信度材料推荐。
解析在独立进程中执行并设超时，避免坏文件拖垮请求。
"""

import base64
import multiprocessing as mp
import os
import tempfile
import time
from datetime import datetime, timezone
from queue import Empty

PARSE_TIMEOUT_SEC = 20
# 预览网格三角化精度（mm）；越大网格越粗、响应越小
PREVIEW_MESH_DEFLECTION = 0.8
# STL 二进制上限（约 8MB），超出则降级或跳过
PREVIEW_MESH_MAX_BYTES = 8 * 1024 * 1024

# 残余倒扣面积占比超过该值才建议加滑块（低于视为解析噪声/圆角）
UNDERCUT_AREA_RATIO_MIN = 0.02
# 侧向面判定：|法向·拔模轴| 小于该值视为与拔模轴近似垂直（侧壁）
SIDE_WALL_DOT_MAX = 0.5
# 面数超过该值时对面做面积降采样（不再直接 skip）
UNDERCUT_MAX_FACES_SOFT = 800
# 倒扣射线总预算（采样点 × 2 方向 × 3 轴）
UNDERCUT_RAY_BUDGET = 60000
UNDERCUT_FACE_SAMPLE_MAX = 9
UNDERCUT_FACE_SAMPLE_MIN = 1
# 空间聚类：倒扣采样点质心距离阈值 = 对角线 × 该比例
UNDERCUT_CLUSTER_DIST_RATIO = 0.15
# 拔模轴 tie-break：倒扣面积相差在该比例内视为接近
UNDERCUT_AXIS_TIE_RATIO = 0.05
# 倒扣分析 wall-clock 软预算（秒）：射线求交对全模型求交，曲面复杂件开销高，
# 到点即用已处理采样点提前收敛，保证整体解析不触发子进程超时。
UNDERCUT_TIME_BUDGET_SEC = 8.0

# 3 个主拔模轴（作为「轴」使用，两个模仁分别沿 ±轴 开模）
_DRAW_AXES = [
    ("X", (1.0, 0.0, 0.0)),
    ("Y", (0.0, 1.0, 0.0)),
    ("Z", (0.0, 0.0, 1.0)),
]


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _face_props(face):
    """返回单个面的（质心, 外法向单位向量, 面积）；失败返回 None。"""
    samples = _sample_face(face, grid_n=1)
    if not samples:
        return None
    point, normal, weight = samples[0]
    total = sum(s[2] for s in samples) or weight
    return (point, normal, total)


def _grid_n_from_pts(pts_per_face):
    pts_per_face = max(UNDERCUT_FACE_SAMPLE_MIN, min(UNDERCUT_FACE_SAMPLE_MAX, int(pts_per_face)))
    if pts_per_face >= 9:
        return 3
    if pts_per_face >= 4:
        return 2
    return 1


def _undercut_sampling_plan(face_count):
    """按射线预算计算每面采样网格与是否降采样。"""
    face_count = max(1, int(face_count))
    pts = UNDERCUT_RAY_BUDGET // (face_count * 6)
    pts = max(UNDERCUT_FACE_SAMPLE_MIN, min(UNDERCUT_FACE_SAMPLE_MAX, pts))
    grid_n = _grid_n_from_pts(pts)
    pts_per_face = grid_n * grid_n
    downsampled = face_count > UNDERCUT_MAX_FACES_SOFT
    if downsampled:
        # 高面数件：仅保留大面积面 + 单点采样，确保在解析子进程预算内
        grid_n = 1
        pts_per_face = 1
        budget_faces = max(1, UNDERCUT_RAY_BUDGET // (pts_per_face * 6))
        max_faces = min(face_count, UNDERCUT_MAX_FACES_SOFT, budget_faces)
    else:
        max_faces = face_count
    if pts_per_face < UNDERCUT_FACE_SAMPLE_MAX:
        downsampled = True
    return {
        "grid_n": grid_n,
        "pts_per_face": pts_per_face,
        "max_faces": max_faces,
        "downsampled": downsampled,
    }


def _sample_face(face, grid_n=1):
    """在面 UV 网格上采样，返回 [(point_xyz, normal_xyz, weight), ...]。"""
    from OCP.BRep import BRep_Tool
    from OCP.BRepClass import BRepClass_FaceClassifier
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.GeomLProp import GeomLProp_SLProps
    from OCP.TopAbs import TopAbs_IN, TopAbs_ON, TopAbs_REVERSED
    from OCP.BRepTools import BRepTools
    from OCP.gp import gp_Pnt2d

    surface = BRep_Tool.Surface_s(face)
    if surface is None:
        return []
    umin, umax, vmin, vmax = BRepTools.UVBounds_s(face)
    if umax <= umin or vmax <= vmin:
        return []

    fprops = GProp_GProps()
    BRepGProp.SurfaceProperties_s(face, fprops)
    face_area = fprops.Mass()
    if face_area <= 0:
        return []

    grid_n = max(1, min(3, int(grid_n)))
    classifier = BRepClass_FaceClassifier()
    samples = []
    for i in range(grid_n):
        for j in range(grid_n):
            u = umin + (i + 0.5) * (umax - umin) / grid_n
            v = vmin + (j + 0.5) * (vmax - vmin) / grid_n
            classifier.Perform(face, gp_Pnt2d(u, v), 1e-6)
            state = classifier.State()
            if state not in (TopAbs_IN, TopAbs_ON):
                continue
            props = GeomLProp_SLProps(surface, u, v, 1, 1e-6)
            if not props.IsNormalDefined():
                continue
            n = props.Normal()
            nx, ny, nz = n.X(), n.Y(), n.Z()
            if face.Orientation() == TopAbs_REVERSED:
                nx, ny, nz = -nx, -ny, -nz
            p = props.Value()
            samples.append(((p.X(), p.Y(), p.Z()), (nx, ny, nz), 0.0))

    if not samples:
        return []

    weight = face_area / len(samples)
    return [(pt, n, weight) for pt, n, _ in samples]


def _collect_face_samples(shape, plan):
    """收集待分析面及其采样点（大面积面优先，可降采样）。"""
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps

    face_entries = []
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = TopoDS.Face_s(explorer.Current())
        fprops = GProp_GProps()
        BRepGProp.SurfaceProperties_s(face, fprops)
        area = fprops.Mass()
        if area > 0:
            face_entries.append((face, area))
        explorer.Next()

    if not face_entries:
        return [], 0.0

    face_entries.sort(key=lambda item: item[1], reverse=True)
    selected = face_entries[: plan["max_faces"]]
    total_area = sum(item[1] for item in face_entries)

    all_samples = []
    for face, area in selected:
        for point, normal, weight in _sample_face(face, plan["grid_n"]):
            all_samples.append((point, normal, weight))

    return all_samples, total_area


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _axis_vec(name):
    for label, vec in _DRAW_AXES:
        if label == name:
            return vec
    return (0.0, 0.0, 1.0)


def _side_direction_key(normal, draw_axis_name):
    """倒扣侧向分组键（排除与拔模轴平行的分量）。"""
    nx, ny, nz = normal
    if draw_axis_name == "X":
        nx = 0.0
    elif draw_axis_name == "Y":
        ny = 0.0
    else:
        nz = 0.0
    length = (nx * nx + ny * ny + nz * nz) ** 0.5
    if length < 1e-6:
        return None
    nx, ny, nz = nx / length, ny / length, nz / length
    parts = []
    if abs(nx) > 0.3:
        parts.append("x+" if nx > 0 else "x-")
    if abs(ny) > 0.3:
        parts.append("y+" if ny > 0 else "y-")
    if abs(nz) > 0.3:
        parts.append("z+" if nz > 0 else "z-")
    return "+".join(parts) if parts else None


def _cluster_sliders_spatial(undercut_samples, diag, draw_axis_name, total_area):
    """方向分组 + 空间位置聚类，返回 (slider_count, clusters)。"""
    if not undercut_samples:
        return 0, []

    axis = _axis_vec(draw_axis_name)
    cluster_dist = max(diag * UNDERCUT_CLUSTER_DIST_RATIO, 1e-3)
    groups = {}
    for point, normal, weight in undercut_samples:
        if abs(_dot(normal, axis)) >= SIDE_WALL_DOT_MAX:
            continue
        key = _side_direction_key(normal, draw_axis_name)
        if not key:
            continue
        groups.setdefault(key, []).append((point, normal, weight))

    clusters = []
    for side_key, items in groups.items():
        remaining = list(items)
        while remaining:
            seed = remaining.pop(0)
            cluster_pts = [seed]
            i = 0
            while i < len(remaining):
                cand = remaining[i]
                dx = cand[0][0] - seed[0][0]
                dy = cand[0][1] - seed[0][1]
                dz = cand[0][2] - seed[0][2]
                if (dx * dx + dy * dy + dz * dz) ** 0.5 <= cluster_dist:
                    cluster_pts.append(cand)
                    remaining.pop(i)
                else:
                    i += 1
            area_sum = sum(p[2] for p in cluster_pts)
            cx = sum(p[0][0] * p[2] for p in cluster_pts) / max(area_sum, 1e-9)
            cy = sum(p[0][1] * p[2] for p in cluster_pts) / max(area_sum, 1e-9)
            cz = sum(p[0][2] * p[2] for p in cluster_pts) / max(area_sum, 1e-9)
            clusters.append(
                {
                    "axis_side": side_key,
                    "centroid": [round(cx, 2), round(cy, 2), round(cz, 2)],
                    "area_ratio": round(area_sum / total_area, 4) if total_area else 0.0,
                }
            )

    return len(clusters), clusters


def _confidence_level(ratio, downsampled, cluster_count, sample_count):
    if downsampled:
        return "low"
    if ratio >= 0.1 and cluster_count <= 4 and sample_count >= 20:
        return "high"
    if ratio >= UNDERCUT_AREA_RATIO_MIN:
        return "medium"
    return "medium"


def analyze_undercut(shape):
    """基于多点采样 + 遮挡检测的倒扣分析（建议值，需人工确认）。"""
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.gp import gp_Lin, gp_Pnt, gp_Dir

    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    face_count = 0
    while explorer.More():
        face_count += 1
        explorer.Next()

    if face_count <= 0:
        return None

    plan = _undercut_sampling_plan(face_count)
    samples, total_area = _collect_face_samples(shape, plan)
    if not samples or total_area <= 0:
        return None

    box = Bnd_Box()
    BRepBndLib.Add_s(shape, box)
    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
    diag = ((xmax - xmin) ** 2 + (ymax - ymin) ** 2 + (zmax - zmin) ** 2) ** 0.5
    if diag <= 0:
        return None
    eps = diag * 1e-4
    ray_len = diag * 2.0

    intersector = IntCurvesFace_ShapeIntersector()
    intersector.Load(shape, 1e-6)

    def _blocked(origin, direction):
        line = gp_Lin(gp_Pnt(*origin), gp_Dir(*direction))
        intersector.Perform(line, eps, ray_len)
        return intersector.NbPnt() > 0

    # 单遍采样：每个采样点一次性完成三轴 ±方向遮挡测试，便于时间预算到点即收敛。
    # 射线对全模型求交，复杂曲面开销高，超预算则用已处理采样点估算。
    axis_acc = {
        name: {"undercut_area": 0.0, "undercut_samples": [], "open_area": 0.0}
        for name, _axis in _DRAW_AXES
    }
    deadline = time.monotonic() + UNDERCUT_TIME_BUDGET_SEC
    analyzed_area = 0.0
    processed = 0
    timed_out = False
    for point, normal, weight in samples:
        if time.monotonic() > deadline:
            timed_out = True
            break
        nx, ny, nz = normal
        ox = point[0] + nx * eps
        oy = point[1] + ny * eps
        oz = point[2] + nz * eps
        for name, axis in _DRAW_AXES:
            ax, ay, az = axis
            up_clear = not _blocked((ox, oy, oz), (ax, ay, az))
            down_clear = not _blocked((ox, oy, oz), (-ax, -ay, -az))
            acc = axis_acc[name]
            if abs(_dot(normal, axis)) > 0.7:
                acc["open_area"] += weight
            if not up_clear and not down_clear:
                acc["undercut_area"] += weight
                acc["undercut_samples"].append((point, normal, weight))
        analyzed_area += weight
        processed += 1

    if processed <= 0:
        return None

    axis_results = [
        {"axis": name, **axis_acc[name]} for name, _axis in _DRAW_AXES
    ]
    best = min(axis_results, key=lambda item: item["undercut_area"])
    # tie-break：倒扣面积接近时选开口面积（沿轴投影）更大者
    eps_area = max(best["undercut_area"] * UNDERCUT_AXIS_TIE_RATIO, analyzed_area * 1e-6)
    candidates = [
        item
        for item in axis_results
        if item["undercut_area"] <= best["undercut_area"] + eps_area
    ]
    best = max(candidates, key=lambda item: item["open_area"])

    # 超预算时仅处理了部分采样点，占比基于已分析面积，避免整体面积稀释导致低估
    ratio_base = analyzed_area if timed_out else total_area
    ratio = best["undercut_area"] / ratio_base if ratio_base else 0.0
    if ratio < UNDERCUT_AREA_RATIO_MIN:
        suggested_sliders = 0
        clusters = []
    else:
        suggested_sliders, clusters = _cluster_sliders_spatial(
            best["undercut_samples"], diag, best["axis"], ratio_base
        )

    downsampled = plan["downsampled"] or timed_out
    confidence = _confidence_level(ratio, downsampled, suggested_sliders, processed)

    return {
        "draw_direction": best["axis"],
        "undercut_area_ratio": round(ratio, 4),
        "suggested_sliders": suggested_sliders,
        "confidence": confidence,
        "undercut_clusters": clusters,
        "sampling": {
            "faces_total": face_count,
            "faces_used": min(face_count, plan["max_faces"]),
            "pts_per_face": plan["pts_per_face"],
            "downsampled": downsampled,
            "partial": timed_out,
        },
    }


def _cluster_slider_count(normals):
    """按倒扣面法向的主方向聚类估算滑块数量（粗略：统计显著的独立侧向）。"""
    if not normals:
        return 0
    buckets = set()
    for nx, ny, nz in normals:
        # 归一到主轴方向的符号组合，作为侧向聚类键
        ax = ("x+" if nx > 0.3 else "x-" if nx < -0.3 else "")
        ay = ("y+" if ny > 0.3 else "y-" if ny < -0.3 else "")
        az = ("z+" if nz > 0.3 else "z-" if nz < -0.3 else "")
        key = ax or ay or az
        if key:
            buckets.add(key)
    return max(1, len(buckets))


def export_preview_mesh(shape, linear_deflection=PREVIEW_MESH_DEFLECTION):
    """将 shape 三角化为 STL 并 base64 编码，供前端 3D 预览（best-effort）。"""
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.StlAPI import StlAPI_Writer

    def _try_export(deflection):
        mesh = BRepMesh_IncrementalMesh(shape, deflection, False, deflection, True)
        mesh.Perform()
        if not mesh.IsDone():
            return None, "mesh_failed"
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
                tmp_path = tmp.name
            writer = StlAPI_Writer()
            writer.ASCIIMode = False
            if not writer.Write(shape, tmp_path):
                return None, "stl_write_failed"
            with open(tmp_path, "rb") as fh:
                data = fh.read()
            if not data:
                return None, "empty_stl"
            if len(data) > PREVIEW_MESH_MAX_BYTES:
                return None, "too_large"
            return {
                "format": "stl",
                "encoding": "base64",
                "data": base64.b64encode(data).decode("ascii"),
            }, "ok"
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    try:
        preview_mesh, status = _try_export(linear_deflection)
        if preview_mesh is not None:
            return preview_mesh, status
        # 粗化一次再试
        preview_mesh, status = _try_export(linear_deflection * 2.5)
        if preview_mesh is not None:
            return preview_mesh, "simplified"
        return None, status or "unavailable"
    except Exception:  # noqa: BLE001
        return None, "unavailable"


def recommend_material_by_geometry(volume_cm3, bbox_mm, surface_area_cm2):
    """基于几何特征的低置信度材料推荐（无历史数据时的规则兜底）。

    仅供参考：用表面积/体积作壁厚代理，结合尺寸给出常见材料倾向。
    """
    if not volume_cm3 or volume_cm3 <= 0:
        return None
    # 壁厚代理：体积/表面积（cm），越小越薄壁
    thickness_proxy = None
    if surface_area_cm2 and surface_area_cm2 > 0:
        thickness_proxy = volume_cm3 / surface_area_cm2  # cm
    max_dim = max(bbox_mm) if bbox_mm else 0

    if thickness_proxy is not None and thickness_proxy < 0.15:
        material, reason = "PP", "thin_wall"
    elif max_dim >= 200:
        material, reason = "ABS", "large_part"
    else:
        material, reason = "ABS", "default"

    return {
        "material": material,
        "source": "geometry_rule",
        "confidence": "low",
        "reason": reason,
    }


def _parse_step_sync(path):
    """在子进程中执行的同步解析，返回可序列化 dict。"""
    from OCP.STEPControl import STEPControl_Reader
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib

    reader = STEPControl_Reader()
    if reader.ReadFile(path) != IFSelect_RetDone:
        return {"parse_status": "error", "error": "STEP read failed"}

    reader.TransferRoots()
    shape = reader.OneShape()
    if shape is None or shape.IsNull():
        return {"parse_status": "error", "error": "empty shape"}

    vprops = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, vprops)
    volume_mm3 = vprops.Mass()

    sprops = GProp_GProps()
    BRepGProp.SurfaceProperties_s(shape, sprops)
    area_mm2 = sprops.Mass()

    box = Bnd_Box()
    BRepBndLib.Add_s(shape, box)
    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
    dims = [xmax - xmin, ymax - ymin, zmax - zmin]

    if volume_mm3 <= 0:
        return {"parse_status": "error", "error": "non-positive volume"}

    volume_cm3 = round(volume_mm3 / 1000.0, 4)
    surface_area_cm2 = round(area_mm2 / 100.0, 4)
    bbox_mm = [round(v, 2) for v in dims]

    # 阶段 B/C：best-effort，异常不影响体积解析
    try:
        undercut = analyze_undercut(shape)
    except Exception as exc:  # noqa: BLE001
        undercut = None
    try:
        material_suggestion = recommend_material_by_geometry(
            volume_cm3, bbox_mm, surface_area_cm2
        )
    except Exception:  # noqa: BLE001
        material_suggestion = None

    preview_mesh = None
    preview_mesh_status = "unavailable"
    try:
        preview_mesh, preview_mesh_status = export_preview_mesh(shape)
    except Exception:  # noqa: BLE001
        preview_mesh_status = "unavailable"

    return {
        "parse_status": "ok",
        "engine": "ocp",
        "volume_cm3": volume_cm3,
        "surface_area_cm2": surface_area_cm2,
        "bbox_mm": bbox_mm,
        "undercut": undercut,
        "material_suggestion": material_suggestion,
        "preview_mesh": preview_mesh,
        "preview_mesh_status": preview_mesh_status,
        "error": None,
    }


def _worker(path, queue):
    try:
        queue.put(_parse_step_sync(path))
    except Exception as exc:  # noqa: BLE001 - 汇总为结构化错误返回
        queue.put({"parse_status": "error", "error": f"{type(exc).__name__}: {exc}"})


def parse_step(path, timeout=PARSE_TIMEOUT_SEC):
    """解析 STEP 文件。独立进程 + 超时，返回结构化 geometry dict。

    parse_status: ok / error / timeout。调用方据此映射错误码。

    必须先 queue.get 再 proc.join：大结果（含 preview_mesh）超过管道缓冲区时，
    若先 join 会导致子进程无法退出并误报 timeout。

    Celery prefork 子进程本身是 daemon，无法再 spawn 子进程；此时改为同步解析，
    超时由任务 soft_time_limit / time_limit 兜底。
    """
    # Celery prefork 子进程是 daemon，无法再 spawn
    if bool(getattr(mp.current_process(), "daemon", False)):
        result = _parse_step_sync(path)
        result.setdefault("engine", "ocp")
        result["parsed_at"] = _now_iso()
        return result

    ctx = mp.get_context("fork")
    queue = ctx.Queue()
    proc = ctx.Process(target=_worker, args=(path, queue), daemon=True)
    proc.start()

    try:
        result = queue.get(timeout=timeout)
    except Empty:
        if proc.is_alive():
            proc.terminate()
        proc.join()
        return {
            "parse_status": "timeout",
            "engine": "ocp",
            "error": "parse timeout",
            "parsed_at": _now_iso(),
        }

    proc.join(timeout=5)
    if proc.is_alive():
        proc.terminate()
        proc.join()

    result.setdefault("engine", "ocp")
    result["parsed_at"] = _now_iso()
    return result
