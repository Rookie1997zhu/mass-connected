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
# 倒扣分析面数上限：射线求交为 O(面数×6)，超过则跳过以保护核心体积/尺寸解析预算
UNDERCUT_MAX_FACES = 800

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
    from OCP.BRep import BRep_Tool
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.GeomLProp import GeomLProp_SLProps
    from OCP.TopAbs import TopAbs_REVERSED
    from OCP.BRepTools import BRepTools

    surface = BRep_Tool.Surface_s(face)
    if surface is None:
        return None
    umin, umax, vmin, vmax = BRepTools.UVBounds_s(face)
    u = (umin + umax) / 2.0
    v = (vmin + vmax) / 2.0
    props = GeomLProp_SLProps(surface, u, v, 1, 1e-6)
    if not props.IsNormalDefined():
        return None
    n = props.Normal()
    nx, ny, nz = n.X(), n.Y(), n.Z()
    if face.Orientation() == TopAbs_REVERSED:
        nx, ny, nz = -nx, -ny, -nz
    fprops = GProp_GProps()
    BRepGProp.SurfaceProperties_s(face, fprops)
    area = fprops.Mass()
    com = fprops.CentreOfMass()
    return ((com.X(), com.Y(), com.Z()), (nx, ny, nz), area)


def analyze_undercut(shape):
    """基于可见性(遮挡)的倒扣分析。

    两板模沿某主拔模轴的 ±方向开模：某面若从其外侧沿 +轴 与 -轴 均被材料挡住
    （无法脱模），则判定为倒扣面。选倒扣面积最小的轴为主拔模轴；残余倒扣占比
    超阈值时按侧向法向聚类给出滑块建议数 + 置信度（建议值，需人工确认）。
    """
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
    from OCP.gp import gp_Lin, gp_Pnt, gp_Dir

    faces = []
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = TopoDS.Face_s(explorer.Current())
        info = _face_props(face)
        if info is not None:
            faces.append(info)
        explorer.Next()

    total_area = sum(f[2] for f in faces)
    if not faces or total_area <= 0:
        return None
    # 面数过多时射线求交开销过大，跳过倒扣分析以保护体积/尺寸解析（best-effort）
    if len(faces) > UNDERCUT_MAX_FACES:
        return {
            "draw_direction": None,
            "undercut_area_ratio": None,
            "suggested_sliders": None,
            "confidence": "skipped",
            "skipped_reason": "too_many_faces",
        }

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

    best = None
    for name, axis in _DRAW_AXES:
        ax, ay, az = axis
        undercut_area = 0.0
        undercut_normals = []
        for (cx, cy, cz), (nx, ny, nz), area in faces:
            # 从面外侧稍偏出的点出发，避免打到自身
            ox, oy, oz = cx + nx * eps, cy + ny * eps, cz + nz * eps
            up_clear = not _blocked((ox, oy, oz), (ax, ay, az))
            down_clear = not _blocked((ox, oy, oz), (-ax, -ay, -az))
            if not up_clear and not down_clear:
                undercut_area += area
                undercut_normals.append((nx, ny, nz))
        if best is None or undercut_area < best["undercut_area"]:
            best = {"axis": name, "undercut_area": undercut_area, "normals": undercut_normals}

    ratio = best["undercut_area"] / total_area if total_area else 0.0
    if ratio < UNDERCUT_AREA_RATIO_MIN:
        suggested_sliders = 0
        confidence = "medium"
    else:
        suggested_sliders = _cluster_slider_count(best["normals"])
        confidence = "medium" if ratio > 0.1 else "low"

    return {
        "draw_direction": best["axis"],
        "undercut_area_ratio": round(ratio, 4),
        "suggested_sliders": suggested_sliders,
        "confidence": confidence,
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
    """
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
