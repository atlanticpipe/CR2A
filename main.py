#!/usr/bin/env python3
"""
Main orchestrator for the complete contract analysis workflow.

This module coordinates all components of the contract analysis system:
- Text extraction from PDF/DOCX files
- ChatGPT API analysis with schema validation
- Response validation against company policies
- PDF report generation with exact template structure
- GUI integration for user interactions
- Error handling and logging

Workflow: extract → API → validate → render → save
"""

import os
import json
import logging
import traceback
from pathlib import Path
from typing import Dict, Tuple, Optional

# Import all workflow modules
import extract
import openai_client
import validator
import renderer
# GUI import with fallback
try:
    import gui
    GUI_AVAILABLE = True
except (ImportError, AttributeError) as e:
    GUI_AVAILABLE = False
    print(f"Warning: GUI not available ({e}). Using CLI mode.")


def validate_environment() -> Tuple[bool, str]:
    """
    Validate that all required files and environment variables are present.

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
        - is_valid: True if environment is properly configured
        - error_message: Empty string if valid, detailed error message if invalid
    """
    # Check required files
    required_files = {
        'output_schemas_v1.json': 'JSON schema file for contract analysis',
        'validation_rules_v1.json': 'Validation rules file for policy compliance'
    }
    
    missing_files = []
    for filename, description in required_files.items():
        file_path = os.path.join(os.path.dirname(__file__), filename)
        if not os.path.exists(file_path):
            missing_files.append(f"  • {filename} - {description}")
    
    if missing_files:
        error_msg = (
            "Missing required configuration files:\n\n"
            + "\n".join(missing_files) +
            "\n\nPlease ensure all configuration files are present in the application directory."
        )
        return False, error_msg
    
    # Check API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        error_msg = (
            "OpenAI API key not configured.\n\n"
            "The OPENAI_API_KEY environment variable must be set to use this application.\n\n"
            "To set it:\n"
            "  Windows: setx OPENAI_API_KEY \"sk-your-key-here\"\n"
            "  Linux/Mac: export OPENAI_API_KEY=\"sk-your-key-here\"\n\n"
            "After setting the key, restart your terminal or IDE.\n\n"
            "Get your API key from: https://platform.openai.com/api-keys"
        )
        return False, error_msg
    
    # Validate API key format (basic check)
    if not api_key.startswith('sk-'):
        error_msg = (
            "Invalid OpenAI API key format.\n\n"
            "API keys should start with 'sk-'\n\n"
            "Please check your OPENAI_API_KEY environment variable."
        )
        return False, error_msg
    
    return True, ""


def setup_logging() -> None:
    """
    Set up logging configuration to write errors to error.log file.

    This function configures logging to append errors to error.log in the
    project root directory with timestamp and detailed error information.
    """
    log_file = os.path.join(os.path.dirname(__file__), 'error.log')

    # Configure logging format
    logging.basicConfig(
        filename=log_file,
        level=logging.ERROR,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def log_error(error_message: str, exception: Optional[Exception] = None) -> None:
    """
    Log error messages to the error.log file.

    Args:
        error_message: The error message to log
        exception: Optional exception object for additional context
    """
    if exception:
        logging.error(f"{error_message}: {str(exception)}")
        logging.error(f"Traceback: {traceback.format_exc()}")
    else:
        logging.error(error_message)


def load_schema_content() -> str:
    """
    Load the JSON schema content for API calls.

    Returns:
        str: JSON schema as formatted string

    Raises:
        FileNotFoundError: If schema file doesn't exist
        json.JSONDecodeError: If schema file contains invalid JSON
    """
    schema_path = os.path.join(os.path.dirname(__file__), 'output_schemas_v1.json')

    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_data = json.load(f)
        return json.dumps(schema_data, indent=2)


def load_policy_content() -> str:
    """
    Load the policy rules content for API calls.

    Returns:
        str: Policy rules as formatted string

    Raises:
        FileNotFoundError: If policy file doesn't exist
        json.JSONDecodeError: If policy file contains invalid JSON
    """
    policy_path = os.path.join(os.path.dirname(__file__), 'validation_rules_v1.json')

    with open(policy_path, 'r', encoding='utf-8') as f:
        policy_data = json.load(f)
        return json.dumps(policy_data, indent=2)


def process_contract(file_path: str, window: gui.sg.Window) -> Tuple[bool, str]:
    """
    Orchestrate the complete contract analysis process.

    This function implements the main workflow:
    1. Extract text from uploaded file
    2. Call ChatGPT API with schema and rules
    3. Validate the response against schema and policy
    4. Return success status and analysis data

    Args:
        file_path: Path to the contract file (PDF or DOCX)
        window: GUI window for status updates

    Returns:
        Tuple[bool, str]: (success, analysis_data_json)
        - success: True if workflow completed successfully
        - analysis_data_json: JSON string of analysis results, empty if failed
    """
    try:
        # Step 1: Extract text from uploaded file
        gui.update_status(window, "extracting text")
        contract_text = extract.extract_text(file_path)

        if not contract_text:
            error_msg = f"Failed to extract text from {file_path}"
            log_error(error_msg)
            gui.show_error_dialog(error_msg)
            return False, ""

        print(f"Successfully extracted {len(contract_text)} characters from contract")

        # Step 2: Call ChatGPT API with schema and rules
        gui.update_status(window, "analyzing with AI")

        try:
            schema_content = load_schema_content()
            rules_content = load_policy_content()
            analysis_result = openai_client.analyze_contract(contract_text, schema_content, rules_content)
        except Exception as e:
            error_msg = f"API call failed: {str(e)}"
            log_error(error_msg, e)
            gui.show_error_dialog(f"API Error: {str(e)}")
            return False, ""

        print("Successfully received analysis from API")

        # Step 3: Validate the response against schema and policy
        gui.update_status(window, "validating results")

        try:
            is_valid, validation_error = validator.validate_analysis_result(analysis_result)

            if not is_valid:
                error_msg = f"Validation failed: {validation_error}"
                log_error(error_msg)
                gui.show_error_dialog(f"Validation Error: {validation_error}")
                return False, ""

        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            log_error(error_msg, e)
            gui.show_error_dialog(f"Validation Error: {str(e)}")
            return False, ""

        print("Successfully validated analysis results")

        # Convert analysis result to JSON string
        analysis_json = json.dumps(analysis_result, indent=2)
        return True, analysis_json

    except Exception as e:
        error_msg = f"Unexpected error in process_contract: {str(e)}"
        log_error(error_msg, e)
        gui.show_error_dialog(f"Unexpected Error: {str(e)}")
        return False, ""


def save_results(data: dict, base_path: str) -> None:
    """
    Save both PDF and JSON files to the specified location.

    Args:
        data: Dictionary containing the analysis results
        base_path: Base path for output files (without extension)

    Raises:
        Exception: If file saving fails
    """
    try:
        # Save JSON file
        json_path = f"{base_path}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"JSON results saved to: {json_path}")

        # Save PDF file
        pdf_path = f"{base_path}.pdf"
        renderer.render_pdf(data, pdf_path)
        print(f"PDF report saved to: {pdf_path}")

    except Exception as e:
        error_msg = f"Failed to save results to {base_path}: {str(e)}"
        log_error(error_msg, e)
        raise Exception(error_msg)


def main() -> None:
    """
    Main entry point that launches the GUI and handles the complete workflow.

    This function:
    1. Validates environment and configuration
    2. Sets up logging configuration
    3. Launches the GUI to get user file selection
    4. Processes the selected contract through the complete workflow
    5. Enables save functionality and handles user save actions
    6. Manages the application lifecycle and error handling
    """
    # Set up logging first
    setup_logging()

    print("Launching Contract Analysis Tool...")
    
    # Validate environment before proceeding
    is_valid, error_message = validate_environment()
    if not is_valid:
        print(f"Environment validation failed:\n{error_message}")
        # Show error dialog before exiting
        try:
            import PySimpleGUI as sg
            sg.popup_error(
                "Configuration Error",
                error_message,
                title="Contract Analysis Tool - Configuration Error",
                button_color=('white', '#d32f2f')
            )
        except:
            # If GUI not available, just print error
            print("\nERROR: Cannot start application due to configuration issues.")
        return

    print("Environment validation passed ✓")

    # Check if GUI is available
    if not GUI_AVAILABLE:
        print("\n" + "="*70)
        print("GUI NOT AVAILABLE - Using CLI Mode")
        print("="*70)
        print("\nUsage: python main.py <contract_file.pdf>")
        print("   or: python run_api_mode.py <contract_file.pdf>")
        print("\nFor GUI support, install PySimpleGUI from:")
        print("  pip install --extra-index-url https://PySimpleGUI.net/install PySimpleGUI")
        print("\nAlternatively, use the CLI version:")
        print("  python run_api_mode.py \"Contract #1.pdf\"")
        print("="*70)
        
        # Check if file was provided as command line argument
        import sys
        if len(sys.argv) > 1:
            contract_file = sys.argv[1]
            if os.path.exists(contract_file):
                print(f"\nProcessing: {contract_file}")
                success, analysis_json = process_contract(contract_file, None)
                if success:
                    analysis_data = json.loads(analysis_json)
                    base_path = os.path.splitext(contract_file)[0]
                    save_results(analysis_data, base_path)
                    print(f"\n✓ Analysis complete! Files saved to:")
                    print(f"  - {base_path}_analysis.json")
                    print(f"  - {base_path}_analysis.pdf")
                else:
                    print("\n✗ Analysis failed. Check error.log for details.")
            else:
                print(f"\nError: File not found: {contract_file}")
        return

    # Create main window for file selection and analysis
    window = gui.create_window()

    try:
        selected_file = None
        analysis_data = None

        while True:
            event, values = window.read()

            if event == gui.sg.WINDOW_CLOSED:
                break

            elif event == '-DROP_ZONE-':
                # Handle file drop event
                dropped_files = values['-DROP_ZONE-'].split('\n') if values['-DROP_ZONE-'] else []
                if dropped_files and dropped_files[0].strip():
                    file_path = dropped_files[0].strip()
                    gui.handle_file_drop(window, file_path)
                    if hasattr(window, 'metadata') and window.metadata.get('file_path'):
                        selected_file = window.metadata['file_path']

            elif event == '-START-':
                # Start analysis button clicked
                if selected_file:
                    print(f"Starting analysis of: {selected_file}")
                    success, analysis_json = process_contract(selected_file, window)

                    if success:
                        gui.update_status(window, "analysis complete")
                        gui.enable_save_button(window)
                        analysis_data = json.loads(analysis_json)
                        print("Analysis completed successfully")
                    else:
                        gui.update_status(window, "analysis failed")
                        print("Analysis failed")

            elif event == '-SAVE-':
                # Save PDF button clicked
                if analysis_data:
                    pdf_filename = gui.sg.popup_get_file(
                        "Save PDF Report",
                        save_as=True,
                        default_extension=".pdf",
                        file_types=(("PDF Files", "*.pdf"), ("All Files", "*.*")),
                        title="Save Contract Analysis Report"
                    )

                    if pdf_filename:
                        try:
                            # Remove .pdf extension if present for base path
                            base_path = pdf_filename[:-4] if pdf_filename.endswith('.pdf') else pdf_filename
                            save_results(analysis_data, base_path)
                            gui.update_status(window, "files saved successfully")
                            gui.sg.popup("Success!", "Both PDF and JSON files saved successfully!")
                            print(f"Files saved successfully to {base_path}")
                        except Exception as e:
                            gui.show_error_dialog(f"Save failed: {str(e)}")
                            print(f"Save failed: {str(e)}")
                    else:
                        gui.update_status(window, "save cancelled")

    except Exception as e:
        error_msg = f"Critical error in main workflow: {str(e)}"
        log_error(error_msg, e)
        gui.show_error_dialog(f"Critical Error: {str(e)}")
        print(f"Critical error: {error_msg}")

    finally:
        window.close()


if __name__ == "__main__":
    main()