import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np

from beam_calculations import (
    LUMBER_SIZES,
    STEEL_SHAPES,
    BeamInput,
    PointLoad,
    UniformLoad,
    analyze_beam,
    validate_beam_input,
)
from beam_storage import load_design_file, save_design_file
from beam_export import CSV_COLUMNS, export_results_csv
from beam_report import export_calculation_sheet_pdf


class BeamCalculationTests(unittest.TestCase):
    def test_specification_validation_case(self):
        beam = BeamInput(
            beam_type="simply_supported",
            span_ft=30.0,
            point_loads=(),
            uniform_loads=(UniformLoad(2.0, 0.0, 15.0),),
            member=STEEL_SHAPES["W18x35"],
        )
        result = analyze_beam(beam)

        self.assertAlmostEqual(result.reactions_kip[0], 22.5, places=3)
        self.assertAlmostEqual(result.reactions_kip[1], 7.5, places=3)
        self.assertAlmostEqual(result.maximum_moment_kip_ft, 126.6, places=1)
        self.assertAlmostEqual(result.moment_location_ft, 11.25, places=1)

    def test_cantilever_point_load(self):
        beam = BeamInput(
            beam_type="cantilever",
            span_ft=10.0,
            point_loads=(PointLoad(10.0, 10.0),),
            uniform_loads=(),
            member=STEEL_SHAPES["W18x35"],
        )
        result = analyze_beam(beam)

        self.assertAlmostEqual(result.reactions_kip[0], 10.0, places=6)
        self.assertAlmostEqual(result.maximum_moment_kip_ft, 100.0, places=3)
        expected_deflection = 10.0 * 120.0 ** 3 / (3.0 * 29000.0 * 510.0)
        self.assertAlmostEqual(result.maximum_deflection_in, expected_deflection, places=2)

    def test_input_validation_rejects_out_of_span_load(self):
        beam = BeamInput(
            beam_type="simply_supported",
            span_ft=20.0,
            point_loads=(PointLoad(5.0, 21.0),),
            uniform_loads=(),
            member=STEEL_SHAPES["W12x22"],
        )
        self.assertTrue(any("position" in error for error in validate_beam_input(beam)))

    def test_lumber_member_is_available(self):
        member = LUMBER_SIZES["Douglas Fir 2x8"]
        self.assertGreater(member.sx_in3, 0)
        self.assertGreater(member.ix_in4, 0)

    def test_custom_deflection_limit_is_used(self):
        beam = BeamInput(
            beam_type="simply_supported",
            span_ft=30.0,
            point_loads=(),
            uniform_loads=(UniformLoad(2.0, 0.0, 15.0),),
            member=STEEL_SHAPES["W18x35"],
            deflection_limit_in=0.5,
        )
        result = analyze_beam(beam)
        self.assertEqual(result.deflection_limit_in, 0.5)
        self.assertIs(result.deflection_pass, False)


class BeamStorageTests(unittest.TestCase):
    def test_save_and_open_preserves_all_design_inputs(self):
        design = {
            "version": 1,
            "support_type": "cantilever",
            "span_ft": 24.0,
            "deflection_limit_in": 0.8,
            "material": "lumber",
            "section": "Douglas Fir 2x10",
            "point_loads": [
                {"magnitude_kip": 1.25, "position_ft": 18.0},
            ],
            "uniform_loads": [
                {
                    "magnitude_kip_ft": 0.3,
                    "start_ft": 2.0,
                    "end_ft": 20.0,
                },
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "beam.beam.json"
            save_design_file(path, design)
            restored = load_design_file(path)

        self.assertEqual(restored, design)

    def test_save_rejects_load_positions_outside_span(self):
        design = {
            "version": 1,
            "support_type": "simply_supported",
            "span_ft": 10.0,
            "deflection_limit_in": 0.5,
            "material": "steel",
            "section": "W18x35",
            "point_loads": [
                {"magnitude_kip": 1.0, "position_ft": 12.0},
            ],
            "uniform_loads": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.beam.json"
            with self.assertRaisesRegex(ValueError, "position"):
                save_design_file(path, design)
            self.assertFalse(path.exists())


class BeamExportTests(unittest.TestCase):
    def test_csv_has_unit_columns_and_one_row_per_analysis_sample(self):
        beam = BeamInput(
            beam_type="simply_supported",
            span_ft=12.0,
            point_loads=(PointLoad(4.0, 6.0),),
            uniform_loads=(),
            member=STEEL_SHAPES["W18x35"],
        )
        result = analyze_beam(beam, samples=101)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.csv"
            export_results_csv(path, result)
            with path.open(newline="", encoding="utf-8-sig") as file:
                rows = list(csv.reader(file))

        self.assertEqual(tuple(rows[0]), CSV_COLUMNS)
        self.assertEqual(len(rows) - 1, len(result.x_ft))
        self.assertEqual(len(rows[1]), 4)
        first_row = tuple(float(value) for value in rows[1])
        self.assertEqual(
            first_row,
            (
                float(result.x_ft[0]),
                float(result.shear_kip[0]),
                float(result.moment_kip_ft[0]),
                float(result.deflection_in[0]),
            ),
        )

    def test_calculation_sheet_exports_a_pdf(self):
        beam = BeamInput(
            beam_type="simply_supported",
            span_ft=30.0,
            point_loads=(),
            uniform_loads=(UniformLoad(2.0, 0.0, 15.0),),
            member=STEEL_SHAPES["W18x35"],
            deflection_limit_in=1.0,
        )
        result = analyze_beam(beam, samples=301)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "calculation-sheet.pdf"
            export_calculation_sheet_pdf(path, beam, result)
            pdf_data = path.read_bytes()

        self.assertTrue(pdf_data.startswith(b"%PDF-"))
        self.assertTrue(pdf_data.rstrip().endswith(b"%%EOF"))


if __name__ == "__main__":
    unittest.main()
