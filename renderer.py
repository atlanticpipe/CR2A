"""
PDF Renderer for Contract Analysis Reports

This module provides PDF generation functionality using reportlab library
to create contract risk and compliance summary reports following the exact
template structure defined in the Clause Risk & Compliance Summary template.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
import textwrap


def format_field_value(value):
    """
    Format different data types for display in PDF.

    Args:
        value: The value to format (string, list, dict, or None)

    Returns:
        str: Formatted string representation of the value
    """
    if value is None or value == "":
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        # Format arrays as bullet points
        if not value:
            return ""
        return "\n".join(f"• {item}" if not str(item).startswith("•") else str(item) for item in value)

    if isinstance(value, dict):
        # Format dictionaries as key-value pairs
        if not value:
            return ""
        pairs = []
        for key, val in value.items():
            if val is not None and val != "":
                pairs.append(f"{key}: {val}")
        return "\n".join(pairs)

    # Convert other types to string
    return str(value)


def add_section_heading(canvas, text, y_position):
    """
    Add a section heading to the PDF.

    Args:
        canvas: ReportLab canvas object
        text: Heading text
        y_position: Current Y position on the page

    Returns:
        float: Updated Y position after adding the heading
    """
    # Set font for heading
    canvas.setFont("Helvetica-Bold", 14)

    # Draw the heading
    canvas.drawString(0.5 * inch, y_position, text)

    # Return updated Y position (heading takes about 20 points)
    return y_position - 25


def add_field_label_and_value(canvas, label, value, y_position, max_width=6.5):
    """
    Add a field label and its value to the PDF with proper formatting.

    Args:
        canvas: ReportLab canvas object
        label: Field label text
        value: Field value (will be formatted by format_field_value)
        y_position: Current Y position on the page
        max_width: Maximum width for text wrapping in inches

    Returns:
        float: Updated Y position after adding the field
    """
    formatted_value = format_field_value(value)

    if not formatted_value.strip():
        # No value to display, just return current position
        return y_position

    # Set font for label (bold)
    canvas.setFont("Helvetica-Bold", 10)

    # Draw label
    canvas.drawString(0.5 * inch, y_position, label)

    # Move down for value
    value_y = y_position - 15
    canvas.setFont("Helvetica", 9)

    # Handle long text with wrapping
    if len(formatted_value) > 100:
        # Wrap long text
        wrapped_lines = textwrap.wrap(formatted_value, width=80)
        for i, line in enumerate(wrapped_lines):
            if value_y < 0.5 * inch:  # Check if we need a new page
                canvas.showPage()
                value_y = 10 * inch

            canvas.drawString(0.6 * inch, value_y, line)
            value_y -= 12

        return value_y - 5  # Extra space after wrapped text
    else:
        # Single line value
        if value_y < 0.5 * inch:  # Check if we need a new page
            canvas.showPage()
            value_y = 10 * inch

        canvas.drawString(0.6 * inch, value_y, formatted_value)
        return value_y - 20  # Space after field


def render_pdf(data, output_path):
    """
    Main PDF generation function that creates a contract analysis report
    following the exact template structure.

    Args:
        data: Dictionary containing all contract analysis data
        output_path: File path where the PDF will be saved

    Returns:
        None
    """
    # Create document template
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch
    )

    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=16,
        spaceAfter=20,
        alignment=TA_CENTER
    )

    # Build PDF content
    content = []

    # Title
    title = Paragraph("Clause Risk & Compliance Summary", title_style)
    content.append(title)
    content.append(Spacer(1, 0.3 * inch))

    # I. Contract Overview Section
    try:
        content.append(Paragraph("<b>I. Contract Overview</b>", styles['Heading1']))
        content.append(Spacer(1, 0.2 * inch))

        # Contract Overview fields - use exact field names from schema
        overview_fields = [
            ("Project Title:", data.get("Project Title", "")),
            ("Solicitation No.:", data.get("Solicitation No.", "")),
            ("Owner:", data.get("Owner", "")),
            ("Contractor:", data.get("Contractor", "")),
            ("Scope:", data.get("Scope", "")),
            ("General Risk Level:", data.get("General Risk Level", "")),
            ("Bid Model:", data.get("Bid Model", "")),
            ("Notes:", data.get("Notes", ""))
        ]

        for label, value in overview_fields:
            formatted_value = format_field_value(value)
            if formatted_value.strip():
                content.append(Paragraph(f"<b>{label}</b> {formatted_value}", styles['Normal']))
                content.append(Spacer(1, 0.1 * inch))

        content.append(Spacer(1, 0.2 * inch))

    except Exception as e:
        print(f"Error rendering Contract Overview: {e}")

    # II. Administrative & Commercial Terms Section
    try:
        content.append(Paragraph("<b>II. Administrative & Commercial Terms</b>", styles['Heading1']))
        content.append(Spacer(1, 0.2 * inch))

        # Define all subsections for Administrative & Commercial Terms
        subsections = [
            "Contract Term, Renewal & Extensions",
            "Bonding, Surety, & Insurance Obligations",
            "Retainage, Progress Payments & Final Payment Terms",
            "Pay-When-Paid, Pay-If-Paid, or Owner Payment Contingencies",
            "Price Escalation Clauses (Labor, Materials, Fuel, Inflation Adjustments)",
            "Fuel Price Adjustment / Fuel Cost Caps",
            "Change Orders, Scope Adjustments & Modifications",
            "Termination for Convenience (Owner/Agency Right to Terminate Without Cause)",
            "Termination for Cause / Default by Contractor",
            "Bid Protest Procedures & Claims of Improper Award",
            "Bid Tabulation, Competition & Award Process Requirements",
            "Contractor Qualification, Licensing & Certification Requirements",
            "Release Orders, Task Orders & Work Authorization Protocols",
            "Assignment & Novation Restrictions (Transfer of Contract Rights)",
            "Audit Rights, Recordkeeping & Document Retention Obligations",
            "Notice Requirements & Claim Timeframes (Notice to Cure, Delay Notices, Termination Notices, etc.)"
        ]

        for subsection in subsections:
            content.append(Paragraph(f"<b>{subsection}</b>", styles['Heading2']))
            content.append(Spacer(1, 0.1 * inch))

            # Get subsection data
            subsection_key = subsection.lower().replace(", ", "_").replace(" ", "_").replace("&", "and")
            subsection_data = data.get("administrative_commercial", {}).get(subsection_key, {})

            # Add each field for the subsection
            fields = [
                ("Clause Language:", subsection_data.get("Clause Language", "")),
                ("Clause Summary:", subsection_data.get("Clause Summary", "")),
                ("Risk Triggers Identified:", subsection_data.get("Risk Triggers Identified", [])),
                ("Flow-Down Obligations:", subsection_data.get("Flow-Down Obligations", [])),
                ("Redline Recommendations:", subsection_data.get("Redline Recommendations", [])),
                ("Harmful Language / Policy Conflicts:", subsection_data.get("Harmful Language / Policy Conflicts", []))
            ]

            for label, value in fields:
                formatted_value = format_field_value(value)
                if formatted_value.strip():
                    content.append(Paragraph(f"<b>{label}</b>", styles['Normal']))
                    # Handle multi-line content
                    if '\n' in formatted_value:
                        for line in formatted_value.split('\n'):
                            if line.strip():
                                content.append(Paragraph(f"  {line}", styles['Normal']))
                    else:
                        content.append(Paragraph(f"  {formatted_value}", styles['Normal']))
                    content.append(Spacer(1, 0.05 * inch))

            content.append(Spacer(1, 0.1 * inch))

    except Exception as e:
        print(f"Error rendering Administrative & Commercial Terms: {e}")

    # III. Technical & Performance Terms Section
    try:
        content.append(PageBreak())
        content.append(Paragraph("<b>III. Technical & Performance Terms</b>", styles['Heading1']))
        content.append(Spacer(1, 0.2 * inch))

        # Define subsections for Technical & Performance Terms
        subsections = [
            "Scope of Work (Work Inclusions, Exclusions & Defined Deliverables)",
            "Performance Schedule, Time for Completion & Critical Path Obligations",
            "Delays of Any Kind (Force Majeure, Acts of God, Weather, Owner-Caused, Unforeseen Events)",
            "Suspension of Work, Work Stoppages & Agency Directives",
            "Submittals, Documentation & Approval Requirements",
            "Emergency & Contingency Work Obligations",
            "Permits, Licensing & Regulatory Approvals for Work",
            "Warranty, Guarantee & Defects Liability Periods",
            "Use of APS Tools, Equipment, Materials or Supplies",
            "Owner-Supplied Support, Utilities & Site Access Provisions",
            "Field Ticket, Daily Work Log & Documentation Requirements",
            "Mobilization & Demobilization Provisions",
            "Utility Coordination, Locate Risk & Conflict Avoidance",
            "Delivery Deadlines, Milestone Dates, Substantial & Final Completion Standards",
            "Punch List, Closeout Procedures & Acceptance of Work",
            "Worksite Coordination, Access Restrictions & Sequencing Obligations",
            "Deliverables, Digital Submissions & Documentation Standards"
        ]

        for subsection in subsections:
            content.append(Paragraph(f"<b>{subsection}</b>", styles['Heading2']))
            content.append(Spacer(1, 0.1 * inch))

            subsection_key = subsection.lower().replace(", ", "_").replace(" ", "_").replace("&", "and")
            subsection_data = data.get("technical_performance", {}).get(subsection_key, {})

            fields = [
                ("Clause Language:", subsection_data.get("Clause Language", "")),
                ("Clause Summary:", subsection_data.get("Clause Summary", "")),
                ("Risk Triggers Identified:", subsection_data.get("Risk Triggers Identified", [])),
                ("Flow-Down Obligations:", subsection_data.get("Flow-Down Obligations", [])),
                ("Redline Recommendations:", subsection_data.get("Redline Recommendations", [])),
                ("Harmful Language / Policy Conflicts:", subsection_data.get("Harmful Language / Policy Conflicts", []))
            ]

            for label, value in fields:
                formatted_value = format_field_value(value)
                if formatted_value.strip():
                    content.append(Paragraph(f"<b>{label}</b>", styles['Normal']))
                    if '\n' in formatted_value:
                        for line in formatted_value.split('\n'):
                            if line.strip():
                                content.append(Paragraph(f"  {line}", styles['Normal']))
                    else:
                        content.append(Paragraph(f"  {formatted_value}", styles['Normal']))
                    content.append(Spacer(1, 0.05 * inch))

            content.append(Spacer(1, 0.1 * inch))

    except Exception as e:
        print(f"Error rendering Technical & Performance Terms: {e}")

    # IV. Legal Risk & Enforcement Section
    try:
        content.append(PageBreak())
        content.append(Paragraph("<b>IV. Legal Risk & Enforcement</b>", styles['Heading1']))
        content.append(Spacer(1, 0.2 * inch))

        subsections = [
            "Indemnification, Defense & Hold Harmless Provisions",
            "Duty to Defend vs. Indemnify Scope Clarifications",
            "Limitations of Liability, Damage Caps & Waivers of Consequential Damages",
            "Insurance Coverage, Additional Insured & Waiver of Subrogation Clauses",
            "Dispute Resolution (Mediation, Arbitration, Litigation)",
            "Flow-Down Clauses (Prime-to-Subcontract Risk Pass-Through)",
            "Subcontracting Restrictions, Approval & Substitution Requirements",
            "Background Screening, Security Clearance & Worker Eligibility Requirements",
            "Safety Standards, OSHA Compliance & Site-Specific Safety Obligations",
            "Site Conditions, Differing Site Conditions & Changed Circumstances Clauses",
            "Environmental Hazards, Waste Disposal & Hazardous Materials Provisions",
            "Conflicting Documents / Order of Precedence Clauses",
            "Setoff & Withholding Rights (Owner's Right to Deduct or Withhold Payment)"
        ]

        for subsection in subsections:
            content.append(Paragraph(f"<b>{subsection}</b>", styles['Heading2']))
            content.append(Spacer(1, 0.1 * inch))

            subsection_key = subsection.lower().replace(", ", "_").replace(" ", "_").replace("&", "and")
            subsection_data = data.get("legal_risk", {}).get(subsection_key, {})

            fields = [
                ("Clause Language:", subsection_data.get("Clause Language", "")),
                ("Clause Summary:", subsection_data.get("Clause Summary", "")),
                ("Risk Triggers Identified:", subsection_data.get("Risk Triggers Identified", [])),
                ("Flow-Down Obligations:", subsection_data.get("Flow-Down Obligations", [])),
                ("Redline Recommendations:", subsection_data.get("Redline Recommendations", [])),
                ("Harmful Language / Policy Conflicts:", subsection_data.get("Harmful Language / Policy Conflicts", []))
            ]

            for label, value in fields:
                formatted_value = format_field_value(value)
                if formatted_value.strip():
                    content.append(Paragraph(f"<b>{label}</b>", styles['Normal']))
                    if '\n' in formatted_value:
                        for line in formatted_value.split('\n'):
                            if line.strip():
                                content.append(Paragraph(f"  {line}", styles['Normal']))
                    else:
                        content.append(Paragraph(f"  {formatted_value}", styles['Normal']))
                    content.append(Spacer(1, 0.05 * inch))

            content.append(Spacer(1, 0.1 * inch))

    except Exception as e:
        print(f"Error rendering Legal Risk & Enforcement: {e}")

    # V. Regulatory & Compliance Terms Section
    try:
        content.append(PageBreak())
        content.append(Paragraph("<b>V. Regulatory & Compliance Terms</b>", styles['Heading1']))
        content.append(Spacer(1, 0.2 * inch))

        subsections = [
            "Certified Payroll, Recordkeeping & Reporting Obligations",
            "Prevailing Wage, Davis-Bacon & Federal/State Wage Compliance",
            "EEO, Non-Discrimination, MWBE/DBE Participation Requirements",
            "Anti-Lobbying / Cone of Silence Provisions",
            "Apprenticeship, Training & Workforce Development Requirements",
            "Immigration / E-Verify Compliance Obligations",
            "Worker Classification & Independent Contractor Restrictions",
            "Drug-Free Workplace Programs & Substance Testing Requirements"
        ]

        for subsection in subsections:
            content.append(Paragraph(f"<b>{subsection}</b>", styles['Heading2']))
            content.append(Spacer(1, 0.1 * inch))

            subsection_key = subsection.lower().replace(", ", "_").replace(" ", "_").replace("&", "and").replace("/", "_")
            subsection_data = data.get("regulatory_compliance", {}).get(subsection_key, {})

            fields = [
                ("Clause Language:", subsection_data.get("Clause Language", "")),
                ("Clause Summary:", subsection_data.get("Clause Summary", "")),
                ("Risk Triggers Identified:", subsection_data.get("Risk Triggers Identified", [])),
                ("Flow-Down Obligations:", subsection_data.get("Flow-Down Obligations", [])),
                ("Redline Recommendations:", subsection_data.get("Redline Recommendations", [])),
                ("Harmful Language / Policy Conflicts:", subsection_data.get("Harmful Language / Policy Conflicts", []))
            ]

            for label, value in fields:
                formatted_value = format_field_value(value)
                if formatted_value.strip():
                    content.append(Paragraph(f"<b>{label}</b>", styles['Normal']))
                    if '\n' in formatted_value:
                        for line in formatted_value.split('\n'):
                            if line.strip():
                                content.append(Paragraph(f"  {line}", styles['Normal']))
                    else:
                        content.append(Paragraph(f"  {formatted_value}", styles['Normal']))
                    content.append(Spacer(1, 0.05 * inch))

            content.append(Spacer(1, 0.1 * inch))

    except Exception as e:
        print(f"Error rendering Regulatory & Compliance Terms: {e}")

    # VI. Data, Technology & Deliverables Section
    try:
        content.append(PageBreak())
        content.append(Paragraph("<b>VI. Data, Technology & Deliverables</b>", styles['Heading1']))
        content.append(Spacer(1, 0.2 * inch))

        subsections = [
            "Data Ownership, Access & Rights to Digital Deliverables",
            "AI / Technology Use Restrictions (Automation, Digital Tools, Proprietary Systems)",
            "Digital Surveillance, GIS-Tagged Deliverables & Monitoring Requirements",
            "GIS, Digital Workflow Integration & Electronic Submittals",
            "Confidentiality, Data Security & Records Retention Obligations",
            "Intellectual Property, Licensing & Ownership of Work Product",
            "Cybersecurity Standards, Breach Notification & IT System Use Policies"
        ]

        for subsection in subsections:
            content.append(Paragraph(f"<b>{subsection}</b>", styles['Heading2']))
            content.append(Spacer(1, 0.1 * inch))

            subsection_key = subsection.lower().replace(", ", "_").replace(" ", "_").replace("&", "and").replace("/", "_")
            subsection_data = data.get("data_technology", {}).get(subsection_key, {})

            fields = [
                ("Clause Language:", subsection_data.get("Clause Language", "")),
                ("Clause Summary:", subsection_data.get("Clause Summary", "")),
                ("Risk Triggers Identified:", subsection_data.get("Risk Triggers Identified", [])),
                ("Flow-Down Obligations:", subsection_data.get("Flow-Down Obligations", [])),
                ("Redline Recommendations:", subsection_data.get("Redline Recommendations", [])),
                ("Harmful Language / Policy Conflicts:", subsection_data.get("Harmful Language / Policy Conflicts", []))
            ]

            for label, value in fields:
                formatted_value = format_field_value(value)
                if formatted_value.strip():
                    content.append(Paragraph(f"<b>{label}</b>", styles['Normal']))
                    if '\n' in formatted_value:
                        for line in formatted_value.split('\n'):
                            if line.strip():
                                content.append(Paragraph(f"  {line}", styles['Normal']))
                    else:
                        content.append(Paragraph(f"  {formatted_value}", styles['Normal']))
                    content.append(Spacer(1, 0.05 * inch))

            content.append(Spacer(1, 0.1 * inch))

    except Exception as e:
        print(f"Error rendering Data, Technology & Deliverables: {e}")

    # VII. Supplemental Operational Risks Section
    try:
        content.append(PageBreak())
        content.append(Paragraph("<b>VII. Supplemental Operational Risks</b>", styles['Heading1']))
        content.append(Spacer(1, 0.2 * inch))

        # This section appears to have multiple blank subsections in the template
        # We'll handle up to 10 supplemental risk entries
        supplemental_risks = data.get("supplemental_risks", [])

        for i, risk in enumerate(supplemental_risks[:10]):  # Limit to 10 to prevent overflow
            content.append(Paragraph(f"<b>Supplemental Risk {i+1}</b>", styles['Heading2']))
            content.append(Spacer(1, 0.1 * inch))

            fields = [
                ("Clause Language:", risk.get("Clause Language", "")),
                ("Clause Summary:", risk.get("Clause Summary", "")),
                ("Risk Triggers Identified:", risk.get("Risk Triggers Identified", [])),
                ("Flow-Down Obligations:", risk.get("Flow-Down Obligations", [])),
                ("Redline Recommendations:", risk.get("Redline Recommendations", [])),
                ("Harmful Language / Policy Conflicts:", risk.get("Harmful Language / Policy Conflicts", []))
            ]

            for label, value in fields:
                formatted_value = format_field_value(value)
                if formatted_value.strip():
                    content.append(Paragraph(f"<b>{label}</b>", styles['Normal']))
                    if '\n' in formatted_value:
                        for line in formatted_value.split('\n'):
                            if line.strip():
                                content.append(Paragraph(f"  {line}", styles['Normal']))
                    else:
                        content.append(Paragraph(f"  {formatted_value}", styles['Normal']))
                    content.append(Spacer(1, 0.05 * inch))

            content.append(Spacer(1, 0.1 * inch))

    except Exception as e:
        print(f"Error rendering Supplemental Operational Risks: {e}")

    # VIII. Final Analysis Section
    try:
        content.append(PageBreak())
        content.append(Paragraph("<b>VIII. Final Analysis</b>", styles['Heading1']))
        content.append(Spacer(1, 0.2 * inch))

        content.append(Paragraph("<b>Final Redline Risk Summary and Recommendations</b>", styles['Heading2']))
        content.append(Spacer(1, 0.1 * inch))

        # Table headers
        content.append(Paragraph("<b>Risk Area</b>", styles['Normal']))
        content.append(Spacer(1, 0.05 * inch))
        content.append(Paragraph("<b>Risk Summary</b>", styles['Normal']))
        content.append(Spacer(1, 0.05 * inch))
        content.append(Paragraph("<b>APS Redline Position</b>", styles['Normal']))
        content.append(Spacer(1, 0.1 * inch))

        # Get final analysis data
        final_analysis = data.get("final_analysis", {}).get("Final Redline Risk Summary and Recommendations", [])

        for item in final_analysis:
            risk_area = format_field_value(item.get("Risk Area", ""))
            risk_summary = format_field_value(item.get("Risk Summary", ""))
            redline_position = format_field_value(item.get("APS Redline Position", ""))

            if risk_area.strip():
                content.append(Paragraph(f"<b>Risk Area:</b> {risk_area}", styles['Normal']))
            if risk_summary.strip():
                content.append(Paragraph(f"<b>Risk Summary:</b> {risk_summary}", styles['Normal']))
            if redline_position.strip():
                content.append(Paragraph(f"<b>APS Redline Position:</b> {redline_position}", styles['Normal']))
            content.append(Spacer(1, 0.1 * inch))

    except Exception as e:
        print(f"Error rendering Final Analysis: {e}")

    # Build PDF
    try:
        doc.build(content)
        print(f"PDF successfully generated: {output_path}")
    except Exception as e:
        print(f"Error building PDF: {e}")
        raise


# Example usage and testing
if __name__ == "__main__":
    # Sample data for testing
    sample_data = {
        "Project Title": "Sample Construction Project",
        "Solicitation No.": "SOL-2024-001",
        "Owner": "City of Sample",
        "Contractor": "ABC Construction LLC",
        "Scope": "Construction of municipal building",
        "General Risk Level": "Medium",
        "Bid Model": "Competitive Bid",
        "Notes": "This is a test contract for PDF generation"
    }

    # Generate sample PDF
    render_pdf(sample_data, "test_contract_analysis.pdf")