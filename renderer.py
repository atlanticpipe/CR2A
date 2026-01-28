import json
import sys
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML, CSS


def load_json(json_file: str) -> dict:
    """Load JSON data from file."""
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def render_template(template_file: str, data: dict) -> str:
    """Render Jinja2 template with JSON data."""
    template_path = Path(template_file).parent
    template_name = Path(template_file).name
    
    env = Environment(
        loader=FileSystemLoader(template_path),
        autoescape=select_autoescape(['html', 'xml'])
    )
    
    template = env.get_template(template_name)
    return template.render(data=data)


def html_to_pdf(html_content: str, output_file: str) -> None:
    """Convert HTML string to PDF."""
    HTML(string=html_content).write_pdf(output_file)


def main():
    """Main entry point."""
    if len(sys.argv) < 4:
        print("Usage: python json_to_pdf.py <json_file> <template_file> <output_pdf>")
        print("\nArguments:")
        print("  json_file      Path to JSON file containing data")
        print("  template_file  Path to Jinja2 HTML template")
        print("  output_pdf     Path where PDF will be saved")
        sys.exit(1)
    
    json_file = sys.argv[1]
    template_file = sys.argv[2]
    output_pdf = sys.argv[3]
    
    try:
        # Load JSON data
        data = load_json(json_file)
        print(f"✓ Loaded JSON from {json_file}")
        
        # Render template
        html_content = render_template(template_file, data)
        print(f"✓ Rendered template from {template_file}")
        
        # Generate PDF
        html_to_pdf(html_content, output_pdf)
        print(f"✓ PDF generated successfully: {output_pdf}")
        
    except FileNotFoundError as e:
        print(f"✗ Error: File not found - {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"✗ Error: Invalid JSON - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()