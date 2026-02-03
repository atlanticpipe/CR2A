#!/usr/bin/env python3
# Contract Analysis CLI - Drag & Drop Interface, Accepts contract files via command line arguments for drag-and-drop functionality

import sys
import os
import json
from pathlib import Path
import traceback

# Try to import modules at module level
extract = None
openai_client = None
validator = None

try:
    import analyzer.extract
    import analyzer.openai_client
    import analyzer.validator
    MODULES_LOADED = True
except Exception as import_error:
    MODULES_LOADED = False
    IMPORT_ERROR = import_error


def pause_on_exit():
    """Always pause before exit so user can see output"""
    try:
        input("\nPress Enter to exit...")
    except:
        pass


def safe_import_modules():
    """Check if required modules were imported successfully"""
    global extract, openai_client, validator
    if not MODULES_LOADED:
        print(f"\n ERROR: Failed to import required modules")
        print(f"   {str(IMPORT_ERROR)}")
        print("\nThis may indicate a problem with the executable build.")
        print("Please ensure all dependencies are properly bundled.")
        traceback.print_exc()
        return False
    return True


def print_banner():
    """Print application banner"""
    print("\n" + "=" * 70)
    print("CONTRACT ANALYSIS TOOL - Drag & Drop CLI")
    print("=" * 70 + "\n")


def analyze_contract_file(file_path: str, output_dir: str = None):
    """Analyze a contract file and generate reports"""
    try:
        print(f"Input file: {file_path}")
        
        # Validate file exists
        if not os.path.exists(file_path):
            print(f"Error: File not found: {file_path}")
            return False
        
        # Determine output directory
        if output_dir is None:
            output_dir = os.path.dirname(file_path) or "."
        
        # Create output filename base
        input_filename = Path(file_path).stem
        output_base = os.path.join(output_dir, f"{input_filename}_analysis")
        
        # Step 1: Extract text
        print("\nStep 1/4: Extracting text from document...")
        contract_text = extract.extract_text(file_path)
        
        if not contract_text:
            print("Error: Failed to extract text from document")
            return False
        
        print(f"Extracted {len(contract_text)} characters")
        
        # Step 2: Load schema and rules
        print("\nStep 2/4: Loading schema and validation rules...")
        
        # Get the directory where the executable is located
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            base_dir = sys._MEIPASS
        else:
            # Running as script
            base_dir = os.path.dirname(__file__)
        
        schema_path = os.path.join(base_dir, 'output_schemas_v1.json')
        rules_path = os.path.join(base_dir, 'validation_rules_v1.json')
        
        if not os.path.exists(schema_path):
            print(f"Error: Schema file not found: {schema_path}")
            return False
        
        if not os.path.exists(rules_path):
            print(f"Error: Rules file not found: {rules_path}")
            return False
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_content = json.dumps(json.load(f), indent=2)
        
        with open(rules_path, 'r', encoding='utf-8') as f:
            rules_content = json.dumps(json.load(f), indent=2)
        
        print("Schema and rules loaded")
        
        # Step 3: Analyze with OpenAI
        print("\nStep 3/4: Analyzing contract with AI...")
        print("   (This may take 30-60 seconds...)")
        
        analysis_result = openai_client.analyze_contract(
            contract_text, 
            schema_content, 
            rules_content
        )
        
        print("AI analysis complete")
        
        # Step 4: Validate results
        print("\nStep 4/4: Validating results...")
        
        is_valid, validation_error = validator.validate_analysis_result(analysis_result)
        
        if not is_valid:
            print(f"Warning: Validation failed: {validation_error}")
            print("Continuing anyway, but results may not match expected format")
        else:
            print("Validation passed")
        
        # Save JSON results
        json_path = f"{output_base}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, indent=2, ensure_ascii=False)
        print(f"\nJSON saved: {json_path}")
        
        # Print summary
        print("\n" + "=" * 70)
        print("ANALYSIS COMPLETE!")
        print("=" * 70)
        
        if 'contract_overview' in analysis_result:
            overview = analysis_result['contract_overview']
            print("\nContract Overview:")
            print(f"Project: {overview.get('Project Title', 'N/A')}")
            print(f"Owner: {overview.get('Owner', 'N/A')}")
            print(f"Contractor: {overview.get('Contractor', 'N/A')}")
            print(f"Risk Level: {overview.get('General Risk Level', 'N/A')}")
        
        print(f"\nOutput file:")
        print(f"JSON: {json_path}")
        print()
        
        return True
        
    except Exception as e:
        print(f"\nError during analysis: {str(e)}")
        traceback.print_exc()
        return False


def main():
    """Main entry point for drag & drop CLI"""
    
    # Wrap everything in try-except to catch any errors
    try:
        print_banner()
        
        # Import modules first
        if not safe_import_modules():
            pause_on_exit()
            return 1
        
        # Check for file argument
        if len(sys.argv) < 2:
            print("DRAG & DROP USAGE:")
            print("Drag and drop a contract file (PDF or DOCX) onto this executable")
            print("to start the analysis.")
            print("\nCOMMAND LINE USAGE:")
            print("ContractAnalysisCLI.exe <contract_file.pdf>")
            print("\nEXAMPLES:")
            print("ContractAnalysisCLI.exe contract.pdf")
            print("ContractAnalysisCLI.exe \"C:\\Documents\\My Contract.docx\"")
            print("\nOUTPUT:")
            print("Analysis results will be saved in the same folder as the input file:")
            print("- <filename>_analysis.json (structured data)")
            print("\nREQUIREMENTS:")
            print("- OpenAI API key must be set as environment variable OPENAI_API_KEY")
            print("- For scanned PDFs: Tesseract OCR and Poppler must be installed")
            print()
            pause_on_exit()
            return 1
        
        file_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else None
        
        # Analyze the contract
        success = analyze_contract_file(file_path, output_dir)
        
        # Keep window open so user can see results
        print("\n" + "=" * 70)
        if success:
            print("SUCCESS! Check the output files above.")
        else:
            print("FAILED! Check the error messages above.")
        print("=" * 70)
        pause_on_exit()
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"\n\nCRITICAL ERROR: {str(e)}")
        traceback.print_exc()
        pause_on_exit()
        return 1


if __name__ == "__main__":
    exit_code = 1
    try:
        exit_code = main()
    except KeyboardInterrupt:
        print("\n\nAnalysis cancelled by user.")
        pause_on_exit()
        exit_code = 1
    except Exception as e:
        print(f"\n\nUNEXPECTED ERROR: {str(e)}")
        traceback.print_exc()
        pause_on_exit()
        exit_code = 1
    finally:
        sys.exit(exit_code)
