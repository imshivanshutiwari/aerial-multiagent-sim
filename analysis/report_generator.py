"""PDF research report generator using ReportLab.

Generates a 4-page PDF:
  Page 1: Title, abstract
  Page 2: Methods
  Page 3: Results (figures)
  Page 4: Key findings, limitations, references
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak,
    )
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


def generate_report(
    output_path: str,
    summary: Dict,
    figure_paths: Optional[Dict[str, str]] = None,
) -> str:
    """Generate the research report PDF.

    Parameters
    ----------
    output_path : str
        Where to save the PDF.
    summary : dict
        Analysis summary dict with key metrics.
    figure_paths : dict[str, str] | None
        Optional dict of figure name → file path for embedding.

    Returns
    -------
    str
        Path to the generated PDF.
    """
    if not HAS_REPORTLAB:
        return "ERROR: reportlab not installed. pip install reportlab"

    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle", parent=styles["Title"],
        fontSize=22, spaceAfter=30,
    )
    heading_style = ParagraphStyle(
        "CustomHeading", parent=styles["Heading2"],
        fontSize=14, spaceAfter=12,
    )
    body_style = styles["BodyText"]

    content = []

    # ---- Page 1: Title + Abstract ----
    content.append(Paragraph(
        "Beyond Visual Range Air Combat AI Agent Simulator:<br/>"
        "Multi-Ship BVR Mission Analysis",
        title_style,
    ))
    content.append(Spacer(1, 1 * cm))

    abstract = (
        f"This report presents the results of a BVR air combat simulation "
        f"between autonomous AI agents. Using a physics-based model with "
        f"Swerling Type-1 radar detection, proportional navigation missile "
        f"guidance, and a 5-step AI decision cycle, we evaluate Blue force "
        f"tactics against a Red force of comparable capability. "
        f"Monte Carlo analysis over multiple replications yields a mean "
        f"kill ratio of {summary.get('mean_kill_ratio', 'N/A'):.2f} with "
        f"P(Blue wins) = {summary.get('p_blue_wins', 'N/A'):.3f}. "
        f"Statistical comparison using Mann-Whitney U tests identifies "
        f"the dominant formation tactic and minimum viable force size."
    )
    content.append(Paragraph("<b>Abstract.</b> " + abstract, body_style))
    content.append(PageBreak())

    # ---- Page 2: Methods ----
    content.append(Paragraph("Methods", heading_style))

    methods = (
        "<b>Simulation Architecture.</b> Point-mass 2D aircraft dynamics with "
        "radar, ECM, and missile subsystems. Each aircraft carries 4 active "
        "radar homing missiles with PN guidance (N=4).<br/><br/>"
        "<b>Physics Model.</b> Radar: P_detect = 1 - exp(-(R_max/R)^4). "
        "Missile phases: boost (3s, 30 m/s²), midcourse (inertial to intercept), "
        "terminal (PN guidance). Kill probability: 0.85 within 30m, exponential "
        "decay to 100m.<br/><br/>"
        "<b>AI Decision Logic.</b> 5-step cycle every 2s: (1) threat assessment, "
        "(2) missile defense (notch + chaff), (3) engagement decision (fire if "
        "PK > 0.55, deconflicted), (4) utility-based positioning, "
        "(5) formation keeping (Blue only).<br/><br/>"
        "<b>Monte Carlo.</b> N replications with independent seeds, parallel "
        "execution via multiprocessing.Pool."
    )
    content.append(Paragraph(methods, body_style))
    content.append(PageBreak())

    # ---- Page 3: Results ----
    content.append(Paragraph("Results", heading_style))
    if figure_paths:
        for fig_name, fig_path in figure_paths.items():
            if Path(fig_path).exists():
                content.append(Paragraph(f"<i>{fig_name}</i>", body_style))
                content.append(Image(fig_path, width=14 * cm, height=8 * cm))
                content.append(Spacer(1, 0.5 * cm))
    else:
        content.append(Paragraph(
            "Figures are available in the Streamlit dashboard.", body_style
        ))

    content.append(PageBreak())

    # ---- Page 4: Findings + Limitations ----
    content.append(Paragraph("Key Findings", heading_style))
    kf = (
        f"Mean kill ratio: {summary.get('mean_kill_ratio', 'N/A'):.2f}. "
        f"P(Blue wins): {summary.get('p_blue_wins', 'N/A'):.3f}. "
        f"Mean engagement duration: {summary.get('mean_duration_sec', 'N/A'):.0f}s."
    )
    content.append(Paragraph(kf, body_style))
    content.append(Spacer(1, 0.5 * cm))

    content.append(Paragraph("Limitations", heading_style))
    lims = (
        "2D model only (no altitude). Simplified aerodynamics (point mass). "
        "No terrain masking. No AWACS. No electronic warfare beyond basic "
        "jamming and chaff. No multi-target missile capability."
    )
    content.append(Paragraph(lims, body_style))
    content.append(Spacer(1, 0.5 * cm))

    content.append(Paragraph("References", heading_style))
    refs = (
        "1. Lockheed Martin DARPA AIR Program Press Release.<br/>"
        "2. Mahafza, B.R. — Radar Systems Analysis and Design Using MATLAB.<br/>"
        "3. Zarchan, P. — Tactical and Strategic Missile Guidance, 6th Ed."
    )
    content.append(Paragraph(refs, body_style))

    doc.build(content)
    return output_path
