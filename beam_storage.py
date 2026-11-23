import json
import math
from pathlib import Path

from beam_calculations import (
    LUMBER_SIZES,
    STEEL_SHAPES,
    BeamInput,
    PointLoad,
    UniformLoad,
    validate_beam_input,
)


def save_design_file(path: str | Path, design: dict) -> None:
    normalized_design = _normalize_design(design)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(normalized_design, file, indent=2, allow_nan=False)


def load_design_file(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as file:
        design = json.load(file)
    return _normalize_design(design)


def _normalize_design(design: object) -> dict:
    if not isinstance(design, dict):
        raise ValueError("Saved beam design must be a JSON object.")
    if type(design.get("version")) is not int or design["version"] != 1:
        raise ValueError("Saved beam design has an unsupported version.")

    support_type = design.get("support_type")
    if not isinstance(support_type, str) or support_type not in {
        "simply_supported", "cantilever"
    }:
        raise ValueError("Saved file has an unsupported support type.")
    material = design.get("material")
    if not isinstance(material, str) or material not in {"steel", "lumber"}:
        raise ValueError("Saved file has an unsupported material.")
    catalog = STEEL_SHAPES if material == "steel" else LUMBER_SIZES
    section = design.get("section")
    if not isinstance(section, str) or section not in catalog:
        raise ValueError("Saved file section is not in the current catalog.")

    span = _finite_number(design.get("span_ft"), "span")
    deflection_limit = _finite_number(
        design.get("deflection_limit_in"), "deflection limit"
    )
    raw_point_loads = design.get("point_loads")
    raw_uniform_loads = design.get("uniform_loads")
    if not isinstance(raw_point_loads, list) or not isinstance(raw_uniform_loads, list):
        raise ValueError("Saved loads must be lists.")

    point_loads = tuple(
        PointLoad(
            _finite_number(load.get("magnitude_kip"), "point load magnitude"),
            _finite_number(load.get("position_ft"), "point load position"),
        )
        for load in _load_objects(raw_point_loads, "point")
    )
    uniform_loads = tuple(
        UniformLoad(
            _finite_number(load.get("magnitude_kip_ft"), "uniform load magnitude"),
            _finite_number(load.get("start_ft"), "uniform load start"),
            _finite_number(load.get("end_ft"), "uniform load end"),
        )
        for load in _load_objects(raw_uniform_loads, "uniform")
    )
    beam = BeamInput(
        beam_type=support_type,
        span_ft=span,
        point_loads=point_loads,
        uniform_loads=uniform_loads,
        member=catalog[section],
        deflection_limit_in=deflection_limit,
    )
    errors = validate_beam_input(beam)
    if errors:
        raise ValueError("; ".join(errors))

    return {
        "version": 1,
        "support_type": support_type,
        "span_ft": span,
        "deflection_limit_in": deflection_limit,
        "material": material,
        "section": section,
        "point_loads": [
            {"magnitude_kip": load.magnitude_kip, "position_ft": load.position_ft}
            for load in point_loads
        ],
        "uniform_loads": [
            {
                "magnitude_kip_ft": load.magnitude_kip_ft,
                "start_ft": load.start_ft,
                "end_ft": load.end_ft,
            }
            for load in uniform_loads
        ],
    }


def _finite_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Saved {label} must be a number.")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ValueError(f"Saved {label} is outside the supported numeric range.") from exc
    if not math.isfinite(number):
        raise ValueError(f"Saved {label} must be finite.")
    return number


def _load_objects(value: list, label: str) -> list[dict]:
    if any(not isinstance(load, dict) for load in value):
        raise ValueError(f"Saved {label} loads must be objects.")
    return value
