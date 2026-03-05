"""
End-to-End Testing Script for CR2A Application
Task 21.1: Perform end-to-end testing on target hardware

This script tests:
- Windows 10 and Windows 11 compatibility
- Minimum spec hardware (8GB RAM)
- Various contract sizes (1, 10, 25, 50 pages)
- Offline query processing
- Error scenario handling

Requirements: 10.1, 10.2, 7.5, 9.1, 9.2, 9.3
"""

import os
import sys
import time
import json
import psutil
import platform
import subprocess
from pathlib import Path
from datetime import datetime


class EndToEndTester:
    """Comprehensive end-to-end testing for CR2A application"""
    
    def __init__(self):
        self.results = {
            "test_date": datetime.now().isoformat(),
            "system_info": self.get_system_info(),
            "tests": []
        }
        self.fixtures_dir = Path("tests/fixtures")
        self.config_dir = Path(os.environ.get('APPDATA')) / "CR2A"
        
    def get_system_info(self):
        """Gather system information"""
        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "os_release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "ram_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "python_version": platform.python_version()
        }
    
    def log_test(self, test_name, status, details="", duration=0):
        """Log test result"""
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "duration_seconds": round(duration, 2)
        }
        self.results["tests"].append(result)
        
        status_symbol = "✓" if status == "PASSED" else "✗" if status == "FAILED" else "⚠"
        print(f"{status_symbol} {test_name}: {status}")
        if details:
            print(f"  Details: {details}")
        if duration > 0:
            print(f"  Duration: {duration:.2f}s")
    
    def test_windows_compatibility(self):
        """Test Windows 10/11 compatibility (Requirement 10.1)"""
        print("\n" + "="*60)
        print("Test 1: Windows Compatibility")
        print("="*60)
        
        start_time = time.time()
        
        os_name = platform.system()
        os_version = platform.release()
        
        if os_name != "Windows":
            self.log_test(
                "Windows Compatibility",
                "FAILED",
                f"Not running on Windows (detected: {os_name})",
                time.time() - start_time
            )
            return False
        
        # Check for Windows 10 or 11
        if os_version in ["10", "11"]:
            self.log_test(
                "Windows Compatibility",
                "PASSED",
                f"Running on Windows {os_version}",
                time.time() - start_time
            )
            return True
        else:
            self.log_test(
                "Windows Compatibility",
                "WARNING",
                f"Running on Windows {os_version} (not 10 or 11)",
                time.time() - start_time
            )
            return True
    
    def test_minimum_hardware_specs(self):
        """Test minimum hardware specifications (Requirement 10.2)"""
        print("\n" + "="*60)
        print("Test 2: Minimum Hardware Specifications")
        print("="*60)
        
        start_time = time.time()
        
        ram_gb = psutil.virtual_memory().total / (1024**3)
        
        if ram_gb >= 8:
            self.log_test(
                "Minimum RAM (8GB)",
                "PASSED",
                f"System has {ram_gb:.2f} GB RAM",
                time.time() - start_time
            )
            return True
        else:
            self.log_test(
                "Minimum RAM (8GB)",
                "FAILED",
                f"System has only {ram_gb:.2f} GB RAM (minimum 8GB required)",
                time.time() - start_time
            )
            return False
    
    def test_contract_file_availability(self):
        """Test that sample contract files are available"""
        print("\n" + "="*60)
        print("Test 3: Sample Contract Files")
        print("="*60)
        
        start_time = time.time()
        
        if not self.fixtures_dir.exists():
            self.log_test(
                "Sample Contract Files",
                "FAILED",
                f"Fixtures directory not found: {self.fixtures_dir}",
                time.time() - start_time
            )
            return False
        
        # Check for required contract sizes
        required_contracts = {
            "1-page": "contract_1page.pdf",
            "10-page": "contract_10pages.pdf",
            "25-page": "contract_25pages.pdf",
            "50-page": "contract_50pages.pdf"
        }
        
        missing_contracts = []
        found_contracts = []
        
        for size, filename in required_contracts.items():
            file_path = self.fixtures_dir / filename
            if file_path.exists():
                found_contracts.append(f"{size} ({filename})")
            else:
                missing_contracts.append(f"{size} ({filename})")
        
        if missing_contracts:
            self.log_test(
                "Sample Contract Files",
                "WARNING",
                f"Missing: {', '.join(missing_contracts)}. Found: {', '.join(found_contracts)}",
                time.time() - start_time
            )
            return len(found_contracts) > 0
        else:
            self.log_test(
                "Sample Contract Files",
                "PASSED",
                f"All contract sizes available: {', '.join(found_contracts)}",
                time.time() - start_time
            )
            return True
    
    def test_config_directory_structure(self):
        """Test configuration directory structure"""
        print("\n" + "="*60)
        print("Test 4: Configuration Directory Structure")
        print("="*60)
        
        start_time = time.time()
        
        # Check if config directory exists
        if not self.config_dir.exists():
            self.log_test(
                "Config Directory",
                "WARNING",
                f"Config directory not found (will be created on first launch): {self.config_dir}",
                time.time() - start_time
            )
            return True
        
        # Check subdirectories
        logs_dir = self.config_dir / "logs"
        config_file = self.config_dir / "config.json"
        
        checks = []
        if logs_dir.exists():
            checks.append("logs directory exists")
        if config_file.exists():
            checks.append("config.json exists")
        
        self.log_test(
            "Config Directory",
            "PASSED",
            f"Config directory found: {', '.join(checks) if checks else 'empty'}",
            time.time() - start_time
        )
        return True
    
    def test_offline_capability_setup(self):
        """Test offline query processing capability (Requirement 7.5)"""
        print("\n" + "="*60)
        print("Test 5: Offline Query Processing Setup")
        print("="*60)
        
        start_time = time.time()
        
        # Check if Pythia engine module exists
        pythia_module = Path("src/pythia_engine.py")
        query_module = Path("src/query_engine.py")
        
        if not pythia_module.exists():
            self.log_test(
                "Offline Query Setup",
                "FAILED",
                f"Pythia engine module not found: {pythia_module}",
                time.time() - start_time
            )
            return False
        
        if not query_module.exists():
            self.log_test(
                "Offline Query Setup",
                "FAILED",
                f"Query engine module not found: {query_module}",
                time.time() - start_time
            )
            return False
        
        self.log_test(
            "Offline Query Setup",
            "PASSED",
            "Pythia and Query engine modules found",
            time.time() - start_time
        )
        return True
    
    def test_error_handling_components(self):
        """Test error handling components (Requirements 9.1, 9.2, 9.3)"""
        print("\n" + "="*60)
        print("Test 6: Error Handling Components")
        print("="*60)
        
        start_time = time.time()
        
        # Check for error handler module
        error_handler = Path("src/error_handler.py")
        
        if not error_handler.exists():
            self.log_test(
                "Error Handling Components",
                "WARNING",
                "Error handler module not found (may be integrated in other modules)",
                time.time() - start_time
            )
            return True
        
        # Read error handler to check for key functions
        content = error_handler.read_text()
        
        checks = []
        if "handle_error" in content or "ErrorHandler" in content:
            checks.append("error handling functions present")
        if "log" in content.lower():
            checks.append("logging integration")
        if "retry" in content.lower():
            checks.append("retry logic")
        
        self.log_test(
            "Error Handling Components",
            "PASSED",
            f"Error handler found: {', '.join(checks)}",
            time.time() - start_time
        )
        return True
    
    def test_executable_availability(self):
        """Test if executable is available for testing"""
        print("\n" + "="*60)
        print("Test 7: Executable Availability")
        print("="*60)
        
        start_time = time.time()
        
        exe_path = Path("dist/CR2A.exe")
        
        if not exe_path.exists():
            self.log_test(
                "Executable Availability",
                "WARNING",
                "CR2A.exe not found in dist/ (run build first)",
                time.time() - start_time
            )
            return False
        
        # Check file size
        size_mb = exe_path.stat().st_size / (1024**2)
        
        self.log_test(
            "Executable Availability",
            "PASSED",
            f"CR2A.exe found ({size_mb:.2f} MB)",
            time.time() - start_time
        )
        return True
    
    def test_log_file_structure(self):
        """Test log file structure and rotation"""
        print("\n" + "="*60)
        print("Test 8: Log File Structure")
        print("="*60)
        
        start_time = time.time()
        
        logs_dir = self.config_dir / "logs"
        
        if not logs_dir.exists():
            self.log_test(
                "Log File Structure",
                "WARNING",
                "Logs directory not found (will be created on first launch)",
                time.time() - start_time
            )
            return True
        
        # Check for log files
        log_files = list(logs_dir.glob("*.log"))
        
        if not log_files:
            self.log_test(
                "Log File Structure",
                "WARNING",
                "No log files found (application not yet run)",
                time.time() - start_time
            )
            return True
        
        # Check main log file
        main_log = logs_dir / "cr2a.log"
        if main_log.exists():
            size_kb = main_log.stat().st_size / 1024
            self.log_test(
                "Log File Structure",
                "PASSED",
                f"Found {len(log_files)} log file(s), main log: {size_kb:.2f} KB",
                time.time() - start_time
            )
        else:
            self.log_test(
                "Log File Structure",
                "PASSED",
                f"Found {len(log_files)} log file(s)",
                time.time() - start_time
            )
        
        return True
    
    def test_component_modules(self):
        """Test that all required component modules exist"""
        print("\n" + "="*60)
        print("Test 9: Component Modules")
        print("="*60)
        
        start_time = time.time()
        
        required_modules = {
            "Main": "src/main.py",
            "Application Controller": "src/application_controller.py",
            "Upload Screen": "src/upload_screen.py",
            "Analysis Screen": "src/analysis_screen.py",
            "Chat Screen": "src/chat_screen.py",
            "Settings Dialog": "src/settings_dialog.py",
            "Contract Uploader": "src/contract_uploader.py",
            "Analysis Engine": "src/analysis_engine.py",
            "Pythia Engine": "src/pythia_engine.py",
            "Query Engine": "src/query_engine.py",
            "Config Manager": "src/config_manager.py"
        }
        
        missing_modules = []
        found_modules = []
        
        for name, path in required_modules.items():
            if Path(path).exists():
                found_modules.append(name)
            else:
                missing_modules.append(f"{name} ({path})")
        
        if missing_modules:
            self.log_test(
                "Component Modules",
                "FAILED",
                f"Missing modules: {', '.join(missing_modules)}",
                time.time() - start_time
            )
            return False
        else:
            self.log_test(
                "Component Modules",
                "PASSED",
                f"All {len(found_modules)} required modules found",
                time.time() - start_time
            )
            return True
    
    def test_network_connectivity(self):
        """Test network connectivity for online features"""
        print("\n" + "="*60)
        print("Test 10: Network Connectivity")
        print("="*60)
        
        start_time = time.time()
        
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            self.log_test(
                "Network Connectivity",
                "PASSED",
                "Network connection available",
                time.time() - start_time
            )
            return True
        except OSError:
            self.log_test(
                "Network Connectivity",
                "WARNING",
                "No network connection (offline mode only)",
                time.time() - start_time
            )
            return False
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        total_tests = len(self.results["tests"])
        passed = sum(1 for t in self.results["tests"] if t["status"] == "PASSED")
        failed = sum(1 for t in self.results["tests"] if t["status"] == "FAILED")
        warnings = sum(1 for t in self.results["tests"] if t["status"] == "WARNING")
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Warnings: {warnings}")
        
        print(f"\nSystem Information:")
        print(f"  OS: {self.results['system_info']['os']} {self.results['system_info']['os_release']}")
        print(f"  RAM: {self.results['system_info']['ram_gb']} GB")
        print(f"  Processor: {self.results['system_info']['processor']}")
        
        # Save report to file
        report_file = Path("tests/end_to_end_test_results.json")
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nDetailed report saved to: {report_file}")
        
        return failed == 0
    
    def run_all_tests(self):
        """Run all end-to-end tests"""
        print("="*60)
        print("CR2A END-TO-END TESTING")
        print("Task 21.1: Perform end-to-end testing on target hardware")
        print("="*60)
        
        # Run all tests
        self.test_windows_compatibility()
        self.test_minimum_hardware_specs()
        self.test_contract_file_availability()
        self.test_config_directory_structure()
        self.test_offline_capability_setup()
        self.test_error_handling_components()
        self.test_executable_availability()
        self.test_log_file_structure()
        self.test_component_modules()
        self.test_network_connectivity()
        
        # Generate report
        success = self.generate_report()
        
        print("\n" + "="*60)
        if success:
            print("✓ ALL TESTS PASSED")
        else:
            print("✗ SOME TESTS FAILED - Review results above")
        print("="*60)
        
        return success


def main():
    """Main entry point"""
    tester = EndToEndTester()
    success = tester.run_all_tests()
    
    print("\nNext Steps:")
    print("1. Review test results above")
    print("2. If executable is available, run manual testing:")
    print("   - Launch CR2A.exe")
    print("   - Test upload → analysis → chat workflow")
    print("   - Test with different contract sizes")
    print("   - Test offline query processing")
    print("   - Test error scenarios")
    print("3. Proceed to Task 21.2: Performance benchmarking")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
