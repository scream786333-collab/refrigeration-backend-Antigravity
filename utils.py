import pandas as pd
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io
import base64


def get_unit(key: str) -> str:
    """Return engineering unit for a given parameter key."""
    key = key.lower()
    if 'temp' in key:
        return '°C'
    if 'pressure' in key or key == 'p':
        return 'kPa'
    if 'enthalpy' in key or key == 'h':
        return 'kJ/kg'
    if 'entropy' in key or key == 's':
        return 'kJ/kg·K'
    if 'cop' in key:
        return '-'
    if 'mass_flow' in key:
        return 'kg/s'
    if 'power' in key or 'work' in key:
        return 'kW'
    if 'heat_rejected' in key:
        return 'kW'
    if 'refrigeration_effect' in key or 'cooling_capacity' in key or 'cooling_load' in key:
        return 'kW'
    if 'efficiency' in key or 'volumetric' in key:
        return '%'
    return ''


def generate_csv_data(simulation_data: dict) -> str:
    """Generate CSV-style text from simulation results (single string)."""
    state_points = simulation_data.get('state_points', {})
    performance = simulation_data.get('performance', {})
    conditions = simulation_data.get('operating_conditions', {})

    # State points
    state_data = []
    for point_id, point_data in state_points.items():
        state_data.append({
            'State Point': point_id,
            'Pressure (kPa)': point_data.get('P', 0),
            'Temperature (°C)': point_data.get('T', 0),
            'Enthalpy (kJ/kg)': point_data.get('h', 0),
            'Entropy (kJ/kg·K)': point_data.get('s', 0),
            'Quality': point_data.get('quality', 'N/A'),
        })
    state_df = pd.DataFrame(state_data)

    # Performance
    perf_data = [{
        'Parameter': key.replace('_', ' ').title(),
        'Value': value,
        'Unit': get_unit(key),
    } for key, value in performance.items()]
    perf_df = pd.DataFrame(perf_data)

    # Operating conditions
    cond_data = [{
        'Parameter': key.replace('_', ' ').title(),
        'Value': value,
        'Unit': get_unit(key),
    } for key, value in conditions.items()]
    cond_df = pd.DataFrame(cond_data)

    # Build text output
    output = "VIRTUAL REFRIGERATION SYSTEM SIMULATOR - EXPORT DATA\n"
    output += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    output += f"Refrigerant: {simulation_data.get('refrigerant', 'N/A')}\n"
    output += f"Model Type: {simulation_data.get('model_type', 'N/A')}\n\n"

    output += "STATE POINTS\n"
    output += "=" * 80 + "\n"
    output += state_df.to_string(index=False) + "\n\n"

    output += "PERFORMANCE PARAMETERS\n"
    output += "=" * 80 + "\n"
    output += perf_df.to_string(index=False) + "\n\n"

    output += "OPERATING CONDITIONS\n"
    output += "=" * 80 + "\n"
    output += cond_df.to_string(index=False) + "\n\n"

    output += "CALCULATION NOTES\n"
    output += "=" * 80 + "\n"
    output += "1. Calculations are based on simplified thermodynamic models.\n"
    output += "2. For high-accuracy design work, use detailed property libraries (e.g., CoolProp).\n"
    output += "3. COP = Refrigeration Effect / Compressor Work.\n"
    output += "4. All temperatures in °C, pressures in kPa, energy terms in kJ/kg or kW.\n"

    return output


def generate_excel_data(simulation_data: dict, filepath: str) -> None:
    """Generate an Excel file with state points, performance, and conditions."""
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        # State points
        state_data = []
        for point_id, point_data in simulation_data.get('state_points', {}).items():
            state_data.append({
                'State Point': point_id,
                'Pressure (kPa)': point_data.get('P', 0),
                'Temperature (°C)': point_data.get('T', 0),
                'Enthalpy (kJ/kg)': point_data.get('h', 0),
                'Entropy (kJ/kg·K)': point_data.get('s', 0),
                'Quality': point_data.get('quality', 'N/A'),
            })
        state_df = pd.DataFrame(state_data)
        state_df.to_excel(writer, sheet_name='State Points', index=False)

        # Performance
        perf_data = []
        for key, value in simulation_data.get('performance', {}).items():
            perf_data.append({
                'Parameter': key.replace('_', ' ').title(),
                'Value': value,
                'Unit': get_unit(key),
            })
        perf_df = pd.DataFrame(perf_data)
        perf_df.to_excel(writer, sheet_name='Performance', index=False)

        # Conditions
        cond_data = []
        for key, value in simulation_data.get('operating_conditions', {}).items():
            cond_data.append({
                'Parameter': key.replace('_', ' ').title(),
                'Value': value,
                'Unit': get_unit(key),
            })
        cond_df = pd.DataFrame(cond_data)
        cond_df.to_excel(writer, sheet_name='Conditions', index=False)

        # Summary
        perf = simulation_data.get('performance', {})
        summary_data = {
            'Refrigerant': [simulation_data.get('refrigerant', 'N/A')],
            'Model Type': [simulation_data.get('model_type', 'N/A')],
            'Timestamp': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            'COP': [perf.get('COP', 0)],
            'Cooling Capacity (kW)': [perf.get('cooling_capacity', 0)],
            'Compressor Power (kW)': [perf.get('compressor_power', 0)],
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)


def _add_chart_if_present(story, styles, charts: dict, key: str, title: str):
    """Helper: add a base64 chart (data URL) to the PDF if provided."""
    img_data_url = charts.get(key)
    if not img_data_url:
        return
    try:
        if img_data_url.startswith('data:image'):
            header, b64data = img_data_url.split(',', 1)
        else:
            b64data = img_data_url

        img_bytes = base64.b64decode(b64data)
        buf = io.BytesIO(img_bytes)

        story.append(Paragraph(title, styles['Heading2']))
        img = RLImage(buf, width=6 * inch, height=3.5 * inch)
        story.append(img)
        story.append(Spacer(1, 12))
    except Exception:
        # If chart decoding fails, ignore silently
        pass


def generate_pdf_report(simulation_data: dict, filepath: str) -> None:
    """Generate a nicely formatted PDF report from simulation data."""
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Custom title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        alignment=1,  # center
        spaceAfter=20,
    )

    # Header
    story.append(Paragraph("Virtual Refrigeration System Simulator", title_style))
    story.append(Paragraph(
        f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        styles['Normal']
    ))
    story.append(Spacer(1, 12))

    # System information
    story.append(Paragraph("System Information", styles['Heading2']))

    oc = simulation_data.get('operating_conditions', {})
    info_data = [
        ['Refrigerant:', simulation_data.get('refrigerant', 'N/A')],
        ['Model Type:', simulation_data.get('model_type', 'N/A')],
        ['Evaporator Temperature:', f"{oc.get('evaporator_temp', 0):.2f} °C"],
        ['Condenser Temperature:', f"{oc.get('condenser_temp', 0):.2f} °C"],
        ['Superheating:', f"{oc.get('superheat', 0):.2f} °C"],
        ['Subcooling:', f"{oc.get('subcool', 0):.2f} °C"],
        ['Compressor Efficiency:', f"{oc.get('compressor_efficiency', 0):.1f} %"],
    ]

    info_table = Table(info_data, colWidths=[2.2 * inch, 3.3 * inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 18))

    # State points
    story.append(Paragraph("Cycle State Points", styles['Heading2']))

    state_points = simulation_data.get('state_points', {})
    state_data = [['Point', 'P (kPa)', 'T (°C)', 'h (kJ/kg)', 's (kJ/kg·K)', 'Quality']]
    for pid in ['1', '2', '3', '4']:
        p = state_points.get(pid, {})
        state_data.append([
            pid,
            f"{p.get('P', 0):.2f}",
            f"{p.get('T', 0):.2f}",
            f"{p.get('h', 0):.2f}",
            f"{p.get('s', 0):.3f}",
            'N/A' if p.get('quality') is None else f"{p.get('quality'):.3f}",
        ])

    state_table = Table(
        state_data,
        colWidths=[0.6 * inch, 1.0 * inch, 1.0 * inch, 1.1 * inch, 1.1 * inch, 1.0 * inch]
    )
    state_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(state_table)
    story.append(Spacer(1, 18))

    # Performance
    story.append(Paragraph("Performance Parameters", styles['Heading2']))

    perf = simulation_data.get('performance', {})
    perf_data = [['Parameter', 'Value', 'Unit']]
    for key, val in perf.items():
        perf_data.append([
            key.replace('_', ' ').title(),
            f"{val}",
            get_unit(key),
        ])

    perf_table = Table(
        perf_data,
        colWidths=[2.5 * inch, 1.5 * inch, 0.8 * inch]
    )
    perf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(perf_table)
    story.append(Spacer(1, 18))

    # Charts if provided (base64 data URLs from /calculate or frontend)
    charts = simulation_data.get('charts', {})
    if charts:
        _add_chart_if_present(story, styles, charts, 'ph_diagram', 'Pressure-Enthalpy (P-h) Diagram')
        _add_chart_if_present(story, styles, charts, 'ts_diagram', 'Temperature-Entropy (T-s) Diagram')

    # Conclusion / notes
    story.append(Paragraph("Remarks & Conclusions", styles['Heading2']))
    story.append(Paragraph(
        "This report summarizes the simulated thermodynamic cycle for the selected "
        "refrigeration system. The results are based on simplified property models "
        "and are intended for educational and comparative analysis. For detailed "
        "design work, validated property libraries (e.g., CoolProp) and more "
        "refined models should be used.",
        styles['Normal']
    ))
    story.append(Spacer(1, 12))

    doc.build(story)