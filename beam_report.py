import textwrap
from pathlib import Path

import numpy as np
from matplotlib.figure import Figure

from beam_calculations import AnalysisResult, BeamInput


def export_calculation_sheet_pdf(
    path: str | Path,
    beam: BeamInput,
    result: AnalysisResult,
) -> None:
    if beam.member is None:
        raise ValueError("A member must be selected before exporting a calculation sheet.")

    input_lines = _input_lines(beam)
    figure_width = 11.7
    figure_height = max(8.3, 7.65 + 0.17 * len(input_lines))
    figure = Figure(figsize=(figure_width, figure_height), facecolor="white")
    figure.text(
        0.05, 1.0 - 0.38 / figure_height,
        "Beam Designer — Calculation Sheet",
        fontsize=17, fontweight="bold", color="#843B28", va="top",
    )
    figure.text(
        0.05, 1.0 - 0.79 / figure_height,
        "Design inputs",
        fontsize=10, fontweight="bold", color="#1d2b38", va="top",
    )
    for index, line in enumerate(input_lines):
        figure.text(
            0.05, 1.0 - (1.05 + 0.17 * index) / figure_height,
            line, fontsize=8.5, color="#1d2b38", va="top",
        )

    plot_width = 5.15 / figure_width
    plot_height = 2.1 / figure_height
    left = 0.55 / figure_width
    right = 6.0 / figure_width
    top_row = 4.35 / figure_height
    bottom_row = 1.9 / figure_height
    beam_axis = figure.add_axes([left, top_row, plot_width, plot_height])
    shear_axis = figure.add_axes([right, top_row, plot_width, plot_height])
    moment_axis = figure.add_axes([left, bottom_row, plot_width, plot_height])
    deflection_axis = figure.add_axes([right, bottom_row, plot_width, plot_height])

    _draw_beam_and_loads(beam_axis, beam)
    _draw_diagram(shear_axis, result.x_ft, result.shear_kip, "Shear Diagram", "V (kip)")
    _draw_diagram(
        moment_axis, result.x_ft, result.moment_kip_ft, "Moment Diagram", "M (kip-ft)"
    )
    _draw_diagram(
        deflection_axis, result.x_ft, result.deflection_in,
        "Deflection Diagram", "Deflection (in)",
    )
    _draw_check_summary(figure, result)

    figure.savefig(
        path,
        format="pdf",
        metadata={"Title": "Beam Designer Calculation Sheet"},
    )


def _input_lines(beam: BeamInput) -> list[str]:
    member = beam.member
    if member is None:
        return []
    support = "Simply supported" if beam.beam_type == "simply_supported" else "Cantilever"
    point_load_text = "; ".join(
        f"P{index} = {load.magnitude_kip:g} kip at {load.position_ft:g} ft"
        for index, load in enumerate(beam.point_loads, start=1)
    ) or "None"
    uniform_load_text = "; ".join(
        f"w{index} = {load.magnitude_kip_ft:g} kip/ft from "
        f"{load.start_ft:g} to {load.end_ft:g} ft"
        for index, load in enumerate(beam.uniform_loads, start=1)
    ) or "None"
    values = [
        f"Support: {support}    Span: {beam.span_ft:g} ft",
        f"Member: {member.material} {member.name}    "
        f"Deflection limit: {beam.deflection_limit_in:g} in"
        if beam.deflection_limit_in is not None
        else f"Member: {member.material} {member.name}    Deflection limit: L/360",
        f"Point loads: {point_load_text}",
        f"Uniform loads: {uniform_load_text}",
    ]
    lines: list[str] = []
    for value in values:
        lines.extend(textwrap.wrap(value, width=145, subsequent_indent="  ") or [""])
    return lines


def _draw_beam_and_loads(axis, beam: BeamInput) -> None:
    color = "#A64E32"
    span = beam.span_ft
    axis.plot([0, span], [0, 0], color="#843B28", linewidth=7, solid_capstyle="round")
    if beam.beam_type == "simply_supported":
        axis.scatter([0, span], [0, 0], marker="^", s=115, color="#647585", zorder=5)
    else:
        axis.plot([-0.02 * span, -0.02 * span], [-0.45, 0.45],
                  color="#647585", linewidth=5)

    arrow_height = 0.5
    for load in beam.point_loads:
        direction = -1 if load.magnitude_kip >= 0 else 1
        axis.annotate(
            "",
            xy=(load.position_ft, 0.04 * direction),
            xytext=(load.position_ft, arrow_height * direction),
            arrowprops=dict(arrowstyle="->", color=color, lw=1.5),
        )
        axis.text(
            load.position_ft, (arrow_height + 0.05) * direction,
            f"{load.magnitude_kip:g} kip",
            ha="center", va="top" if direction < 0 else "bottom",
            fontsize=7, color=color,
        )

    for load in beam.uniform_loads:
        positions = np.linspace(load.start_ft, load.end_ft, 8)
        direction = -1 if load.magnitude_kip_ft >= 0 else 1
        for position in positions:
            axis.annotate(
                "",
                xy=(position, 0.04 * direction),
                xytext=(position, 0.36 * direction),
                arrowprops=dict(arrowstyle="->", color=color, lw=1.0),
            )
        axis.text(
            (load.start_ft + load.end_ft) / 2,
            0.42 * direction,
            f"{load.magnitude_kip_ft:g} kip/ft",
            ha="center", va="top" if direction < 0 else "bottom",
            fontsize=7, color=color,
        )

    axis.set_xlim(-0.06 * span, 1.06 * span)
    axis.set_ylim(-0.85, 0.85)
    axis.set_xticks([0, span])
    axis.set_yticks([])
    axis.set_xlabel("Position (ft)")
    axis.set_title("Beam and Loads", loc="left", fontsize=10, fontweight="bold")
    axis.grid(axis="x", color="#dfe6ea")
    _clean_axes(axis)


def _draw_diagram(axis, x_values, y_values, title: str, ylabel: str) -> None:
    axis.plot(x_values, y_values, color="#A64E32", linewidth=1.8)
    axis.fill_between(x_values, y_values, 0, color="#F3DDD3", alpha=0.8)
    axis.axhline(0, color="#647585", linewidth=0.7)
    axis.set_title(title, loc="left", fontsize=10, fontweight="bold")
    axis.set_xlabel("Position (ft)", fontsize=8)
    axis.set_ylabel(ylabel, fontsize=8)
    axis.tick_params(labelsize=7)
    axis.grid(True, color="#e7ecef", linewidth=0.7)
    _clean_axes(axis)


def _clean_axes(axis) -> None:
    for side in ("top", "right"):
        axis.spines[side].set_visible(False)
    axis.spines["left"].set_color("#cbd5dc")
    axis.spines["bottom"].set_color("#cbd5dc")


def _draw_check_summary(figure: Figure, result: AnalysisResult) -> None:
    bending_status = "PASS" if result.bending_pass else "FAIL"
    deflection_status = "PASS" if result.deflection_pass else "FAIL"
    overall_status = (
        "PASS" if result.bending_pass and result.deflection_pass else "FAIL"
    )
    summary = (
        f"Maximum shear: {result.maximum_shear_kip:.3f} kip     "
        f"Maximum moment: {result.maximum_moment_kip_ft:.3f} kip-ft "
        f"at {result.moment_location_ft:.3f} ft\n"
        f"Bending: {result.bending_stress_ksi:.3f} / "
        f"{result.bending_limit_ksi:.3f} ksi — {bending_status}     "
        f"Deflection: {result.maximum_deflection_in:.4f} / "
        f"{result.deflection_limit_in:.4f} in — {deflection_status}     "
        f"Overall: {overall_status}"
    )
    figure.text(
        0.05, 0.065, summary,
        fontsize=8.5, color="#1d2b38", va="bottom",
        bbox=dict(boxstyle="round,pad=0.45", facecolor="#f4f7f9", edgecolor="#ccd6de"),
    )
