from dataclasses import dataclass, field
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class PointLoad:
    magnitude_kip: float
    position_ft: float


@dataclass(frozen=True)
class UniformLoad:
    magnitude_kip_ft: float
    start_ft: float
    end_ft: float


@dataclass(frozen=True)
class MemberProperties:
    name: str
    material: str
    area_in2: float
    sx_in3: float
    ix_in4: float
    e_ksi: float
    fb_ksi: float


@dataclass(frozen=True)
class BeamInput:
    beam_type: str
    span_ft: float
    point_loads: tuple[PointLoad, ...] = field(default_factory=tuple)
    uniform_loads: tuple[UniformLoad, ...] = field(default_factory=tuple)
    member: MemberProperties | None = None
    deflection_limit_in: float | None = None


@dataclass(frozen=True)
class AnalysisResult:
    reactions_kip: tuple[float, ...]
    x_ft: np.ndarray
    shear_kip: np.ndarray
    moment_kip_ft: np.ndarray
    deflection_in: np.ndarray
    maximum_shear_kip: float
    maximum_moment_kip_ft: float
    moment_location_ft: float
    maximum_deflection_in: float
    deflection_location_ft: float
    bending_stress_ksi: float | None
    bending_limit_ksi: float | None
    bending_pass: bool | None
    deflection_limit_in: float
    deflection_pass: bool | None


STEEL_SHAPES = {
    "W18x35": MemberProperties("W18x35", "Steel", 10.3, 57.6, 510.0, 29000.0, 33.0),
    "W16x31": MemberProperties("W16x31", "Steel", 9.13, 54.0, 375.0, 29000.0, 33.0),
    "W12x22": MemberProperties("W12x22", "Steel", 6.48, 29.3, 156.0, 29000.0, 33.0),
}

LUMBER_SIZES = {
    "Douglas Fir 2x8": MemberProperties(
        "Douglas Fir 2x8", "Lumber", 10.875, 13.14, 47.63, 1600.0, 1.5
    ),
    "Douglas Fir 2x10": MemberProperties(
        "Douglas Fir 2x10", "Lumber", 13.875, 21.39, 98.93, 1600.0, 1.5
    ),
    "Douglas Fir 2x12": MemberProperties(
        "Douglas Fir 2x12", "Lumber", 16.875, 31.17, 178.0, 1600.0, 1.5
    ),
}


def validate_beam_input(beam: BeamInput) -> list[str]:
    errors: list[str] = []
    if beam.beam_type not in {"simply_supported", "cantilever"}:
        errors.append("Beam type must be simply supported or cantilever.")
    if not np.isfinite(beam.span_ft) or beam.span_ft <= 0:
        errors.append("Span must be greater than zero.")
    if beam.span_ft > 100:
        errors.append("Span must be 100 ft or less.")
    if beam.deflection_limit_in is not None:
        if not np.isfinite(beam.deflection_limit_in) or beam.deflection_limit_in <= 0:
            errors.append("Deflection limit must be greater than zero.")

    for index, load in enumerate(beam.point_loads, start=1):
        if not np.isfinite(load.magnitude_kip) or not np.isfinite(load.position_ft):
            errors.append(f"Point load {index} contains a non-numeric value.")
        elif load.position_ft < 0 or load.position_ft > beam.span_ft:
            errors.append(f"Point load {index} position must be from 0 to the span.")

    for index, load in enumerate(beam.uniform_loads, start=1):
        if not np.isfinite(load.magnitude_kip_ft):
            errors.append(f"Uniform load {index} contains a non-numeric magnitude.")
        if not np.isfinite(load.start_ft) or not np.isfinite(load.end_ft):
            errors.append(f"Uniform load {index} contains a non-numeric position.")
        elif load.start_ft < 0 or load.end_ft > beam.span_ft or load.end_ft < load.start_ft:
            errors.append(f"Uniform load {index} must stay within the span with start at or before end.")

    if beam.member is None:
        errors.append("Select a member.")
    elif beam.member.sx_in3 <= 0 or beam.member.ix_in4 <= 0 or beam.member.e_ksi <= 0:
        errors.append("Selected member has invalid properties.")
    return errors


def default_beam() -> BeamInput:
    return BeamInput(
        beam_type="simply_supported",
        span_ft=30.0,
        point_loads=(),
        uniform_loads=(UniformLoad(2.0, 0.0, 15.0),),
        member=STEEL_SHAPES["W18x35"],
        deflection_limit_in=30.0 * 12.0 / 360.0,
    )


def _uniform_force(load: UniformLoad) -> float:
    return load.magnitude_kip_ft * (load.end_ft - load.start_ft)


def _uniform_moment_about(load: UniformLoad, origin_ft: float) -> float:
    length = load.end_ft - load.start_ft
    centroid = load.start_ft + length / 2
    return load.magnitude_kip_ft * length * (centroid - origin_ft)


def _shear_grid(
    x: np.ndarray,
    point_loads: Iterable[PointLoad],
    uniform_loads: Iterable[UniformLoad],
    left_reaction: float = 0.0,
) -> np.ndarray:
    point_loads = tuple(point_loads)
    uniform_loads = tuple(uniform_loads)
    shear = np.full_like(x, left_reaction)
    for load in point_loads:
        shear -= np.where(x >= load.position_ft, load.magnitude_kip, 0.0)
    for load in uniform_loads:
        overlap = np.clip(x - load.start_ft, 0.0, load.end_ft - load.start_ft)
        shear -= load.magnitude_kip_ft * overlap
    return shear


def analyze_beam(beam: BeamInput, samples: int = 3001) -> AnalysisResult:
    errors = validate_beam_input(beam)
    if errors:
        raise ValueError("; ".join(errors))

    x = np.linspace(0.0, beam.span_ft, samples)
    point_loads = tuple(beam.point_loads)
    uniform_loads = tuple(beam.uniform_loads)
    span_in = beam.span_ft * 12.0

    if beam.beam_type == "simply_supported":
        total_force = sum(load.magnitude_kip for load in point_loads)
        total_force += sum(_uniform_force(load) for load in uniform_loads)
        moment_sum = sum(load.magnitude_kip * load.position_ft for load in point_loads)
        moment_sum += sum(_uniform_moment_about(load, 0.0) for load in uniform_loads)
        left_reaction = (total_force * beam.span_ft - moment_sum) / beam.span_ft
        right_reaction = total_force - left_reaction
        reactions = (left_reaction, right_reaction)

        shear = _shear_grid(x, point_loads, uniform_loads, left_reaction)
        moment = np.zeros_like(x)
        for index, position in enumerate(x):
            value = left_reaction * position
            value -= sum(
                load.magnitude_kip * (position - load.position_ft)
                for load in point_loads
                if position >= load.position_ft
            )
            value -= sum(
                (
                    0.0
                    if position <= load.start_ft
                    else (
                        load.magnitude_kip_ft
                        * 0.5
                        * (position - load.start_ft) ** 2
                        if position <= load.end_ft
                        else load.magnitude_kip_ft
                        * (load.end_ft - load.start_ft)
                        * (position - (load.start_ft + load.end_ft) / 2.0)
                    )
                )
                for load in uniform_loads
            )
            moment[index] = value
    else:
        reactions = (sum(load.magnitude_kip for load in point_loads)
                     + sum(_uniform_force(load) for load in uniform_loads),)
        shear = np.zeros_like(x)
        moment = np.zeros_like(x)
        for index, position in enumerate(x):
            shear[index] = sum(
                load.magnitude_kip for load in point_loads
                if load.position_ft >= position
            ) + sum(
                load.magnitude_kip_ft * max(0.0, load.end_ft - max(position, load.start_ft))
                for load in uniform_loads
            )
            moment[index] = -sum(
                load.magnitude_kip * max(0.0, load.position_ft - position)
                for load in point_loads
            )
            for load in uniform_loads:
                overlap_start = max(position, load.start_ft)
                overlap_end = load.end_ft
                if overlap_end > overlap_start:
                    centroid = (overlap_start + overlap_end) / 2
                    moment[index] -= load.magnitude_kip_ft * (overlap_end - overlap_start) * (
                        centroid - position
                    )

    member = beam.member
    assert member is not None
    ei = member.e_ksi * member.ix_in4
    x_in = x * 12.0
    moment_kip_in = moment * 12.0
    deflection = np.zeros_like(x)
    n = len(x)
    dx = span_in / (n - 1)
    if beam.beam_type == "simply_supported":
        interior = n - 2
        matrix = np.zeros((interior, interior))
        rhs = -moment_kip_in[1:-1] / ei
        np.fill_diagonal(matrix, -2.0)
        if interior > 1:
            np.fill_diagonal(matrix[1:], 1.0)
            np.fill_diagonal(matrix[:, 1:], 1.0)
        interior_deflection = np.linalg.solve(matrix, rhs * dx * dx)
        deflection[1:-1] = interior_deflection
    else:
        deflection = np.zeros_like(x)
        for load in point_loads:
            position_in = load.position_ft * 12.0
            for index, position_x_in in enumerate(x_in):
                if position_x_in <= position_in:
                    deflection[index] += (
                        load.magnitude_kip
                        * position_x_in**2
                        * (3.0 * position_in - position_x_in)
                        / (6.0 * ei)
                    )
                else:
                    deflection[index] += (
                        load.magnitude_kip
                        * position_in**2
                        * (3.0 * position_x_in - position_in)
                        / (6.0 * ei)
                    )

        for load in uniform_loads:
            segment_edges = np.linspace(
                load.start_ft * 12.0,
                load.end_ft * 12.0,
                201,
            )
            segment_width = segment_edges[1] - segment_edges[0]
            segment_midpoints = (segment_edges[:-1] + segment_edges[1:]) / 2.0
            for position_in in segment_midpoints:
                point_force = load.magnitude_kip_ft * segment_width / 12.0
                for index, x_position_in in enumerate(x_in):
                    if x_position_in <= position_in:
                        deflection[index] += (
                            point_force
                            * x_position_in**2
                            * (3.0 * position_in - x_position_in)
                            / (6.0 * ei)
                        )
                    else:
                        deflection[index] += (
                            point_force
                            * position_in**2
                            * (3.0 * x_position_in - position_in)
                            / (6.0 * ei)
                        )

    max_shear = float(np.max(np.abs(shear)))
    max_moment = float(np.max(np.abs(moment)))
    moment_location = float(x[int(np.argmax(np.abs(moment)))])
    max_deflection = float(np.max(np.abs(deflection)))
    deflection_location = float(x[int(np.argmax(np.abs(deflection)))])
    deflection_limit = (
        beam.deflection_limit_in
        if beam.deflection_limit_in is not None
        else beam.span_ft * 12.0 / 360.0
    )

    bending_stress = max_moment * 12.0 / member.sx_in3
    bending_pass = bending_stress <= member.fb_ksi
    deflection_pass = max_deflection <= deflection_limit

    return AnalysisResult(
        reactions_kip=reactions,
        x_ft=x,
        shear_kip=shear,
        moment_kip_ft=moment,
        deflection_in=deflection,
        maximum_shear_kip=max_shear,
        maximum_moment_kip_ft=max_moment,
        moment_location_ft=moment_location,
        maximum_deflection_in=max_deflection,
        deflection_location_ft=deflection_location,
        bending_stress_ksi=bending_stress,
        bending_limit_ksi=member.fb_ksi,
        bending_pass=bending_pass,
        deflection_limit_in=deflection_limit,
        deflection_pass=deflection_pass,
    )
