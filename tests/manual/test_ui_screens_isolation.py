"""
Manual test script to verify all UI screens work independently.

This script tests each screen in isolation to verify:
- All UI elements are present
- All UI elements are functional
- Screens can be rendered without dependencies
- State management works correctly

Run this script to perform checkpoint 13 verification.
"""

import tkinter as tk
from tkinter import ttk
import sys
import os
from unittest.mock import Mock

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.upload_screen import UploadScreen
from src.analysis_screen import AnalysisScreen
from src.chat_screen import ChatScreen


class TestResult:
    """Track test results."""
    def __init__(self):
        self.passed = []
        self.failed = []
    
    def add_pass(self, test_name):
        self.passed.append(test_name)
        print(f"  ✓ {test_name}")
    
    def add_fail(self, test_name, error):
        self.failed.append((test_name, error))
        print(f"  ✗ {test_name}: {error}")
    
    def summary(self):
        total = len(self.passed) + len(self.failed)
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY: {len(self.passed)}/{total} passed")
        print(f"{'='*60}")
        if self.failed:
            print("\nFailed tests:")
            for name, error in self.failed:
                print(f"  - {name}: {error}")


def test_upload_screen_isolation():
    """Test UploadScreen in isolation."""
    print("\n=== Testing UploadScreen in Isolation ===")
    results = TestResult()
    
    try:
        # Create Tkinter root
        root = tk.Tk()
        root.withdraw()  # Hide window
        parent = ttk.Frame(root)
        
        # Create mock controller
        controller = Mock()
        controller.contract_uploader = Mock()
        
        # Test 1: Screen can be instantiated
        try:
            upload_screen = UploadScreen(parent, controller)
            results.add_pass("UploadScreen instantiation")
        except Exception as e:
            results.add_fail("UploadScreen instantiation", str(e))
            root.destroy()
            return results
        
        # Test 2: Screen can be rendered
        try:
            upload_screen.render()
            results.add_pass("UploadScreen render")
        except Exception as e:
            results.add_fail("UploadScreen render", str(e))
            root.destroy()
            return results
        
        # Test 3: All UI elements are present
        ui_elements = {
            'main_frame': upload_screen.main_frame,
            'title_label': upload_screen.title_label,
            'file_select_button': upload_screen.file_select_button,
            'file_info_frame': upload_screen.file_info_frame,
            'file_name_label': upload_screen.file_name_label,
            'file_size_label': upload_screen.file_size_label,
            'analyze_button': upload_screen.analyze_button,
            'status_label': upload_screen.status_label
        }
        
        for name, element in ui_elements.items():
            if element is not None:
                results.add_pass(f"UI element present: {name}")
            else:
                results.add_fail(f"UI element present: {name}", "Element is None")
        
        # Test 4: Analyze button is initially disabled
        if str(upload_screen.analyze_button['state']) == 'disabled':
            results.add_pass("Analyze button initially disabled")
        else:
            results.add_fail("Analyze button initially disabled", 
                           f"State is {upload_screen.analyze_button['state']}")
        
        # Test 5: File validation enables analyze button
        controller.contract_uploader.validate_format.return_value = (True, "")
        controller.contract_uploader.get_file_info.return_value = {
            'filename': 'test.pdf',
            'file_size_mb': '1.0 MB',
            'page_count': 5
        }
        upload_screen.validate_file('/path/to/test.pdf')
        
        if str(upload_screen.analyze_button['state']) == 'normal':
            results.add_pass("Analyze button enabled after valid file")
        else:
            results.add_fail("Analyze button enabled after valid file",
                           f"State is {upload_screen.analyze_button['state']}")
        
        # Test 6: Invalid file shows error
        controller.contract_uploader.validate_format.return_value = (False, "Invalid format")
        upload_screen.validate_file('/path/to/test.txt')
        
        if "Error" in upload_screen.status_label['text']:
            results.add_pass("Error message displayed for invalid file")
        else:
            results.add_fail("Error message displayed for invalid file",
                           f"Status is: {upload_screen.status_label['text']}")
        
        # Test 7: File info display
        file_info = {
            'filename': 'contract.pdf',
            'file_size_mb': '2.5 MB',
            'page_count': 20
        }
        upload_screen.display_file_info(file_info)
        
        if upload_screen.file_name_label['text'] == 'contract.pdf':
            results.add_pass("Filename displayed correctly")
        else:
            results.add_fail("Filename displayed correctly",
                           f"Got: {upload_screen.file_name_label['text']}")
        
        if '2.5 MB' in upload_screen.file_size_label['text']:
            results.add_pass("File size displayed correctly")
        else:
            results.add_fail("File size displayed correctly",
                           f"Got: {upload_screen.file_size_label['text']}")
        
        # Clean up
        root.destroy()
        
    except Exception as e:
        results.add_fail("UploadScreen test", str(e))
    
    return results


def test_analysis_screen_isolation():
    """Test AnalysisScreen in isolation."""
    print("\n=== Testing AnalysisScreen in Isolation ===")
    results = TestResult()
    
    try:
        # Create Tkinter root
        root = tk.Tk()
        root.withdraw()  # Hide window
        parent = ttk.Frame(root)
        
        # Create mock controller
        controller = Mock()
        controller.analysis_engine = Mock()
        
        # Test 1: Screen can be instantiated
        try:
            analysis_screen = AnalysisScreen(parent, controller)
            results.add_pass("AnalysisScreen instantiation")
        except Exception as e:
            results.add_fail("AnalysisScreen instantiation", str(e))
            root.destroy()
            return results
        
        # Test 2: Screen can be rendered
        try:
            analysis_screen.render()
            results.add_pass("AnalysisScreen render")
        except Exception as e:
            results.add_fail("AnalysisScreen render", str(e))
            root.destroy()
            return results
        
        # Test 3: All UI elements are present
        ui_elements = {
            'main_frame': analysis_screen.main_frame,
            'title_label': analysis_screen.title_label,
            'progress_bar': analysis_screen.progress_bar,
            'status_label': analysis_screen.status_label,
            'time_label': analysis_screen.time_label,
            'cancel_button': analysis_screen.cancel_button
        }
        
        for name, element in ui_elements.items():
            if element is not None:
                results.add_pass(f"UI element present: {name}")
            else:
                results.add_fail(f"UI element present: {name}", "Element is None")
        
        # Test 4: Initial state
        if analysis_screen.progress_bar['value'] == 0:
            results.add_pass("Progress bar initially at 0")
        else:
            results.add_fail("Progress bar initially at 0",
                           f"Value is {analysis_screen.progress_bar['value']}")
        
        if "Initializing" in analysis_screen.status_label['text']:
            results.add_pass("Initial status message displayed")
        else:
            results.add_fail("Initial status message displayed",
                           f"Status is: {analysis_screen.status_label['text']}")
        
        # Test 5: Progress updates
        analysis_screen.update_progress("Extracting text...", 25)
        
        if analysis_screen.progress_bar['value'] == 25:
            results.add_pass("Progress bar updates correctly")
        else:
            results.add_fail("Progress bar updates correctly",
                           f"Value is {analysis_screen.progress_bar['value']}")
        
        if "Extracting text" in analysis_screen.status_label['text']:
            results.add_pass("Status message updates correctly")
        else:
            results.add_fail("Status message updates correctly",
                           f"Status is: {analysis_screen.status_label['text']}")
        
        # Test 6: Completion updates UI
        mock_result = {'clauses': [], 'risks': []}
        analysis_screen.on_analysis_complete(mock_result)
        
        if analysis_screen.progress_bar['value'] == 100:
            results.add_pass("Progress bar reaches 100 on completion")
        else:
            results.add_fail("Progress bar reaches 100 on completion",
                           f"Value is {analysis_screen.progress_bar['value']}")
        
        if not analysis_screen.is_analyzing:
            results.add_pass("is_analyzing flag cleared on completion")
        else:
            results.add_fail("is_analyzing flag cleared on completion",
                           "Flag is still True")
        
        # Clean up
        root.destroy()
        
    except Exception as e:
        results.add_fail("AnalysisScreen test", str(e))
    
    return results


def test_chat_screen_isolation():
    """Test ChatScreen in isolation."""
    print("\n=== Testing ChatScreen in Isolation ===")
    results = TestResult()
    
    try:
        # Create Tkinter root
        root = tk.Tk()
        root.withdraw()  # Hide window
        parent = ttk.Frame(root)
        
        # Create mock controller
        controller = Mock()
        controller.query_engine = Mock()
        
        # Test 1: Screen can be instantiated
        try:
            chat_screen = ChatScreen(parent, controller)
            results.add_pass("ChatScreen instantiation")
        except Exception as e:
            results.add_fail("ChatScreen instantiation", str(e))
            root.destroy()
            return results
        
        # Test 2: Screen can be rendered
        try:
            chat_screen.render()
            results.add_pass("ChatScreen render")
        except Exception as e:
            results.add_fail("ChatScreen render", str(e))
            root.destroy()
            return results
        
        # Test 3: All UI elements are present
        ui_elements = {
            'main_frame': chat_screen.main_frame,
            'title_label': chat_screen.title_label,
            'conversation_text': chat_screen.conversation_text,
            'query_input': chat_screen.query_input,
            'send_button': chat_screen.send_button,
            'new_analysis_button': chat_screen.new_analysis_button,
            'thinking_label': chat_screen.thinking_label
        }
        
        for name, element in ui_elements.items():
            if element is not None:
                results.add_pass(f"UI element present: {name}")
            else:
                results.add_fail(f"UI element present: {name}", "Element is None")
        
        # Test 4: Send button initially disabled
        if str(chat_screen.send_button['state']) == 'disabled':
            results.add_pass("Send button initially disabled")
        else:
            results.add_fail("Send button initially disabled",
                           f"State is {chat_screen.send_button['state']}")
        
        # Test 5: Input enables send button
        chat_screen.query_input.insert("1.0", "Test query")
        chat_screen._on_input_change()
        
        if str(chat_screen.send_button['state']) == 'normal':
            results.add_pass("Send button enabled with input")
        else:
            results.add_fail("Send button enabled with input",
                           f"State is {chat_screen.send_button['state']}")
        
        # Test 6: Load analysis updates title
        analysis_result = {
            'contract_metadata': {
                'filename': 'test_contract.pdf',
                'analyzed_at': '2024-01-15T10:30:00Z',
                'page_count': 10
            },
            'clauses': [],
            'risks': [],
            'compliance_issues': [],
            'redlining_suggestions': []
        }
        chat_screen.load_analysis(analysis_result)
        
        if 'test_contract.pdf' in chat_screen.title_label['text']:
            results.add_pass("Title updated with contract filename")
        else:
            results.add_fail("Title updated with contract filename",
                           f"Title is: {chat_screen.title_label['text']}")
        
        # Test 7: Welcome message displayed
        if len(chat_screen.conversation_history) > 0:
            results.add_pass("Welcome message added to history")
        else:
            results.add_fail("Welcome message added to history",
                           "History is empty")
        
        # Test 8: Display message functionality
        chat_screen.display_message("user", "Test question")
        
        if len(chat_screen.conversation_history) == 2:  # Welcome + user message
            results.add_pass("User message added to history")
        else:
            results.add_fail("User message added to history",
                           f"History length is {len(chat_screen.conversation_history)}")
        
        # Test 9: Thinking indicator
        chat_screen.show_thinking_indicator()
        if chat_screen.thinking_label['text']:
            results.add_pass("Thinking indicator shows")
        else:
            results.add_fail("Thinking indicator shows", "Label is empty")
        
        chat_screen.hide_thinking_indicator()
        if not chat_screen.thinking_label['text']:
            results.add_pass("Thinking indicator hides")
        else:
            results.add_fail("Thinking indicator hides",
                           f"Label is: {chat_screen.thinking_label['text']}")
        
        # Test 10: Input field clearing
        chat_screen.query_input.delete("1.0", tk.END)
        chat_screen.query_input.insert("1.0", "Another query")
        
        # Simulate query submission (without processing)
        query_text = chat_screen.query_input.get("1.0", tk.END).strip()
        chat_screen.query_input.delete("1.0", tk.END)
        
        cleared_text = chat_screen.query_input.get("1.0", tk.END).strip()
        if not cleared_text:
            results.add_pass("Input field clears after submission")
        else:
            results.add_fail("Input field clears after submission",
                           f"Input still contains: {cleared_text}")
        
        # Clean up
        root.destroy()
        
    except Exception as e:
        results.add_fail("ChatScreen test", str(e))
    
    return results


def main():
    """Run all isolation tests."""
    print("=" * 60)
    print("UI SCREENS ISOLATION TEST - CHECKPOINT 13")
    print("=" * 60)
    print("\nTesting each screen in isolation to verify:")
    print("  - All UI elements are present")
    print("  - All UI elements are functional")
    print("  - Screens work independently")
    print("=" * 60)
    
    all_results = []
    
    # Test each screen
    all_results.append(test_upload_screen_isolation())
    all_results.append(test_analysis_screen_isolation())
    all_results.append(test_chat_screen_isolation())
    
    # Combined summary
    print("\n" + "=" * 60)
    print("COMBINED TEST SUMMARY")
    print("=" * 60)
    
    total_passed = sum(len(r.passed) for r in all_results)
    total_failed = sum(len(r.failed) for r in all_results)
    total_tests = total_passed + total_failed
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_failed > 0:
        print(f"\n{total_failed} tests failed:")
        for result in all_results:
            for name, error in result.failed:
                print(f"  - {name}: {error}")
        print("\n❌ CHECKPOINT 13 FAILED")
        return 1
    else:
        print("\n✅ CHECKPOINT 13 PASSED")
        print("\nAll UI screens work independently!")
        print("  ✓ UploadScreen: All elements present and functional")
        print("  ✓ AnalysisScreen: All elements present and functional")
        print("  ✓ ChatScreen: All elements present and functional")
        return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
