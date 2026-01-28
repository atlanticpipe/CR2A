from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors
import textwrap

def format_field_value(value):
    """Format values for display in PDF"""
    if value is None or value == "":
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        # Handle lists of strings (simple bullet points)
        if not value:
            return ""
        formatted_items = []
        for item in value:
            if isinstance(item, dict):
                # Skip dicts - they need special handling
                continue
            item_str = str(item).strip()
            if item_str and not item_str.startswith("•"):
                formatted_items.append(f"• {item_str}")
            elif item_str:
                formatted_items.append(item_str)
        return "\n".join(formatted_items) if formatted_items else ""
    if isinstance(value, dict):
        # Format dictionaries as key-value pairs
        if not value:
            return ""
        pairs = []
        for key, val in value.items():
            if val is not None and val != "":
                pairs.append(f"{key}: {val}")
        return "\n".join(pairs) if pairs else ""
    # Convert other types to string
    return str(value)

def format_redline_recommendations(recommendations):
    """Format redline recommendations which are objects with action/text/reference"""
    if not recommendations or not isinstance(recommendations, list):
        return ""
    
    formatted = []
    for item in recommendations:
        if isinstance(item, dict):
            action = item.get("action", "").upper()
            text = item.get("text", "").strip()
            reference = item.get("reference", "").strip()
            
            if text:
                line = f"[{action}] {text}"
                if reference:
                    line += f" (ref: {reference})"
                formatted.append(line)
    
    return "\n".join(formatted) if formatted else ""

def render_clause_block(content, label_prefix, clause_data, styles):
    """Render a single ClauseBlock from the schema"""
    if not clause_data or not isinstance(clause_data, dict):
        return
    
    # Fields in order as per schema
    clause_language = clause_data.get("Clause Language", "").strip()
    clause_summary = clause_data.get("Clause Summary", "").strip()
    risk_triggers = clause_data.get("Risk Triggers Identified", [])
    flow_down = clause_data.get("Flow-Down Obligations", [])
    redlines = clause_data.get("Redline Recommendations", [])
    harmful_lang = clause_data.get("Harmful Language / Policy Conflicts", [])
    
    # Only render if there's content
    has_content = any([clause_language, clause_summary, risk_triggers, flow_down, redlines, harmful_lang])
    if not has_content:
        return
    
    if clause_language:
        content.append(Paragraph("<b>Clause Language:</b>", styles['Normal']))
        content.append(Paragraph(f"&nbsp;&nbsp;<i>{clause_language}</i>", styles['Normal']))
        content.append(Spacer(1, 0.05 * inch))
    
    if clause_summary:
        content.append(Paragraph("<b>Clause Summary:</b>", styles['Normal']))
        content.append(Paragraph(f"&nbsp;&nbsp;{clause_summary}", styles['Normal']))
        content.append(Spacer(1, 0.05 * inch))
    
    if risk_triggers:
        formatted = format_field_value(risk_triggers)
        if formatted.strip():
            content.append(Paragraph("<b>Risk Triggers Identified:</b>", styles['Normal']))
            for line in formatted.split('\n'):
                if line.strip():
                    content.append(Paragraph(f"&nbsp;&nbsp;{line}", styles['Normal']))
            content.append(Spacer(1, 0.05 * inch))
    
    if flow_down:
        formatted = format_field_value(flow_down)
        if formatted.strip():
            content.append(Paragraph("<b>Flow-Down Obligations:</b>", styles['Normal']))
            for line in formatted.split('\n'):
                if line.strip():
                    content.append(Paragraph(f"&nbsp;&nbsp;{line}", styles['Normal']))
            content.append(Spacer(1, 0.05 * inch))
    
    if redlines:
        formatted = format_redline_recommendations(redlines)
        if formatted.strip():
            content.append(Paragraph("<b>Redline Recommendations:</b>", styles['Normal']))
            for line in formatted.split('\n'):
                if line.strip():
                    content.append(Paragraph(f"&nbsp;&nbsp;{line}", styles['Normal']))
            content.append(Spacer(1, 0.05 * inch))
    
    if harmful_lang:
        formatted = format_field_value(harmful_lang)
        if formatted.strip():
            content.append(Paragraph("<b>Harmful Language / Policy Conflicts:</b>", styles['Normal']))
            for line in formatted.split('\n'):
                if line.strip():
                    content.append(Paragraph(f"&nbsp;&nbsp;{line}", styles['Normal']))
            content.append(Spacer(1, 0.05 * inch))

def render_pdf(data, output_path):
    """Main PDF rendering function that matches output_schemas_v1.json structure"""
    
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
        content.append(Paragraph("I. Contract Overview", styles['Heading1']))
        content.append(Spacer(1, 0.2 * inch))
        
        overview_data = data.get("contract_overview", {})
        
        overview_fields = [
            ("Project Title:", overview_data.get("Project Title", "")),
            ("Solicitation No.:", overview_data.get("Solicitation No.", "")),
            ("Owner:", overview_data.get("Owner", "")),
            ("Contractor:", overview_data.get("Contractor", "")),
            ("Scope:", overview_data.get("Scope", "")),
            ("General Risk Level:", overview_data.get("General Risk Level", "")),
            ("Bid Model:", overview_data.get("Bid Model", "")),
            ("Notes:", overview_data.get("Notes", ""))
        ]
        
        for label, value in overview_fields:
            if value and str(value).strip():
                content.append(Paragraph(f"<b>{label}</b> {value}", styles['Normal']))
                content.append(Spacer(1, 0.1 * inch))
        
        content.append(Spacer(1, 0.2 * inch))
    except Exception as e:
        print(f"Error rendering Contract Overview: {e}")
    
    # II. Administrative & Commercial Terms Section
    try:
        content.append(Paragraph("II. Administrative & Commercial Terms", styles['Heading1']))
        content.append(Spacer(1, 0.2 * inch))
        
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
        
        admin_terms = data.get("administrative_and_commercial_terms", {})
        for subsection in subsections:
            if subsection in admin_terms:
                subsection_data = admin_terms[subsection]
                content.append(Paragraph(f"<b>{subsection}</b>", styles['Heading2']))
                content.append(Spacer(1, 0.1 * inch))
                
                render_clause_block(content, subsection, subsection_data, styles)
                content.append(Spacer(1, 0.1 * inch))
    except Exception as e:
        print(f"Error rendering Administrative & Commercial Terms: {e}")
    
    # III. Technical & Performance Terms Section
    try:
        content.append(PageBreak())
        content.append(Paragraph("III. Technical & Performance Terms", styles['Heading1']))
        content.append(Spacer(1, 0.2 * inch))
        
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
        
        tech_terms = data.get("technical_and_performance_terms", {})
        for subsection in subsections:
            if subsection in tech_terms:
                subsection_data = tech_terms[subsection]
                content.append(Paragraph(f"<b>{subsection}</b>", styles['Heading2']))
                content.append(Spacer(1, 0.1 * inch))
                
                render_clause_block(content, subsection, subsection_data, styles)
                content.append(Spacer(1, 0.1 * inch))
    except Exception as e:
        print(f"Error rendering Technical & Performance Terms: {e}")
    
    # IV. Legal Risk & Enforcement Section
    try:
        content.append(PageBreak())
        content.append(Paragraph("IV. Legal Risk & Enforcement", styles['Heading1']))
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
        
        legal_risk = data.get("legal_risk_and_enforcement", {})
        for subsection in subsections:
            if subsection in legal_risk:
                subsection_data = legal_risk[subsection]
                content.append(Paragraph(f"<b>{subsection}</b>", styles['Heading2']))
                content.append(Spacer(1, 0.1 * inch))
                
                render_clause_block(content, subsection, subsection_data, styles)
                content.append(Spacer(1, 0.1 * inch))
    except Exception as e:
        print(f"Error rendering Legal Risk & Enforcement: {e}")
    
    # V. Regulatory & Compliance Terms Section
    try:
        content.append(PageBreak())
        content.append(Paragraph("V. Regulatory & Compliance Terms", styles['Heading1']))
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
        
        regulatory_terms = data.get("regulatory_and_compliance_terms", {})
        for subsection in subsections:
            if subsection in regulatory_terms:
                subsection_data = regulatory_terms[subsection]
                content.append(Paragraph(f"<b>{subsection}</b>", styles['Heading2']))
                content.append(Spacer(1, 0.1 * inch))
                
                render_clause_block(content, subsection, subsection_data, styles)
                content.append(Spacer(1, 0.1 * inch))
    except Exception as e:
        print(f"Error rendering Regulatory & Compliance Terms: {e}")
    
    # VI. Data, Technology & Deliverables Section
    try:
        content.append(PageBreak())
        content.append(Paragraph("VI. Data, Technology & Deliverables", styles['Heading1']))
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
        
        data_tech = data.get("data_technology_and_deliverables", {})
        for subsection in subsections:
            if subsection in data_tech:
                subsection_data = data_tech[subsection]
                content.append(Paragraph(f"<b>{subsection}</b>", styles['Heading2']))
                content.append(Spacer(1, 0.1 * inch))
                
                render_clause_block(content, subsection, subsection_data, styles)
                content.append(Spacer(1, 0.1 * inch))
    except Exception as e:
        print(f"Error rendering Data, Technology & Deliverables: {e}")
    
    # VII. Supplemental Operational Risks Section
    try:
        content.append(PageBreak())
        content.append(Paragraph("VII. Supplemental Operational Risks", styles['Heading1']))
        content.append(Spacer(1, 0.2 * inch))
        
        supplemental_risks = data.get("supplemental_operational_risks", [])
        for i, risk in enumerate(supplemental_risks[:9]):  # Max 9 per schema
            content.append(Paragraph(f"<b>Supplemental Risk {i+1}</b>", styles['Heading2']))
            content.append(Spacer(1, 0.1 * inch))
            
            render_clause_block(content, f"Risk {i+1}", risk, styles)
            content.append(Spacer(1, 0.1 * inch))
    except Exception as e:
        print(f"Error rendering Supplemental Operational Risks: {e}")
    
    # VIII. Final Analysis Section
    try:
        content.append(PageBreak())
        content.append(Paragraph("VIII. Final Analysis", styles['Heading1']))
        content.append(Spacer(1, 0.2 * inch))
        
        final_analysis = data.get("final_analysis", {})
        risk_summary_data = final_analysis.get("Final Redline Risk Summary and Recommendations", [])
        
        if risk_summary_data and isinstance(risk_summary_data, list):
            content.append(Paragraph("<b>Final Redline Risk Summary and Recommendations</b>", styles['Normal']))
            content.append(Spacer(1, 0.1 * inch))
            
            # Build table data
            table_data = [["Risk Area", "Risk Summary", "APS Redline Position"]]
            
            for row in risk_summary_data:
                if isinstance(row, dict):
                    risk_area = row.get("Risk Area", "")
                    risk_summary = row.get("Risk Summary", "")
                    redline_pos = row.get("APS Redline Position", "")
                    
                    table_data.append([risk_area, risk_summary, redline_pos])
            
            if len(table_data) > 1:  # Only create table if there's data
                # Create table with proper styling
                table = Table(table_data, colWidths=[1.5*inch, 2.5*inch, 2*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
                ]))
                content.append(table)
            
            content.append(Spacer(1, 0.2 * inch))
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
    # Sample data following the output_schemas_v1.json structure
    sample_data = {
        "schema_version": "v1.0.0",
        "contract_overview": {
            "Project Title": "Highway Reconstruction Project",
            "Solicitation No.": "SOL-2024-1001",
            "Owner": "State DOT",
            "Contractor": "Smith Construction Inc.",
            "Scope": "Resurfacing 5 miles of US Route 1",
            "General Risk Level": "High",
            "Bid Model": "Unit Price",
            "Notes": "Prevailing wage required"
        },
        "administrative_and_commercial_terms": {
            "Contract Term, Renewal & Extensions": {
                "Clause Language": "The initial term shall be 18 months from the date of notice to proceed.",
                "Clause Summary": "Fixed 18-month contract with optional 6-month extensions up to 2 years total",
                "Risk Triggers Identified": [
                    "Extensions are at owner's sole discretion",
                    "No guaranteed renewal provision"
                ],
                "Flow-Down Obligations": [
                    "Pass contract term limits to subcontractors"
                ],
                "Redline Recommendations": [
                    {
                        "action": "replace",
                        "text": "Add: 'Extensions shall be offered with 30 days written notice'",
                        "reference": "APS Policy Section 3.2"
                    }
                ],
                "Harmful Language / Policy Conflicts": [
                    "Sole discretion language limits business planning certainty"
                ]
            }
        },
        "technical_and_performance_terms": {},
        "legal_risk_and_enforcement": {},
        "regulatory_and_compliance_terms": {},
        "data_technology_and_deliverables": {},
        "supplemental_operational_risks": [],
        "final_analysis": {
            "Final Redline Risk Summary and Recommendations": [
                {
                    "Risk Area": "Contract Term",
                    "Risk Summary": "18-month fixed term with discretionary extensions creates business continuity risk",
                    "APS Redline Position": "Request 2-year guaranteed term with documented extension procedure"
                }
            ]
        }
    }
    
    # Generate sample PDF
    render_pdf(sample_data, "test_contract_analysis.pdf")
    print("Test complete!")