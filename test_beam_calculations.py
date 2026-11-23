import unittest

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


if __name__ == "__main__":
    unittest.main()
