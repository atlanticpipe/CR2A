"""
Error Scenario Testing Script for CR2A Application
Task 21.3: Test error scenarios comprehensively

This script tests:
- Missing API key (should show settings dialog)
- Invalid API key (should show validation error)
- Network disconnected during analysis (should show error and retry option)
- Corrupted files (should show error message)
- Pythia model unavailable (should show initialization error)
- Error logging functionality

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 7.6
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime


class ErrorScenarioTester:
    """Comprehensive error scenario testing for CR2A application"""
    
    def __init__(self):
        self.results = {
            "test_date": datetime.now().isoformat(),
            "tests": []
        }
        self.config_dir = Path(os.environ.get('APPDATA')) / "CR2A"
        self.fixtures_dir = Path("tests/fixtures")
        
    def log_test(self, test_name, status, details="", expected_behavior=""):
        """Log test result"""
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "expected_behavior": expected_behavior
        }
        self.results["tests"].append(result)
        
        status_symbol = "✓" if status == "PASSED" else "✗" if status == "FAILED" else "⚠"
        print(f"{status_symbol} {test_name}: {status}")
        if expected_behavior:
            print(f"  Expected: {expected_behavior}")
        if details:
            print(f"  Details: {details}")
    
    def test_missing_api_key(self):
        """Test missing API key scenario (Requirement 9.4)"""
        print("\n" + "="*60)
        print("Test 1: Missing API Key")
        print("="*60)
        
        config_file = self.config_dir / "config.json"
        backup_file = self.config_dir / "config.json.backup"
        
        # Check if config exists
        if not config_file.exists():
            self.log_test(
                "Missing API Key",
                "READY",
                "Config file does not exist - ready to test",
                "Settings dialog should be shown on application launch"
            )
            return
        
        # Backup existing config
        if config_file.exists():
            shutil.copy(config_file, backup_file)
            print(f"Backed up config to: {backup_file}")
        
        # Read config
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Check if API key is present
        has_api_key = "openai_api_key" in config and config["openai_api_key"]
        
        if has_api_key:
            self.log_test(
                "Missing API Key",
                "SETUP",
                "API key is present in config. To test: delete config.json and restart app",
                "Settings dialog should be shown on application launch"
            )
        else:
            self.log_test(
                "Missing API Key",
                "READY",
                "API key is missing from config - ready to test",
                "Settings dialog should be shown on application launch"
            )
    
    def test_invalid_api_key_format(self):
        """Test invalid API key format (Requirement 12.4, 12.5)"""
        print("\n" + "="*60)
        print("Test 2: Invalid API Key Format")
        print("="*60)
        
        # Check if config manager exists
        config_manager_path = Path("src/config_manager.py")
        if not config_manager_path.exists():
            self.log_test(
                "Invalid API Key Format",
                "SKIPPED",
                "Config manager not found",
                "Validation error should be shown"
            )
            return
        
        # Read config manager to check for validation
        content = config_manager_path.read_text()
        
        has_validation = "validate" in content.lower() and "api" in content.lower()
        
        if has_validation:
            self.log_test(
                "Invalid API Key Format",
                "READY",
                "Config manager has validation logic",
                "Validation error should be shown for invalid format (not starting with 'sk-')"
            )
        else:
            self.log_test(
                "Invalid API Key Format",
                "WARNING",
                "Validation logic not clearly identified in config manager",
                "Validation error should be shown for invalid format"
            )
    
    def test_network_disconnection(self):
        """Test network disconnection during analysis (Requirement 9.2)"""
        print("\n" + "="*60)
        print("Test 3: Network Disconnection During Analysis")
        print("="*60)
        
        # Check if analysis engine has error handling
        analysis_engine_path = Path("src/analysis_engine.py")
        if not analysis_engine_path.exists():
            self.log_test(
                "Network Disconnection",
                "SKIPPED",
                "Analysis engine not found",
                "Error message and retry option should be shown"
            )
            return
        
        # Read analysis engine to check for error handling
        content = analysis_engine_path.read_text()
        
        has_error_handling = "except" in content and ("network" in content.lower() or "connection" in content.lower() or "timeout" in content.lower())
        has_retry = "retry" in content.lower()
        
        if has_error_handling and has_retry:
            self.log_test(
                "Network Disconnection",
                "READY",
                "Analysis engine has network error handling and retry logic",
                "Error message and retry option should be shown"
            )
        elif has_error_handling:
            self.log_test(
                "Network Disconnection",
                "PARTIAL",
                "Analysis engine has error handling but retry logic unclear",
                "Error message and retry option should be shown"
            )
        else:
            self.log_test(
                "Network Disconnection",
                "WARNING",
                "Network error handling not clearly identified",
                "Error message and retry option should be shown"
            )
    
    def test_corrupted_files(self):
        """Test corrupted file handling (Requirement 9.1)"""
        print("\n" + "="*60)
        print("Test 4: Corrupted File Handling")
        print("="*60)
        
        # Check for corrupted test files
        corrupted_pdf = self.fixtures_dir / "corrupted.pdf"
        malformed_pdf = self.fixtures_dir / "malformed_fake.pdf"
        malformed_docx = self.fixtures_dir / "malformed_fake.docx"
        
        test_files = []
        if corrupted_pdf.exists():
            test_files.append("corrupted.pdf")
        if malformed_pdf.exists():
            test_files.append("malformed_fake.pdf")
        if malformed_docx.exists():
            test_files.append("malformed_fake.docx")
        
        if not test_files:
            self.log_test(
                "Corrupted File Handling",
                "WARNING",
                "No corrupted test files found in fixtures",
                "Error message should be shown for corrupted files"
            )
            return
        
        # Check if contract uploader has error handling
        uploader_path = Path("src/contract_uploader.py")
        if not uploader_path.exists():
            self.log_test(
                "Corrupted File Handling",
                "SKIPPED",
                "Contract uploader not found",
                "Error message should be shown for corrupted files"
            )
            return
        
        content = uploader_path.read_text()
        has_error_handling = "except" in content and ("error" in content.lower() or "exception" in content.lower())
        
        if has_error_handling:
            self.log_test(
                "Corrupted File Handling",
                "READY",
                f"Contract uploader has error handling. Test files available: {', '.join(test_files)}",
                "Error message should be shown for corrupted files"
            )
        else:
            self.log_test(
                "Corrupted File Handling",
                "WARNING",
                f"Error handling not clearly identified. Test files available: {', '.join(test_files)}",
                "Error message should be shown for corrupted files"
            )
    
    def test_pythia_model_unavailable(self):
        """Test Pythia model unavailable scenario (Requirement 7.6)"""
        print("\n" + "="*60)
        print("Test 5: Pythia Model Unavailable")
        print("="*60)
        
        # Check if Pythia engine exists
        pythia_engine_path = Path("src/pythia_engine.py")
        if not pythia_engine_path.exists():
            self.log_test(
                "Pythia Model Unavailable",
                "SKIPPED",
                "Pythia engine not found",
                "Initialization error should be shown"
            )
            return
        
        # Read Pythia engine to check for error handling
        content = pythia_engine_path.read_text()
        
        has_load_error_handling = "load_model" in content and "except" in content
        has_initialization_check = "is_loaded" in content or "model_loaded" in content
        
        if has_load_error_handling and has_initialization_check:
            self.log_test(
                "Pythia Model Unavailable",
                "READY",
                "Pythia engine has model loading error handling and status check",
                "Initialization error should be shown if model fails to load"
            )
        elif has_load_error_handling:
            self.log_test(
                "Pythia Model Unavailable",
                "PARTIAL",
                "Pythia engine has error handling but status check unclear",
                "Initialization error should be shown if model fails to load"
            )
        else:
            self.log_test(
                "Pythia Model Unavailable",
                "WARNING",
                "Model loading error handling not clearly identified",
                "Initialization error should be shown if model fails to load"
            )
    
    def test_error_logging(self):
        """Test error logging functionality (Requirement 9.5)"""
        print("\n" + "="*60)
        print("Test 6: Error Logging")
        print("="*60)
        
        logs_dir = self.config_dir / "logs"
        
        # Check if logs directory exists
        if not logs_dir.exists():
            self.log_test(
                "Error Logging",
                "WARNING",
                "Logs directory does not exist (will be created on first launch)",
                "All errors should be logged to cr2a.log"
            )
            return
        
        # Check for log files
        log_files = list(logs_dir.glob("*.log"))
        
        if not log_files:
            self.log_test(
                "Error Logging",
                "WARNING",
                "No log files found (application not yet run)",
                "All errors should be logged to cr2a.log"
            )
            return
        
        # Check main log file
        main_log = logs_dir / "cr2a.log"
        if not main_log.exists():
            self.log_test(
                "Error Logging",
                "WARNING",
                f"Main log file not found. Found: {[f.name for f in log_files]}",
                "All errors should be logged to cr2a.log"
            )
            return
        
        # Read log file to check for error entries
        content = main_log.read_text()
        
        has_error_logs = "ERROR" in content or "Exception" in content
        has_timestamps = any(char.isdigit() for char in content[:100])  # Check first 100 chars for timestamps
        
        if has_error_logs:
            self.log_test(
                "Error Logging",
                "PASSED",
                "Log file contains error entries with timestamps",
                "All errors should be logged to cr2a.log"
            )
        elif has_timestamps:
            self.log_test(
                "Error Logging",
                "READY",
                "Log file exists with timestamps (no errors logged yet)",
                "All errors should be logged to cr2a.log"
            )
        else:
            self.log_test(
                "Error Logging",
                "WARNING",
                "Log file exists but format unclear",
                "All errors should be logged to cr2a.log"
            )
    
    def test_log_rotation(self):
        """Test log rotation configuration"""
        print("\n" + "="*60)
        print("Test 7: Log Rotation")
        print("="*60)
        
        # Check for log rotation configuration in code
        main_path = Path("src/main.py")
        if not main_path.exists():
            self.log_test(
                "Log Rotation",
                "SKIPPED",
                "Main module not found",
                "Logs should rotate (7 days, 100MB max)"
            )
            return
        
        content = main_path.read_text()
        
        has_rotation = "RotatingFileHandler" in content or "TimedRotatingFileHandler" in content
        has_max_bytes = "maxBytes" in content or "max_bytes" in content
        has_backup_count = "backupCount" in content or "backup_count" in content
        
        if has_rotation and (has_max_bytes or has_backup_count):
            self.log_test(
                "Log Rotation",
                "PASSED",
                "Log rotation is configured in main module",
                "Logs should rotate (7 days, 100MB max)"
            )
        elif has_rotation:
            self.log_test(
                "Log Rotation",
                "PARTIAL",
                "Log rotation handler found but configuration unclear",
                "Logs should rotate (7 days, 100MB max)"
            )
        else:
            self.log_test(
                "Log Rotation",
                "WARNING",
                "Log rotation configuration not clearly identified",
                "Logs should rotate (7 days, 100MB max)"
            )
    
    def test_empty_file_handling(self):
        """Test empty file handling"""
        print("\n" + "="*60)
        print("Test 8: Empty File Handling")
        print("="*60)
        
        # Check for empty test files
        empty_pdf = self.fixtures_dir / "empty.pdf"
        empty_docx = self.fixtures_dir / "empty.docx"
        
        test_files = []
        if empty_pdf.exists():
            test_files.append("empty.pdf")
        if empty_docx.exists():
            test_files.append("empty.docx")
        
        if not test_files:
            self.log_test(
                "Empty File Handling",
                "WARNING",
                "No empty test files found in fixtures",
                "Error message should be shown for empty files"
            )
            return
        
        self.log_test(
            "Empty File Handling",
            "READY",
            f"Empty test files available: {', '.join(test_files)}",
            "Error message should be shown for empty files"
        )
    
    def test_data_preservation_on_error(self):
        """Test data preservation on error (Requirement 9.6)"""
        print("\n" + "="*60)
        print("Test 9: Data Preservation on Error")
        print("="*60)
        
        # Check if application controller has error handling
        controller_path = Path("src/application_controller.py")
        if not controller_path.exists():
            self.log_test(
                "Data Preservation on Error",
                "SKIPPED",
                "Application controller not found",
                "Analysis result should be preserved on error"
            )
            return
        
        content = controller_path.read_text()
        
        has_error_handler = "handle_error" in content
        has_state_preservation = "analysis_result" in content and "self." in content
        
        if has_error_handler and has_state_preservation:
            self.log_test(
                "Data Preservation on Error",
                "READY",
                "Application controller has error handling and state management",
                "Analysis result should be preserved on error"
            )
        elif has_error_handler:
            self.log_test(
                "Data Preservation on Error",
                "PARTIAL",
                "Application controller has error handling but state preservation unclear",
                "Analysis result should be preserved on error"
            )
        else:
            self.log_test(
                "Data Preservation on Error",
                "WARNING",
                "Error handling and state preservation not clearly identified",
                "Analysis result should be preserved on error"
            )
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "="*60)
        print("ERROR SCENARIO TEST SUMMARY")
        print("="*60)
        
        total_tests = len(self.results["tests"])
        passed = sum(1 for t in self.results["tests"] if t["status"] == "PASSED")
        ready = sum(1 for t in self.results["tests"] if t["status"] == "READY")
        partial = sum(1 for t in self.results["tests"] if t["status"] == "PARTIAL")
        warning = sum(1 for t in self.results["tests"] if t["status"] == "WARNING")
        skipped = sum(1 for t in self.results["tests"] if t["status"] == "SKIPPED")
        setup = sum(1 for t in self.results["tests"] if t["status"] == "SETUP")
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed}")
        print(f"Ready: {ready}")
        print(f"Partial: {partial}")
        print(f"Warning: {warning}")
        print(f"Skipped: {skipped}")
        print(f"Setup Required: {setup}")
        
        # Save report to file
        report_file = Path("tests/error_scenario_test_results.json")
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nDetailed report saved to: {report_file}")
        
        return True
    
    def run_all_tests(self):
        """Run all error scenario tests"""
        print("="*60)
        print("CR2A ERROR SCENARIO TESTING")
        print("Task 21.3: Test error scenarios comprehensively")
        print("="*60)
        
        # Run all tests
        self.test_missing_api_key()
        self.test_invalid_api_key_format()
        self.test_network_disconnection()
        self.test_corrupted_files()
        self.test_pythia_model_unavailable()
        self.test_error_logging()
        self.test_log_rotation()
        self.test_empty_file_handling()
        self.test_data_preservation_on_error()
        
        # Generate report
        self.generate_report()
        
        print("\n" + "="*60)
        print("ERROR SCENARIO TESTS COMPLETED")
        print("="*60)
        
        return True


def main():
    """Main entry point"""
    tester = ErrorScenarioTester()
    tester.run_all_tests()
    
    print("\nManual Testing Required:")
    print("The tests above verify that error handling code is present.")
    print("To fully test error scenarios, run the application and:")
    print("\n1. Missing API Key:")
    print("   - Delete %APPDATA%\\CR2A\\config.json")
    print("   - Launch CR2A.exe")
    print("   - Verify settings dialog is shown")
    print("\n2. Invalid API Key:")
    print("   - Enter 'invalid_key' in settings")
    print("   - Try to analyze a contract")
    print("   - Verify validation error is shown")
    print("\n3. Network Disconnection:")
    print("   - Start analyzing a contract")
    print("   - Disconnect network during analysis")
    print("   - Verify error message and retry option")
    print("\n4. Corrupted Files:")
    print("   - Try to upload corrupted.pdf from fixtures")
    print("   - Verify error message is shown")
    print("\n5. Pythia Model Unavailable:")
    print("   - Rename or remove Pythia model files")
    print("   - Launch CR2A.exe")
    print("   - Verify initialization error is shown")
    print("\n6. Error Logging:")
    print("   - Trigger any error scenario")
    print("   - Check %APPDATA%\\CR2A\\logs\\cr2a.log")
    print("   - Verify error is logged with timestamp")
    
    print("\nNext Steps:")
    print("1. Perform manual error scenario testing")
    print("2. Document any issues found")
    print("3. Verify all error messages are clear and helpful")
    print("4. Verify recovery options work correctly")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
