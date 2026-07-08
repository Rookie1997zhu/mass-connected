"""STP 几何解析、倒扣分析与预览网格单元测试。"""

import unittest

try:
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.gp import gp_Pnt
    HAS_OCP = True
except ImportError:
    HAS_OCP = False


def _make_box(x, y, z, ox=0.0, oy=0.0, oz=0.0):
    if ox or oy or oz:
        return BRepPrimAPI_MakeBox(gp_Pnt(ox, oy, oz), x, y, z).Shape()
    return BRepPrimAPI_MakeBox(x, y, z).Shape()


def _cut(base, cutter):
    return BRepAlgoAPI_Cut(base, cutter).Shape()


def _fuse(a, b):
    return BRepAlgoAPI_Fuse(a, b).Shape()


def _side_pocket(base_size, pocket_origin, pocket_size):
    """从 +X 侧切入的侧向口袋，形成 Z 向脱模倒扣。"""
    base = _make_box(*base_size)
    cutter = _make_box(*pocket_size, *pocket_origin)
    return _cut(base, cutter)


@unittest.skipUnless(HAS_OCP, "cadquery-ocp not installed")
class GeometryPreviewMeshTests(unittest.TestCase):
    def test_export_preview_mesh_box(self):
        from apps.simplequote.geometry import export_preview_mesh

        shape = BRepPrimAPI_MakeBox(10.0, 20.0, 30.0).Shape()
        mesh, status = export_preview_mesh(shape)
        self.assertIn(status, ("ok", "simplified"))
        self.assertIsNotNone(mesh)
        self.assertEqual(mesh["format"], "stl")
        self.assertEqual(mesh["encoding"], "base64")
        self.assertTrue(len(mesh["data"]) > 0)


@unittest.skipUnless(HAS_OCP, "cadquery-ocp not installed")
class UndercutAnalysisTests(unittest.TestCase):
    def test_plain_box_no_sliders(self):
        from apps.simplequote.geometry import analyze_undercut

        shape = _make_box(80.0, 60.0, 40.0)
        result = analyze_undercut(shape)
        self.assertIsNotNone(result)
        self.assertEqual(result["suggested_sliders"], 0)
        self.assertIn(result["draw_direction"], ("X", "Y", "Z"))
        self.assertLess(result["undercut_area_ratio"], 0.02)
        self.assertIn("sampling", result)
        self.assertFalse(result["sampling"]["downsampled"])

    def test_single_side_pocket_one_slider(self):
        from apps.simplequote.geometry import analyze_undercut

        # 与双凹槽用例相同基体，仅保留一侧口袋
        base = _make_box(120.0, 80.0, 50.0)
        pocket = _make_box(22.0, 30.0, 20.0, 95.0, 10.0, 15.0)
        shape = _cut(base, pocket)
        result = analyze_undercut(shape)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result["suggested_sliders"], 1)
        self.assertGreaterEqual(result["undercut_area_ratio"], 0.02)
        self.assertIn("undercut_clusters", result)

    def test_two_separated_pockets_at_least_two_sliders(self):
        from apps.simplequote.geometry import analyze_undercut

        base = _make_box(120.0, 80.0, 50.0)
        left = _make_box(22.0, 30.0, 20.0, 95.0, 10.0, 15.0)
        right = _make_box(22.0, 30.0, 20.0, 95.0, 40.0, 15.0)
        shape = _cut(_cut(base, left), right)
        result = analyze_undercut(shape)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result["suggested_sliders"], 2)
        self.assertGreaterEqual(len(result["undercut_clusters"]), 2)

    def test_high_face_count_downsampled_not_skipped(self):
        from apps.simplequote.geometry import UNDERCUT_MAX_FACES_SOFT, analyze_undercut

        shape = _make_box(120.0, 120.0, 5.0)
        for i in range(15):
            for j in range(15):
                tiny = _make_box(3.0, 3.0, 6.0, i * 7.5, j * 7.5, 5.0)
                shape = _fuse(shape, tiny)

        result = analyze_undercut(shape)
        self.assertIsNotNone(result)
        self.assertNotEqual(result.get("confidence"), "skipped")
        self.assertIsNone(result.get("skipped_reason"))
        self.assertIn(result["draw_direction"], ("X", "Y", "Z"))
        self.assertIn("sampling", result)
        self.assertTrue(result["sampling"]["downsampled"])
        self.assertGreater(result["sampling"]["faces_total"], UNDERCUT_MAX_FACES_SOFT)
        self.assertLessEqual(result["sampling"]["faces_used"], UNDERCUT_MAX_FACES_SOFT)


@unittest.skipUnless(HAS_OCP, "cadquery-ocp not installed")
class UndercutSamplingTests(unittest.TestCase):
    def test_sample_face_grid(self):
        from apps.simplequote.geometry import _sample_face

        shape = _make_box(30.0, 20.0, 10.0)
        from OCP.TopExp import TopExp_Explorer
        from OCP.TopAbs import TopAbs_FACE
        from OCP.TopoDS import TopoDS

        explorer = TopExp_Explorer(shape, TopAbs_FACE)
        face = TopoDS.Face_s(explorer.Current())
        samples = _sample_face(face, grid_n=3)
        self.assertGreaterEqual(len(samples), 1)
        self.assertAlmostEqual(sum(s[2] for s in samples), sum(s[2] for s in _sample_face(face, grid_n=1)), places=1)


if __name__ == "__main__":
    unittest.main()
