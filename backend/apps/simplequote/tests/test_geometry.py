"""STP 几何解析与预览网格单元测试。"""

import unittest

try:
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    HAS_OCP = True
except ImportError:
    HAS_OCP = False


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


if __name__ == "__main__":
    unittest.main()
