from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors

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

def has_clause_content(clause_data):
    """Check if a ClauseBlock has any actual content"""
    if not clause_data or not isinstance(clause_data, dict):
        return False
    
    return any([
        clause_data.get("Clause Language", "").strip(),
        clause_data.get("Clause Summary", "").strip(),
        clause_data.get("Risk Triggers Identified", []),
        clause_data.get("Flow-Down Obligations", []),
        clause_data.get("Redline Recommendations", []),
        clause_data.get("Harmful Language / Policy Conflicts", [])
    ])

def render_clause_block(content, clause_data, styles):
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
    """Data-driven PDF renderer - renders JSON structure as-is without hardcoded template"""
    
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
    
    # Define section order (in case you want it, but actually render what's in data)
    section_names = {
        "contract_overview": "I. Contract Overview",
        "administrative_and_commercial_terms": "II. Administrative & Commercial Terms",
        "technical_and_performance_terms": "III. Technical & Performance Terms",
        "legal_risk_and_enforcement": "IV. Legal Risk & Enforcement",
        "regulatory_and_compliance_terms": "V. Regulatory & Compliance Terms",
        "data_technology_and_deliverables": "VI. Data, Technology & Deliverables",
        "supplemental_operational_risks": "VII. Supplemental Operational Risks",
        "final_analysis": "VIII. Final Analysis"
    }
    
    # Iterate through section_names to maintain order, but only render if data exists
    first_section = True
    
    for section_key, section_title in section_names.items():
        section_data = data.get(section_key)
        
        # Skip sections that don't exist or are empty
        if section_data is None or (isinstance(section_data, (dict, list)) and not section_data):
            continue
        
        # Add page break before sections (except first)
        if not first_section:
            content.append(PageBreak())
        first_section = False
        
        try:
            # Render section title
            content.append(Paragraph(section_title, styles['Heading1']))
            content.append(Spacer(1, 0.2 * inch))
            
            # Handle special cases
            if section_key == "contract_overview":
                # Contract overview is simple key-value pairs
                if isinstance(section_data, dict):
                    for key, value in section_data.items():
                        if value and str(value).strip():
                            content.append(Paragraph(f"<b>{key}:</b> {value}", styles['Normal']))
                            content.append(Spacer(1, 0.1 * inch))
            
            elif section_key == "supplemental_operational_risks":
                # Supplemental risks is an array of ClauseBlocks
                if isinstance(section_data, list):
                    for i, risk_item in enumerate(section_data[:9]):
                        if not has_clause_content(risk_item):
                            continue
                        
                        content.append(Paragraph(f"<b>Supplemental Risk {i+1}</b>", styles['Heading2']))
                        content.append(Spacer(1, 0.1 * inch))
                        render_clause_block(content, risk_item, styles)
                        content.append(Spacer(1, 0.1 * inch))
            
            elif section_key == "final_analysis":
                # Final analysis is a special structure with a table
                risk_summary_data = section_data.get("Final Redline Risk Summary and Recommendations", [])
                
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
                            
                            if any([risk_area, risk_summary, redline_pos]):
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
            
            else:
                # Standard sections with subsections containing ClauseBlocks
                if isinstance(section_data, dict):
                    for subsection_key, subsection_item in section_data.items():
                        if not has_clause_content(subsection_item):
                            continue
                        
                        # Render subsection header only if there's content
                        content.append(Paragraph(f"<b>{subsection_key}</b>", styles['Heading2']))
                        content.append(Spacer(1, 0.1 * inch))
                        
                        render_clause_block(content, subsection_item, styles)
                        content.append(Spacer(1, 0.1 * inch))
        
        except Exception as e:
            print(f"Error rendering {section_title}: {e}")
    
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
            },
            "Bonding, Surety, & Insurance Obligations": {}
        },
        "technical_and_performance_terms": {
            "Scope of Work (Work Inclusions, Exclusions & Defined Deliverables)": {
                "Clause Language": "Contractor shall perform all work as shown on the Plans and as described in the Specifications.",
                "Clause Summary": "Standard scope of work clause requiring adherence to contract documents",
                "Risk Triggers Identified": [
                    "Undefined scope can lead to disputes"
                ],
                "Flow-Down Obligations": [],
                "Redline Recommendations": [
                    {
                        "action": "insert",
                        "text": "Add detailed list of deliverables and acceptance criteria"
                    }
                ],
                "Harmful Language / Policy Conflicts": []
            }
        },
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
                },
                {
                    "Risk Area": "Scope of Work",
                    "Risk Summary": "Generic scope language could lead to interpretation disputes",
                    "APS Redline Position": "Add detailed deliverables and acceptance criteria"
                }
            ]
        }
    }
    
    # Generate sample PDF
    render_pdf(sample_data, "test_contract_analysis.pdf")
    print("Test complete!")