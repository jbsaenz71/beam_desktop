# Beam Designer

## Platform
- Python desktop app using Tkinter, started with `python app.py`
- Calculations with numpy, kept in their own module, separate from
  the window code
- Diagrams drawn with matplotlib, embedded in the window

## Purpose
Shear, moment, and deflection diagrams for a beam, with a check of
whether the beam is strong and stiff enough.

## Inputs
- Simply supported or cantilever, and the span (ft)
- Point loads and uniform loads
- A steel W-shape or a lumber size

## Calculations
- Reactions, shear, and moment from statics
- Deflection
- Bending stress fb = M/S, compared to the allowable stress
- Deflection compared to L/360

## Outputs
- The beam with its loads, and the three diagrams
- Pass or fail for bending and deflection
- An Export Results button that saves a CSV file compatible with Excel,
  with one row per analysis sample point and columns `x_ft`, `V_kip`,
  `M_kip_ft`, and `deflection_in`.
- An Export Calculation Sheet button that saves a PDF with the beam inputs
  (support type, span, section, deflection limit, and all loads) at the top,
  followed by the beam/load diagram, shear, moment, and deflection diagrams,
  and bending and deflection check results. The sheet should be suitable to
  hand in with a design.

## Look and feel
Clean and professional, with an example beam loaded when it opens.
Inputs in a panel on the left, the beam and diagrams on the right, and a window that can be resized. Remove the lines about phones.
- Include a File menu with Save and Open commands.

## File storage
- Save beam designs to a file.
- Saved data includes support type, span, section, deflection limit,
  point loads, and uniform loads.
- Open a saved file and restore all of those beam inputs.

## Validation
Simply supported, 30 ft, W18x35, uniform 2 kips/ft from 0 to 15 ft
only: reactions 22.5 k (left) and 7.5 k (right); max moment
126.6 kip-ft at 11.25 ft.

## Out of scope
Continuous beams and buckling.