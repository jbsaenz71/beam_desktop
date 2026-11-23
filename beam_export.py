import csv
import math
from pathlib import Path

from beam_calculations import AnalysisResult


CSV_COLUMNS = ("x_ft", "V_kip", "M_kip_ft", "deflection_in")


def export_results_csv(path: str | Path, result: AnalysisResult) -> None:
    columns = (
        result.x_ft,
        result.shear_kip,
        result.moment_kip_ft,
        result.deflection_in,
    )
    if not columns[0].size or any(column.size != columns[0].size for column in columns):
        raise ValueError("Beam result arrays must be non-empty and have matching lengths.")
    if any(
        not math.isfinite(float(value))
        for column in columns
        for value in column
    ):
        raise ValueError("Beam results contain a non-finite value.")

    with open(path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(CSV_COLUMNS)
        for values in zip(*columns):
            row = tuple(float(value) for value in values)
            writer.writerow(row)
