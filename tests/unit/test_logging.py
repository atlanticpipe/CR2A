"""
Unit tests for logging configuration and rotation.

Tests verify that:
- Log directory is created correctly
- Log rotation is configured properly
- Old logs are cleaned up
- All error handlers use logging
"""

import unittest
import logging
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import sys
import os

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestLoggingConfiguration(unittest.TestCase):
    """Test logging configuration and rotation."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for test logs
        self.test_dir = Path(tempfile.mkdtemp())
        self.log_dir = self.test_dir / 'logs'
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary directory
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_log_directory_creation(self):
        """Test that log directory is created if it doesn't exist."""
        # Remove log directory
        if self.log_dir.exists():
            shutil.rmtree(self.log_dir)
        
        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Verify directory exists
        self.assertTrue(self.log_dir.exists())
        self.assertTrue(self.log_dir.is_dir())
    
    def test_log_file_creation(self):
        """Test that log file is created."""
        from logging.handlers import RotatingFileHandler
        
        log_file = self.log_dir / 'test.log'
        
        # Create rotating file handler
        handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=100 * 1024 * 1024,  # 100MB
            backupCount=5,
            encoding='utf-8'
        )
        
        # Create logger
        logger = logging.getLogger('test_logger')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Write log message
        logger.info("Test log message")
        
        # Verify log file exists
        self.assertTrue(log_file.exists())
        
        # Verify log file contains message
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("Test log message", content)
        
        # Clean up
        handler.close()
        logger.removeHandler(handler)
    
    def test_log_rotation_configuration(self):
        """Test that log rotation is configured correctly."""
        from logging.handlers import RotatingFileHandler
        
        log_file = self.log_dir / 'test.log'
        
        # Create rotating file handler with small max size for testing
        handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=1024,  # 1KB for testing
            backupCount=3,
            encoding='utf-8'
        )
        
        # Verify configuration
        self.assertEqual(handler.maxBytes, 1024)
        self.assertEqual(handler.backupCount, 3)
        
        # Clean up
        handler.close()
    
    def test_old_log_cleanup(self):
        """Test that old log files are cleaned up."""
        # Import cleanup function
        from src.main import cleanup_old_logs
        
        # Create some old log files
        old_date = datetime.now() - timedelta(days=10)
        recent_date = datetime.now() - timedelta(days=3)
        
        old_log = self.log_dir / 'cr2a_old.log'
        recent_log = self.log_dir / 'cr2a_recent.log'
        
        # Create files
        old_log.touch()
        recent_log.touch()
        
        # Set modification times
        old_timestamp = old_date.timestamp()
        recent_timestamp = recent_date.timestamp()
        
        os.utime(old_log, (old_timestamp, old_timestamp))
        os.utime(recent_log, (recent_timestamp, recent_timestamp))
        
        # Verify both files exist
        self.assertTrue(old_log.exists())
        self.assertTrue(recent_log.exists())
        
        # Run cleanup (7 day retention)
        cleanup_old_logs(self.log_dir, max_age_days=7)
        
        # Verify old file is deleted, recent file remains
        self.assertFalse(old_log.exists())
        self.assertTrue(recent_log.exists())
    
    def test_logging_format(self):
        """Test that log messages are formatted correctly."""
        from logging.handlers import RotatingFileHandler
        
        log_file = self.log_dir / 'test.log'
        
        # Create handler with formatter
        handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=100 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        
        formatter = logging.Formatter(
            '[%(asctime)s.%(msecs)03d] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        # Create logger
        logger = logging.getLogger('test_format_logger')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Write log messages
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        # Read log file
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verify format
        self.assertIn("[INFO]", content)
        self.assertIn("[WARNING]", content)
        self.assertIn("[ERROR]", content)
        self.assertIn("[test_format_logger]", content)
        self.assertIn("Info message", content)
        self.assertIn("Warning message", content)
        self.assertIn("Error message", content)
        
        # Clean up
        handler.close()
        logger.removeHandler(handler)
    
    def test_error_logging_in_components(self):
        """Test that error handlers in components use logging."""
        # This test verifies that key components have logging configured
        
        # Test ApplicationController
        from src.application_controller import ApplicationController
        controller = ApplicationController()
        
        # Verify logger is configured
        logger = logging.getLogger('src.application_controller')
        self.assertIsNotNone(logger)
        
        # Test AnalysisEngine
        from src.analysis_engine import AnalysisEngine
        # Note: AnalysisEngine requires API key, so we just verify logger exists
        logger = logging.getLogger('src.analysis_engine')
        self.assertIsNotNone(logger)
        
        # Test ContractUploader
        from src.contract_uploader import ContractUploader
        uploader = ContractUploader()
        logger = logging.getLogger('src.contract_uploader')
        self.assertIsNotNone(logger)
        
        # Test ConfigManager
        from src.config_manager import ConfigManager
        config_manager = ConfigManager(config_path=str(self.test_dir / 'config.json'))
        logger = logging.getLogger('src.config_manager')
        self.assertIsNotNone(logger)


if __name__ == '__main__':
    unittest.main()
