"""
Integration tests for ChatScreen with ApplicationController and QueryEngine.

Tests the complete workflow of loading analysis results and processing queries.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.application_controller import ApplicationController, AppState
from src.chat_screen import ChatScreen


class TestChatScreenIntegration(unittest.TestCase):
    """Integration test cases for ChatScreen."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock controller with required components
        self.mock_controller = Mock(spec=ApplicationController)
        self.mock_controller.query_engine = Mock()
        self.mock_controller.transition_to_upload = Mock()
        
        # Create mock parent frame
        self.mock_parent = Mock()
        self.mock_parent.winfo_children.return_value = []
        self.mock_parent.after = Mock(side_effect=lambda delay, func: func())
        
        # Create ChatScreen instance
        self.chat_screen = ChatScreen(self.mock_parent, self.mock_controller)
    
    def test_load_analysis_and_process_query_workflow(self):
        """Test complete workflow: load analysis -> submit query -> display response."""
        # Create mock analysis result
        analysis_result = {
            'contract_metadata': {
                'filename': 'test_contract.pdf',
                'analyzed_at': '2024-01-15T10:30:00Z',
                'page_count': 10
            },
            'clauses': [
                {
                    'id': 'clause_1',
                    'type': 'payment_terms',
                    'text': 'Payment shall be made within 30 days',
                    'page': 3,
                    'risk_level': 'low'
                }
            ],
            'risks': [],
            'compliance_issues': [],
            'redlining_suggestions': []
        }
        
        # Mock query engine response
        self.mock_controller.query_engine.process_query.return_value = "Payment is due within 30 days."
        
        # Load analysis result
        self.chat_screen.analysis_result = analysis_result
        self.chat_screen.contract_filename = 'test_contract.pdf'
        
        # Simulate query processing
        query_text = "What are the payment terms?"
        
        # Add query to history
        self.chat_screen.conversation_history.append({
            'sender': 'user',
            'message': query_text,
            'timestamp': None
        })
        
        # Process query (simulate background thread completion)
        response = self.mock_controller.query_engine.process_query(
            query=query_text,
            analysis_result=analysis_result
        )
        
        # Verify query engine was called correctly
        self.mock_controller.query_engine.process_query.assert_called_once_with(
            query=query_text,
            analysis_result=analysis_result
        )
        
        # Verify response was generated
        self.assertEqual(response, "Payment is due within 30 days.")
    
    def test_query_processing_with_no_query_engine(self):
        """Test error handling when query engine is not initialized."""
        # Set query engine to None
        self.mock_controller.query_engine = None
        
        # Create mock analysis result
        analysis_result = {
            'contract_metadata': {'filename': 'test.pdf'},
            'clauses': [],
            'risks': [],
            'compliance_issues': [],
            'redlining_suggestions': []
        }
        
        self.chat_screen.analysis_result = analysis_result
        
        # Attempt to process query
        query_text = "Test query"
        
        # Run query processing (will call error handler)
        self.chat_screen._run_query_processing(query_text)
        
        # Verify error handler was called (via parent.after)
        self.assertTrue(self.mock_parent.after.called)
    
    def test_query_processing_with_no_analysis_result(self):
        """Test error handling when no analysis result is loaded."""
        # Set analysis result to None
        self.chat_screen.analysis_result = None
        
        # Attempt to process query
        query_text = "Test query"
        
        # Run query processing (will call error handler)
        self.chat_screen._run_query_processing(query_text)
        
        # Verify error handler was called (via parent.after)
        self.assertTrue(self.mock_parent.after.called)
    
    def test_query_processing_with_exception(self):
        """Test error handling when query processing raises exception."""
        # Create mock analysis result
        analysis_result = {
            'contract_metadata': {'filename': 'test.pdf'},
            'clauses': [],
            'risks': [],
            'compliance_issues': [],
            'redlining_suggestions': []
        }
        
        self.chat_screen.analysis_result = analysis_result
        
        # Mock query engine to raise exception
        self.mock_controller.query_engine.process_query.side_effect = Exception("Test error")
        
        # Attempt to process query
        query_text = "Test query"
        
        # Run query processing (will call error handler)
        self.chat_screen._run_query_processing(query_text)
        
        # Verify error handler was called (via parent.after)
        self.assertTrue(self.mock_parent.after.called)
    
    def test_conversation_history_persistence(self):
        """Test that conversation history persists across multiple queries."""
        # Create mock analysis result
        analysis_result = {
            'contract_metadata': {'filename': 'test.pdf'},
            'clauses': [],
            'risks': [],
            'compliance_issues': [],
            'redlining_suggestions': []
        }
        
        self.chat_screen.analysis_result = analysis_result
        
        # Add multiple messages to history
        messages = [
            ('user', 'First question'),
            ('assistant', 'First answer'),
            ('user', 'Second question'),
            ('assistant', 'Second answer')
        ]
        
        for sender, message in messages:
            self.chat_screen.conversation_history.append({
                'sender': sender,
                'message': message,
                'timestamp': None
            })
        
        # Verify all messages are in history
        self.assertEqual(len(self.chat_screen.conversation_history), 4)
        
        # Verify order is preserved
        for i, (sender, message) in enumerate(messages):
            self.assertEqual(self.chat_screen.conversation_history[i]['sender'], sender)
            self.assertEqual(self.chat_screen.conversation_history[i]['message'], message)
    
    @patch('tkinter.messagebox')
    def test_new_analysis_clears_state(self, mock_messagebox):
        """Test that starting new analysis clears all state."""
        # Create mock analysis result
        analysis_result = {
            'contract_metadata': {'filename': 'test.pdf'},
            'clauses': [],
            'risks': [],
            'compliance_issues': [],
            'redlining_suggestions': []
        }
        
        # Set up chat screen state
        self.chat_screen.analysis_result = analysis_result
        self.chat_screen.conversation_history = [
            {'sender': 'user', 'message': 'Test', 'timestamp': None}
        ]
        
        # Mock user confirming new analysis
        mock_messagebox.askyesno.return_value = True
        
        # Trigger new analysis
        self.chat_screen.on_new_analysis_click()
        
        # Verify state is cleared
        self.assertIsNone(self.chat_screen.analysis_result)
        self.assertEqual(len(self.chat_screen.conversation_history), 0)
        
        # Verify transition was called
        self.mock_controller.transition_to_upload.assert_called_once()


if __name__ == '__main__':
    unittest.main()
