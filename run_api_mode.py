import sys
import os
import json
from pathlib import Path

# Import modules
import extract
import openai_client
import validator
import renderer

def print_banner():
    """Print application banner"""
    print("\n" + "=" * 70)
    print("CONTRACT ANALYSIS TOOL - API Mode")
    print("=" * 70 + "\n")

def analyze_contract_file(file_path: str, output_dir: str = None):
    print(f"📄 Input file: {file_path}")
    
    # Validate file exists
    if not os.path.exists(file_path):
        print(f" Error: File not found: {file_path}")
        return False
    
    # Determine output directory
    if output_dir is None:
        output_dir = os.path.dirname(file_path) or "."
    
    # Create output filename base
    input_filename = Path(file_path).stem
    output_base = os.path.join(output_dir, f"{input_filename}_analysis")
    
    try:
        # Step 1: Extract text
        print("\n Step 1/4: Extracting text from document...")
        contract_text = extract.extract_text(file_path)
        
        if not contract_text:
            print("Error: Failed to extract text from document")
            return False
        
        print(f"✓ Extracted {len(contract_text)} characters")
        
        # Step 2: Load schema and rules
        print("\n Step 2/4: Loading schema and validation rules...")
        
        schema_path = os.path.join(os.path.dirname(__file__), 'output_schemas_v1.json')
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_content = json.dumps(json.load(f), indent=2)
        
        rules_path = os.path.join(os.path.dirname(__file__), 'validation_rules_v1.json')
        with open(rules_path, 'r', encoding='utf-8') as f:
            rules_content = json.dumps(json.load(f), indent=2)
        
        print("✓ Schema and rules loaded")
        
        # Step 3: Analyze with OpenAI
        print("\n Step 3/4: Analyzing contract with AI...")
        print("   (This may take 30-60 seconds...)")
        
        analysis_result = openai_client.analyze_contract(
            contract_text, 
            schema_content, 
            rules_content
        )
        
        print("✓ AI analysis complete")
        
        # Step 4: Validate results
        print("\n Step 4/4: Validating results...")
        
        is_valid, validation_error = validator.validate_analysis_result(analysis_result)
        
        if not is_valid:
            print(f"Warning: Validation failed: {validation_error}")
            print("   Continuing anyway, but results may not match expected format")
        else:
            print("✓ Validation passed")
        
        # Save JSON results
        json_path = f"{output_base}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, indent=2, ensure_ascii=False)
        print(f"\n JSON saved: {json_path}")
        
        # Generate PDF report
        pdf_path = f"{output_base}.pdf"
        renderer.render_pdf(analysis_result, pdf_path)
        print(f" PDF saved: {pdf_path}")
        
        # Print summary
        print("\n" + "=" * 70)
        print(" ANALYSIS COMPLETE!")
        print("=" * 70)
        
        if 'contract_overview' in analysis_result:
            overview = analysis_result['contract_overview']
            print("\n Contract Overview:")
            print(f"   Project: {overview.get('Project Title', 'N/A')}")
            print(f"   Owner: {overview.get('Owner', 'N/A')}")
            print(f"   Contractor: {overview.get('Contractor', 'N/A')}")
            print(f"   Risk Level: {overview.get('General Risk Level', 'N/A')}")
        
        print(f"\n Output files:")
        print(f"   JSON: {json_path}")
        print(f"   PDF:  {pdf_path}")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n Error during analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point"""
    print_banner()
    
    # Check for file argument
    if len(sys.argv) < 2:
        print("Usage: python run_api_mode.py <contract_file.pdf>")
        print("\nExample:")
        print("  python run_api_mode.py contract.pdf")
        print("  python run_api_mode.py path/to/contract.docx")
        print("\nOutput files will be saved in the same directory as the input file.")
        print()
        input("\nPress Enter to exit...")
        return 1
    
    file_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Analyze the contract
    success = analyze_contract_file(file_path, output_dir)
    
    # Keep window open so user can see results
    print("\n" + "=" * 70)
    if success:
        print(" SUCCESS! Check the output files above.")
    else:
        print(" FAILED! Check the error messages above.")
    print("=" * 70)
    input("\nPress Enter to exit...")
    
    return 0 if success else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n  Analysis cancelled by user.")
        input("\nPress Enter to exit...")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)
