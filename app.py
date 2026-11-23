import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import filedialog

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from beam_calculations import (
    LUMBER_SIZES,
    STEEL_SHAPES,
    BeamInput,
    PointLoad,
    UniformLoad,
    analyze_beam,
)
from beam_storage import load_design_file, save_design_file


class BeamDesignerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Beam Designer")
        self.root.geometry("1400x850")
        self.root.minsize(980, 650)

        self.beam_type = tk.StringVar(value="simply_supported")
        self.member_type = tk.StringVar(value="steel")
        self.member_name = tk.StringVar(value="W18x35")

        self._configure_styles()
        self._build_layout()
        self._build_menu()
        self._build_example()
        self.calculate()

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self.root)
        file_menu = tk.Menu(menu_bar, tearoff=False)
        file_menu.add_command(label="Save", command=self.save_design)
        file_menu.add_command(label="Open", command=self.open_design)
        menu_bar.add_cascade(label="File", menu=file_menu)
        self.root.config(menu=menu_bar)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background="#f4f7f9")
        style.configure("Panel.TFrame", background="#ffffff")
        style.configure("Card.TLabelframe", background="#ffffff")
        style.configure("Card.TLabelframe.Label", background="#ffffff", foreground="#1d2b38",
                        font=("Segoe UI", 11, "bold"))
        style.configure("TLabel", background="#ffffff", foreground="#415466",
                        font=("Segoe UI", 10))
        style.configure("Title.TLabel", background="#ffffff", foreground="#1d2b38",
                        font=("Segoe UI", 14, "bold"))
        style.configure("Status.TLabel", background="#edf8f3", foreground="#16835b",
                        font=("Segoe UI", 11, "bold"))
        style.configure("Fail.Status.TLabel", background="#fff0f0", foreground="#a83232")
        style.configure("Primary.TButton", font=("Segoe UI", 11, "bold"),
                        background="#A64E32", foreground="#ffffff")

    def _build_layout(self) -> None:
        header = tk.Frame(self.root, height=68, bg="#A64E32")
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="Beam Designer", bg="#A64E32", fg="white",
                 font=("Segoe UI", 16, "bold")).pack(side="left", padx=24)
        tk.Label(header, text="US Customary Units", bg="#A64E32", fg="#F9DED2",
                 font=("Segoe UI", 10, "bold")).pack(side="right", padx=24)

        content = ttk.Panedwindow(self.root, orient="horizontal")
        content.pack(fill="both", expand=True)

        left_scroll = tk.Frame(content, bg="#f4f7f9")
        content.add(left_scroll, weight=0)
        canvas = tk.Canvas(left_scroll, width=360, bg="#f4f7f9", highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_scroll, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        panel = ttk.Frame(canvas, style="Panel.TFrame", padding=16)
        canvas_window = canvas.create_window((0, 0), window=panel, anchor="nw")
        panel.bind(
            "<Configure>",
            lambda event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(canvas_window, width=event.width),
        )

        right = ttk.Frame(content, padding=12)
        content.add(right, weight=1)

        ttk.Label(panel, text="Beam and Loading", style="Title.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )

        ttk.Label(panel, text="Beam type").grid(row=1, column=0, columnspan=2, sticky="w")
        beam_buttons = ttk.Frame(panel)
        beam_buttons.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 12))
        ttk.Radiobutton(beam_buttons, text="Simply supported", value="simply_supported",
                        variable=self.beam_type).pack(side="left", expand=True, fill="x")
        ttk.Radiobutton(beam_buttons, text="Cantilever", value="cantilever",
                        variable=self.beam_type).pack(side="left", expand=True, fill="x")

        ttk.Label(panel, text="Span").grid(row=3, column=0, sticky="w")
        self.span_entry = ttk.Entry(panel)
        self.span_entry.grid(row=3, column=1, sticky="ew")
        ttk.Label(panel, text="ft").grid(row=3, column=2, sticky="w", padx=(6, 0))

        ttk.Label(panel, text="Deflection limit").grid(row=4, column=0, sticky="w")
        self.deflection_limit_entry = ttk.Entry(panel)
        self.deflection_limit_entry.grid(row=4, column=1, sticky="ew")
        ttk.Label(panel, text="in").grid(row=4, column=2, sticky="w", padx=(6, 0))

        point_section = ttk.LabelFrame(panel, text="Point Loads", style="Card.TLabelframe",
                                       padding=8)
        point_section.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(14, 8))
        self.point_container = ttk.Frame(point_section)
        self.point_container.pack(fill="x")
        ttk.Button(point_section, text="+ Add point load",
                   command=self.add_point_load).pack(anchor="e", pady=(8, 0))

        uniform_section = ttk.LabelFrame(panel, text="Uniform Loads", style="Card.TLabelframe",
                                         padding=8)
        uniform_section.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(8, 8))
        self.uniform_container = ttk.Frame(uniform_section)
        self.uniform_container.pack(fill="x")
        ttk.Button(uniform_section, text="+ Add uniform load",
                   command=self.add_uniform_load).pack(anchor="e", pady=(8, 0))

        member_section = ttk.LabelFrame(panel, text="Member", style="Card.TLabelframe",
                                        padding=8)
        member_section.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(8, 8))
        ttk.Label(member_section, text="Material").grid(row=0, column=0, sticky="w")
        material_buttons = ttk.Frame(member_section)
        material_buttons.grid(row=0, column=1, sticky="ew")
        ttk.Radiobutton(material_buttons, text="Steel", value="steel",
                        variable=self.member_type,
                        command=self._refresh_member_choices).pack(side="left", expand=True)
        ttk.Radiobutton(material_buttons, text="Lumber", value="lumber",
                        variable=self.member_type,
                        command=self._refresh_member_choices).pack(side="left", expand=True)

        ttk.Label(member_section, text="Section").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.member_combo = ttk.Combobox(member_section, textvariable=self.member_name,
                                         state="readonly")
        self.member_combo.grid(row=1, column=1, sticky="ew", pady=(8, 0))
        self.member_combo.bind("<<ComboboxSelected>>", lambda event: self._update_member_properties())

        self.properties_label = ttk.Label(member_section, text="",
                                          justify="left", wraplength=260)
        self.properties_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))

        panel.columnconfigure(1, weight=1)
        member_section.columnconfigure(1, weight=1)

        ttk.Button(panel, text="Calculate Beam", style="Primary.TButton",
                   command=self.calculate).grid(
            row=8, column=0, columnspan=3, sticky="ew", pady=(12, 8)
        )
        ttk.Button(panel, text="Reset Example", command=self._build_example).grid(
            row=9, column=0, columnspan=3, sticky="ew"
        )

        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        self.status_frame = ttk.Frame(right)
        self.status_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.status_label = ttk.Label(self.status_frame, text="", style="Status.TLabel",
                                      padding=(10, 8))
        self.status_label.pack(side="left", fill="x", expand=True)

        self.figure = Figure(figsize=(11, 7), dpi=100, facecolor="#f4f7f9")
        self.canvas = FigureCanvasTkAgg(self.figure, master=right)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")

        self._refresh_member_choices()

    def _clear_load_rows(self) -> None:
        for widget in self.point_container.winfo_children():
            widget.destroy()
        for widget in self.uniform_container.winfo_children():
            widget.destroy()

    def _build_example(self) -> None:
        self._clear_load_rows()
        self.beam_type.set("simply_supported")
        self.span_entry.delete(0, "end")
        self.span_entry.insert(0, "30")
        self.deflection_limit_entry.delete(0, "end")
        self.deflection_limit_entry.insert(0, "1.0")
        self.member_type.set("steel")
        self.member_name.set("W18x35")
        self._refresh_member_choices()
        self.add_uniform_load(2.0, 0.0, 15.0)
        self._update_member_properties()
        self.calculate()

    def add_point_load(self, magnitude: float | None = None, position: float | None = None) -> None:
        row = ttk.Frame(self.point_container)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text="Magnitude").grid(row=0, column=0, sticky="w")
        magnitude_entry = ttk.Entry(row, width=9)
        magnitude_entry.grid(row=1, column=0, sticky="ew")
        ttk.Label(row, text="kip").grid(row=1, column=1, sticky="w", padx=(4, 8))
        ttk.Label(row, text="Position").grid(row=0, column=2, sticky="w")
        position_entry = ttk.Entry(row, width=9)
        position_entry.grid(row=1, column=2, sticky="ew")
        ttk.Label(row, text="ft").grid(row=1, column=3, sticky="w", padx=(4, 4))
        ttk.Button(row, text="x", width=3,
                   command=row.destroy).grid(row=1, column=4)
        row.magnitude_entry = magnitude_entry
        row.position_entry = position_entry
        row.columnconfigure(0, weight=1)
        row.columnconfigure(2, weight=1)
        if magnitude is not None:
            magnitude_entry.insert(0, str(magnitude))
        if position is not None:
            position_entry.insert(0, str(position))

    def add_uniform_load(
        self, magnitude: float | None = None,
        start: float | None = None, end: float | None = None,
    ) -> None:
        row = ttk.Frame(self.uniform_container)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text="w").grid(row=0, column=0, sticky="w")
        magnitude_entry = ttk.Entry(row, width=8)
        magnitude_entry.grid(row=1, column=0, sticky="ew")
        ttk.Label(row, text="kip/ft").grid(row=1, column=1, sticky="w", padx=(4, 6))
        ttk.Label(row, text="Start").grid(row=0, column=2, sticky="w")
        start_entry = ttk.Entry(row, width=7)
        start_entry.grid(row=1, column=2, sticky="ew")
        ttk.Label(row, text="End").grid(row=0, column=3, sticky="w")
        end_entry = ttk.Entry(row, width=7)
        end_entry.grid(row=1, column=3, sticky="ew")
        ttk.Label(row, text="ft").grid(row=1, column=4, sticky="w", padx=(4, 4))
        ttk.Button(row, text="x", width=3,
                   command=row.destroy).grid(row=1, column=5)
        row.magnitude_entry = magnitude_entry
        row.start_entry = start_entry
        row.end_entry = end_entry
        if magnitude is not None:
            magnitude_entry.insert(0, str(magnitude))
        if start is not None:
            start_entry.insert(0, str(start))
        if end is not None:
            end_entry.insert(0, str(end))

    def _refresh_member_choices(self) -> None:
        catalog = STEEL_SHAPES if self.member_type.get() == "steel" else LUMBER_SIZES
        names = list(catalog)
        self.member_combo["values"] = names
        if self.member_name.get() not in catalog:
            self.member_name.set(names[0])
        self._update_member_properties()

    def _update_member_properties(self) -> None:
        catalog = STEEL_SHAPES if self.member_type.get() == "steel" else LUMBER_SIZES
        member = catalog.get(self.member_name.get())
        if member is None:
            self.properties_label.configure(text="")
            return
        self.properties_label.configure(
            text=(
                f"A = {member.area_in2:.3g} in²\n"
                f"Sx = {member.sx_in3:.3g} in³\n"
                f"Ix = {member.ix_in4:.3g} in⁴\n"
                f"E = {member.e_ksi:.3g} ksi\n"
                f"Reference Fb = {member.fb_ksi:.3g} ksi"
            )
        )

    def _selected_member(self):
        catalog = STEEL_SHAPES if self.member_type.get() == "steel" else LUMBER_SIZES
        return catalog[self.member_name.get()]

    def _parse_float(self, entry: ttk.Entry, label: str) -> float:
        try:
            return float(entry.get())
        except ValueError:
            raise ValueError(f"{label} must be a number.")

    def _collect_design(self) -> dict:
        span = self._parse_float(self.span_entry, "Span")
        deflection_limit = self._parse_float(
            self.deflection_limit_entry, "Deflection limit"
        )
        point_loads = []
        for row in self.point_container.winfo_children():
            point_loads.append({
                "magnitude_kip": self._parse_float(
                    row.magnitude_entry, "Point load magnitude"
                ),
                "position_ft": self._parse_float(
                    row.position_entry, "Point load position"
                ),
            })
        uniform_loads = []
        for row in self.uniform_container.winfo_children():
            uniform_loads.append({
                "magnitude_kip_ft": self._parse_float(
                    row.magnitude_entry, "Uniform load magnitude"
                ),
                "start_ft": self._parse_float(
                    row.start_entry, "Uniform load start"
                ),
                "end_ft": self._parse_float(
                    row.end_entry, "Uniform load end"
                ),
            })
        return {
            "version": 1,
            "support_type": self.beam_type.get(),
            "span_ft": span,
            "deflection_limit_in": deflection_limit,
            "material": self.member_type.get(),
            "section": self.member_name.get(),
            "point_loads": point_loads,
            "uniform_loads": uniform_loads,
        }

    def save_design(self) -> None:
        try:
            design = self._collect_design()
        except ValueError as exc:
            messagebox.showerror("Unable to save beam", str(exc))
            return

        path = filedialog.asksaveasfilename(
            title="Save Beam Design",
            defaultextension=".beam.json",
            filetypes=[("Beam design", "*.beam.json"), ("JSON", "*.json")],
        )
        if not path:
            return
        try:
            save_design_file(path, design)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Unable to save beam", str(exc))

    def open_design(self) -> None:
        path = filedialog.askopenfilename(
            title="Open Beam Design",
            filetypes=[("Beam design", "*.beam.json"), ("JSON", "*.json")],
        )
        if not path:
            return
        try:
            design = load_design_file(path)
            self._clear_load_rows()
            self.beam_type.set(design["support_type"])
            self.span_entry.delete(0, "end")
            self.span_entry.insert(0, str(design["span_ft"]))
            self.deflection_limit_entry.delete(0, "end")
            self.deflection_limit_entry.insert(
                0, str(design["deflection_limit_in"])
            )
            self.member_type.set(design["material"])
            self._refresh_member_choices()
            self.member_name.set(design["section"])
            self._update_member_properties()

            for load in design.get("point_loads", []):
                self.add_point_load(
                    load["magnitude_kip"], load["position_ft"]
                )
            for load in design.get("uniform_loads", []):
                self.add_uniform_load(
                    load["magnitude_kip_ft"],
                    load["start_ft"],
                    load["end_ft"],
                )
            self.calculate()
        except (OSError, TypeError, ValueError) as exc:
            messagebox.showerror("Unable to open beam", str(exc))

    def calculate(self) -> None:
        try:
            span = self._parse_float(self.span_entry, "Span")
            deflection_limit = self._parse_float(
                self.deflection_limit_entry, "Deflection limit"
            )
            point_loads = []
            for row in self.point_container.winfo_children():
                magnitude = self._parse_float(row.magnitude_entry, "Point load magnitude")
                position = self._parse_float(row.position_entry, "Point load position")
                point_loads.append(PointLoad(magnitude, position))

            uniform_loads = []
            for row in self.uniform_container.winfo_children():
                magnitude = self._parse_float(row.magnitude_entry, "Uniform load magnitude")
                start = self._parse_float(row.start_entry, "Uniform load start")
                end = self._parse_float(row.end_entry, "Uniform load end")
                uniform_loads.append(UniformLoad(magnitude, start, end))

            beam = BeamInput(
                beam_type=self.beam_type.get(),
                span_ft=span,
                point_loads=tuple(point_loads),
                uniform_loads=tuple(uniform_loads),
                member=self._selected_member(),
                deflection_limit_in=deflection_limit,
            )
            result = analyze_beam(beam)
        except (ValueError, KeyError) as exc:
            messagebox.showerror("Unable to calculate beam", str(exc))
            return

        bending_ok = result.bending_pass is True
        deflection_ok = result.deflection_pass is True
        overall_ok = bending_ok and deflection_ok
        if overall_ok:
            status_text = "PASS — Bending and deflection checks passed"
            status_style = "Status.TLabel"
        else:
            failed = []
            if not bending_ok:
                failed.append("bending")
            if not deflection_ok:
                failed.append("deflection")
            status_text = "FAIL — " + " and ".join(failed) + " check"
            if len(failed) > 1:
                status_text += "s"
            status_style = "Fail.Status.TLabel"
        self.status_label.configure(text=status_text, style=status_style)

        self._draw_results(beam, result)

    def _draw_results(self, beam: BeamInput, result) -> None:
        self.figure.clear()
        beam_ax = self.figure.add_subplot(2, 2, 1)
        shear_ax = self.figure.add_subplot(2, 2, 2)
        moment_ax = self.figure.add_subplot(2, 2, 3)
        deflection_ax = self.figure.add_subplot(2, 2, 4)

        colors = {"brand": "#A64E32", "grid": "#dfe6ea", "ink": "#1d2b38"}
        span = beam.span_ft

        beam_ax.set_xlim(-1, span + 1)
        beam_ax.set_ylim(-1.5, 1.5)
        beam_ax.plot([0, span], [0, 0], color="#843B28", linewidth=8,
                     solid_capstyle="round")
        beam_ax.plot([0, span], [0, 0], color="#843B28", linewidth=1)
        if beam.beam_type == "simply_supported":
            beam_ax.scatter([0, span], [0, 0], marker="^", s=220,
                            color="#647585", zorder=5)
        else:
            beam_ax.plot([-0.25, -0.25], [-0.8, 0.8], color="#647585", linewidth=8)
            beam_ax.scatter([0], [0], marker="s", s=180, color="#647585", zorder=5)

        for load in beam.point_loads:
            beam_ax.annotate(
                "", xy=(load.position_ft, 0.05), xytext=(load.position_ft, 0.75),
                arrowprops=dict(arrowstyle="->", color=colors["brand"], lw=1.8),
            )
            beam_ax.text(load.position_ft, 0.9,
                         f"{load.magnitude_kip:g} kip",
                         ha="center", va="bottom", color=colors["brand"],
                         fontsize=8)
        for load in beam.uniform_loads:
            count = max(3, int((load.end_ft - load.start_ft) / 2))
            positions = np.linspace(load.start_ft, load.end_ft, count)
            for position in positions:
                beam_ax.annotate(
                    "", xy=(position, 0.05), xytext=(position, 0.55),
                    arrowprops=dict(arrowstyle="->", color=colors["brand"], lw=1.2),
                )
            beam_ax.text((load.start_ft + load.end_ft) / 2, 0.75,
                         f"{load.magnitude_kip_ft:g} kip/ft",
                         ha="center", color=colors["brand"], fontsize=8)

        beam_ax.set_title("Beam and Loads", loc="left", fontweight="bold",
                          color=colors["ink"])
        beam_ax.set_xticks([0, span])
        beam_ax.set_yticks([])
        beam_ax.grid(axis="x", color=colors["grid"])
        for side in ("top", "right", "left"):
            beam_ax.spines[side].set_visible(False)
        beam_ax.spines["bottom"].set_color(colors["grid"])

        for axis, values, title, ylabel in (
            (shear_ax, result.shear_kip, "Shear Diagram", "V (kip)"),
            (moment_ax, result.moment_kip_ft, "Moment Diagram", "M (kip-ft)"),
            (deflection_ax, result.deflection_in, "Deflection Diagram", "y (in)"),
        ):
            axis.plot(result.x_ft, values, color=colors["brand"], linewidth=2)
            axis.fill_between(result.x_ft, values, 0, color="#F3DDD3", alpha=0.8)
            axis.axhline(0, color="#647585", linewidth=0.8)
            axis.set_title(title, loc="left", fontweight="bold", color=colors["ink"])
            axis.set_xlabel("Position (ft)")
            axis.set_ylabel(ylabel)
            axis.grid(True, color=colors["grid"], linewidth=0.8)
            for side in ("top", "right"):
                axis.spines[side].set_visible(False)

        result_text = (
            f"Vmax {result.maximum_shear_kip:.2f} kip\n"
            f"Mmax {result.maximum_moment_kip_ft:.2f} kip-ft at "
            f"{result.moment_location_ft:.2f} ft\n"
            f"Bending fb {result.bending_stress_ksi:.2f} / "
            f"{result.bending_limit_ksi:.2f} ksi "
            f"{'PASS' if result.bending_pass else 'FAIL'}\n"
            f"Deflection {result.maximum_deflection_in:.3f} / "
            f"{result.deflection_limit_in:.3f} in "
            f"{'PASS' if result.deflection_pass else 'FAIL'}"
        )
        beam_ax.text(
            1.0, -0.12, result_text,
            transform=beam_ax.transAxes,
            ha="right", va="top", fontsize=8, color=colors["ink"],
        )

        self.figure.tight_layout(pad=1.5)
        self.canvas.draw_idle()


def main() -> None:
    root = tk.Tk()
    app = BeamDesignerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
