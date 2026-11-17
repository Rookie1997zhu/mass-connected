"""SMT 工艺费：对齐 jlc_smt_calc 金样 / 价格矩阵。"""

import csv
import unittest
from pathlib import Path

from apps.simplequote.calculator import DEFAULT_PARAMS, SmtQuoteError, calc_smt

REPO_ROOT = Path(__file__).resolve().parents[4]
MATRIX_PATH = REPO_ROOT / "exports" / "jlc_smt_calc" / "jlc_smt_price_matrix.csv"


def _params():
    return dict(DEFAULT_PARAMS["smt"])


def _inputs_from_row(row):
    return {
        "board_length_cm": float(row["boardLength"]),
        "board_width_cm": float(row["boardWidth"]),
        "patch_location": row["patchLocation"],
        "patch_quantity": int(row["patchQuantity"]),
        "patch_component_quantity": int(row["patchComponentQuantity"]),
        "patch_component_type": int(row["patchComponentType"]),
        "plugin_quantity": int(row["plugInQuantity"]),
        "plugin_type": int(row["plugInType"]),
    }


def _load_matrix():
    with MATRIX_PATH.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


class SmtFormulaMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not MATRIX_PATH.exists():
            raise unittest.SkipTest(f"missing matrix: {MATRIX_PATH}")
        cls.rows = _load_matrix()

    def test_matrix_local_totals_within_0_01(self):
        params = _params()
        for row in self.rows:
            with self.subTest(case_id=row["case_id"]):
                result = calc_smt(_inputs_from_row(row), params)
                eco_flag = str(row["eco_available"]).lower() in ("true", "1")
                self.assertEqual(result["eco_available"], eco_flag)
                expected_std = float(row["local_std_total"])
                self.assertAlmostEqual(result["standard"]["totalMoney"], expected_std, delta=0.01)
                self.assertAlmostEqual(result["total"], round(expected_std, 2), delta=0.01)
                if eco_flag:
                    self.assertIsNotNone(result["economic"])
                    self.assertAlmostEqual(
                        result["economic"]["totalMoney"],
                        float(row["local_eco_total"]),
                        delta=0.01,
                    )
                else:
                    self.assertIsNone(result["economic"])

    def test_golden_api_totals_within_0_01(self):
        params = _params()
        golden = [
            row
            for row in self.rows
            if row.get("api_status") == "golden" and str(row.get("diff_ok")).lower() in ("true", "1")
        ]
        self.assertGreaterEqual(len(golden), 10)
        for row in golden:
            with self.subTest(case_id=row["case_id"]):
                result = calc_smt(_inputs_from_row(row), params)
                if row.get("api_std_total"):
                    self.assertAlmostEqual(
                        result["standard"]["totalMoney"],
                        float(row["api_std_total"]),
                        delta=0.01,
                    )
                if result["eco_available"] and row.get("api_eco_total"):
                    self.assertAlmostEqual(
                        result["economic"]["totalMoney"],
                        float(row["api_eco_total"]),
                        delta=0.01,
                    )

    def test_golden_fee_line_items(self):
        """抽检分项：工程费 / 焊点 / 换料计入 / 钢网 / 包装。"""
        params = _params()
        row = next(r for r in self.rows if r["case_id"] == "g000")
        result = calc_smt(_inputs_from_row(row), params)
        eco = result["economic"]
        std = result["standard"]
        self.assertAlmostEqual(eco["projectMoney"], 50.0, delta=0.01)
        self.assertAlmostEqual(eco["padMoney"], 1.0, delta=0.01)
        self.assertAlmostEqual(eco["plateChangeMaterialCountMoney"], 50.0, delta=0.01)
        self.assertAlmostEqual(eco["changeMaterielMoney"], 200.0, delta=0.01)
        self.assertAlmostEqual(std["projectMoney"], 150.0, delta=0.01)
        self.assertAlmostEqual(std["steelMoney"], 50.0, delta=0.01)
        self.assertAlmostEqual(std["packageMoney"], 3.1, delta=0.01)
        self.assertAlmostEqual(std["totalMoney"], 254.1, delta=0.01)

    def test_tb_disables_economic(self):
        result = calc_smt(
            {
                "board_length_cm": 10,
                "board_width_cm": 10,
                "patch_location": "TB",
                "patch_quantity": 5,
                "patch_component_quantity": 20,
                "patch_component_type": 10,
            },
            _params(),
        )
        self.assertFalse(result["eco_available"])
        self.assertIsNone(result["economic"])
        self.assertAlmostEqual(result["standard"]["projectMoney"], 300.0, delta=0.01)
        self.assertAlmostEqual(result["standard"]["steelMoney"], 100.0, delta=0.01)

    def test_quantity_over_50_disables_economic(self):
        result = calc_smt(
            {
                "board_length_cm": 10,
                "board_width_cm": 10,
                "patch_location": "T",
                "patch_quantity": 51,
                "patch_component_quantity": 10,
                "patch_component_type": 2,
            },
            _params(),
        )
        self.assertFalse(result["eco_available"])

    def test_rejects_quantity_below_2(self):
        with self.assertRaises(SmtQuoteError):
            calc_smt(
                {
                    "board_length_cm": 10,
                    "board_width_cm": 10,
                    "patch_location": "T",
                    "patch_quantity": 1,
                },
                _params(),
            )

    def test_excludes_component_cost(self):
        result = calc_smt(
            {
                "board_length_cm": 10,
                "board_width_cm": 10,
                "patch_location": "T",
                "patch_quantity": 5,
            },
            _params(),
        )
        self.assertIn("元器件物料费", result["excludes"])

    def test_pdf_builds(self):
        try:
            from core.pdf import build_smt_quotation_pdf
        except ImportError as exc:
            raise unittest.SkipTest(f"pdf deps unavailable: {exc}") from exc
        result = calc_smt(
            {
                "board_length_cm": 10,
                "board_width_cm": 10,
                "patch_location": "T",
                "patch_quantity": 5,
                "patch_component_quantity": 20,
                "patch_component_type": 10,
            },
            _params(),
        )
        pdf = build_smt_quotation_pdf(
            quote_no="SQ-SMT-TEST",
            product_name="Demo",
            inputs={},
            result=result,
            valid_until="2099-01-01",
            created_at="2026-11-03 12:00",
        )
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 500)


if __name__ == "__main__":
    unittest.main()
