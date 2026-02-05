"""
CR2A Qt GUI - Desktop GUI using PyQt5 (no tkinter!)

A PyQt5-based desktop interface that's more reliable than tkinter.
Supports both standard and exhaustive analysis modes with verification.
"""

import os
import sys
import json
import logging
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QFileDialog, QMessageBox,
    QProgressBar, QTabWidget, QScrollArea, QGroupBox, QLineEdit,
    QMenuBar, QMenu, QAction, QDialog, QFormLayout, QDialogButtonBox,
    QCheckBox, QSpinBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent))

# Use absolute imports for PyInstaller compatibility
from src.analysis_engine import AnalysisEngine
from src.query_engine import QueryEngine
from src.openai_fallback_client import OpenAIClient
from src.config_manager import ConfigManager
from src.exhaustiveness_models import VerifiedAnalysisResult, PresenceStatus
from src.history_store import HistoryStore, HistoryStoreError
from src.history_tab import HistoryTab
from src.structured_analysis_view import StructuredAnalysisView


class AnalysisThread(QThread):
    """Background thread for contract analysis."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(str, int)
    
    def __init__(self, engine, filepath, exhaustive=False, num_passes=2):
        super().__init__()
        self.engine = engine
        self.filepath = filepath
        self.exhaustive = exhaustive
        self.num_passes = num_passes
    
    def run(self):
        try:
            def progress_callback(status, percent):
                self.progress.emit(status, percent)
            
            result = self.engine.analyze_contract(
                self.filepath,
                progress_callback=progress_callback,
                exhaustive=self.exhaustive,
                num_passes=self.num_passes
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class QueryThread(QThread):
    """Background thread for query processing."""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, engine, question, analysis):
        super().__init__()
        self.engine = engine
        self.question = question
        self.analysis = analysis
    
    def run(self):
        try:
            answer = self.engine.process_query(self.question, self.analysis)
            self.finished.emit(answer)
        except Exception as e:
            self.error.emit(str(e))


class CR2A_GUI(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.analysis_engine = None
        self.query_engine = None
        self.current_analysis = None
        self.current_file = None
        self.config_manager = None
        self.contract_text = None  # Store extracted text for verification
        self.history_store = None  # History store for persistent analysis records
        self.current_history_record_id = None  # Track the record_id of currently loaded historical analysis
        
        # Versioning components
        self.version_db = None
        self.differential_storage = None
        self.contract_identity_detector = None
        self.change_comparator = None
        self.version_manager = None
        
        self.init_ui()
        self.init_config()
        self.init_versioning()
        self.init_history_store()
        self.init_engines()
    
    def init_config(self):
        """Initialize configuration manager."""
        try:
            self.config_manager = ConfigManager()
            self.config_manager.load_config()
        except Exception as e:
            QMessageBox.warning(
                self,
                "Configuration Warning",
                f"Failed to load configuration:\n{str(e)}\n\nUsing defaults."
            )
    
    def init_versioning(self):
        """Initialize versioning components for contract change tracking."""
        try:
            from src.version_database import VersionDatabase
            from src.differential_storage import DifferentialStorage
            from src.contract_identity_detector import ContractIdentityDetector
            from src.change_comparator import ChangeComparator
            from src.version_manager import VersionManager
            
            # Initialize version database
            self.version_db = VersionDatabase()
            logger.info("Version database initialized")
            
            # Initialize differential storage
            self.differential_storage = DifferentialStorage(self.version_db)
            logger.info("Differential storage initialized")
            
            # Initialize other versioning components
            self.contract_identity_detector = ContractIdentityDetector(self.differential_storage)
            self.change_comparator = ChangeComparator()
            self.version_manager = VersionManager(self.differential_storage)
            
            logger.info("Versioning system initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize versioning system: %s", e, exc_info=True)
            QMessageBox.warning(
                self,
                "Versioning Warning",
                f"Failed to initialize versioning system:\n{str(e)}\n\n"
                "Contract versioning features will be disabled.\n"
                "You can still analyze contracts normally."
            )
            self.version_db = None
            self.differential_storage = None
            self.contract_identity_detector = None
            self.change_comparator = None
            self.version_manager = None
    
    def init_history_store(self):
        """Initialize history store for persistent analysis records."""
        try:
            self.history_store = HistoryStore()
            logger.info("History store initialized successfully")
        except HistoryStoreError as e:
            logger.error("Failed to initialize history store: %s", e)
            QMessageBox.warning(
                self,
                "History Store Warning",
                f"Failed to initialize history storage:\n{str(e)}\n\n"
                "Analysis history features will be disabled.\n"
                "You can still analyze contracts normally."
            )
            self.history_store = None
        except Exception as e:
            logger.error("Unexpected error initializing history store: %s", e)
            QMessageBox.warning(
                self,
                "History Store Warning",
                f"Unexpected error initializing history storage:\n{str(e)}\n\n"
                "Analysis history features will be disabled.\n"
                "You can still analyze contracts normally."
            )
            self.history_store = None
        
        # Initialize History tab if history_store is available
        self.init_history_tab()
    
    def init_history_tab(self):
        """Initialize the History tab if history store is available."""
        if self.history_store is not None:
            try:
                # Create History tab with optional differential_storage
                self.history_tab = HistoryTab(
                    self.history_store,
                    differential_storage=self.differential_storage
                )
                
                # Add tab after Chat tab
                self.tabs.addTab(self.history_tab, "📜 History")
                
                # Connect signals to handler methods
                self.history_tab.analysis_selected.connect(self.on_history_selected)
                self.history_tab.analysis_deleted.connect(self.on_history_deleted)
                
                logger.info("History tab initialized successfully (versioning: %s)", 
                           "enabled" if self.differential_storage else "disabled")
            except Exception as e:
                logger.error("Failed to initialize history tab: %s", e)
                QMessageBox.warning(
                    self,
                    "History Tab Warning",
                    f"Failed to initialize history tab:\n{str(e)}\n\n"
                    "History tab will not be available."
                )
                self.history_tab = None
        else:
            logger.info("History tab not initialized (history store unavailable)")
    
    def on_history_selected(self, record_id: str):
        """
        Handle history record selection.
        
        Loads the full analysis from HistoryStore, sets it as current_analysis,
        displays it in the Analysis tab, enables the Chat tab for querying,
        and switches to the Analysis tab.
        
        Args:
            record_id: ID of the selected analysis record
        """
        logger.info("History record selected: %s", record_id)
        
        # Check if history store is available
        if self.history_store is None:
            QMessageBox.warning(
                self,
                "History Unavailable",
                "History store is not available.\n"
                "Cannot load historical analysis."
            )
            return
        
        try:
            # Load full analysis from HistoryStore
            analysis_result = self.history_store.get(record_id)
            
            # Handle load errors
            if analysis_result is None:
                logger.error("Failed to load analysis: %s", record_id)
                QMessageBox.critical(
                    self,
                    "Load Error",
                    f"Failed to load the selected analysis.\n\n"
                    f"The analysis file may be corrupted or missing.\n"
                    f"Record ID: {record_id}"
                )
                return
            
            # Set as current_analysis
            self.current_analysis = analysis_result
            
            # Store the record_id for tracking
            self.current_history_record_id = record_id
            
            # Set current_file to the filename from metadata
            if analysis_result.metadata and analysis_result.metadata.filename:
                self.current_file = analysis_result.metadata.filename
            
            # Display in Analysis tab
            self.display_analysis(analysis_result)
            
            # Enable Chat tab for querying (it's already enabled by default, but ensure it's accessible)
            # The chat tab is always enabled, but we can update the chat history to indicate a new analysis is loaded
            self.chat_history.append(
                f"<br><b>📜 Historical Analysis Loaded:</b> {analysis_result.metadata.filename}<br>"
                f"<i>You can now ask questions about this analysis.</i><br>"
            )
            
            # Switch to Analysis tab
            self.tabs.setCurrentIndex(1)  # Analysis tab is at index 1
            
            logger.info("Successfully loaded historical analysis: %s", record_id)
            self.statusBar().showMessage(f"Loaded analysis: {analysis_result.metadata.filename}")
            
        except Exception as e:
            logger.error("Unexpected error loading analysis %s: %s", record_id, e)
            QMessageBox.critical(
                self,
                "Load Error",
                f"An unexpected error occurred while loading the analysis:\n\n{str(e)}"
            )
    
    def on_history_deleted(self, record_id: str):
        """
        Handle history record deletion.
        
        Performs cleanup if the deleted analysis was currently loaded,
        and logs the deletion for debugging purposes.
        
        Args:
            record_id: ID of the deleted analysis record
        """
        logger.info("History record deleted: %s", record_id)
        
        # Check if the deleted analysis is currently loaded
        if self.current_history_record_id == record_id:
            logger.info("Deleted analysis was currently loaded, clearing current analysis")
            
            # Clear the current analysis
            self.current_analysis = None
            self.current_file = None
            self.current_history_record_id = None
            
            # Clear the analysis display
            self._clear_analysis_display()
            
            # Update the chat history to indicate the analysis was deleted
            self.chat_history.append(
                "<br><b>⚠️ Notice:</b> The currently loaded analysis has been deleted from history.<br>"
                "<i>Please analyze a new contract or select another analysis from history.</i><br>"
            )
            
            # Update status bar
            self.statusBar().showMessage("Current analysis was deleted from history")
            
            logger.info("Cleared current analysis after deletion")
    
    def _clear_analysis_display(self):
        """Clear the analysis display and show the 'no analysis' message."""
        # Clear existing content
        while self.analysis_layout.count():
            child = self.analysis_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Show the "no analysis" message
        self.no_analysis_label = QLabel("No contract analyzed yet.\nGo to Upload tab to analyze a contract.")
        self.no_analysis_label.setAlignment(Qt.AlignCenter)
        self.no_analysis_label.setStyleSheet("padding: 50px; font-size: 14px; color: #666;")
        self.analysis_layout.addWidget(self.no_analysis_label)
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("CR2A - Contract Review & Analysis")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Title
        title = QLabel("Contract Review & Analysis")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Upload tab
        self.upload_tab = self.create_upload_tab()
        self.tabs.addTab(self.upload_tab, "📄 Upload")
        
        # Analysis tab
        self.analysis_tab = self.create_analysis_tab()
        self.tabs.addTab(self.analysis_tab, "📊 Analysis")
        
        # Chat tab
        self.chat_tab = self.create_chat_tab()
        self.tabs.addTab(self.chat_tab, "💬 Chat")
        
        # History tab (will be initialized after history_store is ready)
        self.history_tab = None
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def create_upload_tab(self):
        """Create the upload tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Instructions
        instructions = QLabel(
            "Upload a contract file (PDF, DOCX, or TXT) to begin analysis.\n"
            "The analysis will extract parties, terms, dates, risks, and more."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("padding: 20px; font-size: 14px;")
        layout.addWidget(instructions)
        
        # File selection
        file_layout = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("padding: 10px; border: 1px solid #ccc; background: #f5f5f5;")
        file_layout.addWidget(self.file_label)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_file)
        browse_btn.setStyleSheet("padding: 10px; font-size: 14px;")
        file_layout.addWidget(browse_btn)
        
        layout.addLayout(file_layout)
        
        # Exhaustive analysis options
        exhaustive_group = QGroupBox("Analysis Options")
        exhaustive_layout = QVBoxLayout()
        exhaustive_group.setLayout(exhaustive_layout)
        
        self.exhaustive_checkbox = QCheckBox("Enable Exhaustive Analysis (Multi-Pass Verification)")
        self.exhaustive_checkbox.setToolTip(
            "Performs multiple analysis passes with verification to ensure\n"
            "absolute certainty about clause presence and prevent hallucinations."
        )
        self.exhaustive_checkbox.stateChanged.connect(self.on_exhaustive_changed)
        exhaustive_layout.addWidget(self.exhaustive_checkbox)
        
        # Number of passes
        passes_layout = QHBoxLayout()
        passes_label = QLabel("Number of passes:")
        passes_layout.addWidget(passes_label)
        
        self.passes_spinbox = QSpinBox()
        self.passes_spinbox.setRange(2, 5)
        self.passes_spinbox.setValue(2)
        self.passes_spinbox.setEnabled(False)
        self.passes_spinbox.setToolTip("More passes = higher accuracy but longer analysis time")
        passes_layout.addWidget(self.passes_spinbox)
        passes_layout.addStretch()
        exhaustive_layout.addLayout(passes_layout)
        
        # Info label
        self.exhaustive_info = QLabel(
            "ℹ️ Exhaustive analysis runs multiple passes to verify findings,\n"
            "detect hallucinations, and provide confidence scores."
        )
        self.exhaustive_info.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        self.exhaustive_info.setVisible(False)
        exhaustive_layout.addWidget(self.exhaustive_info)
        
        layout.addWidget(exhaustive_group)
        
        # Analyze button
        self.analyze_btn = QPushButton("Analyze Contract")
        self.analyze_btn.clicked.connect(self.analyze_contract)
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setStyleSheet(
            "padding: 15px; font-size: 16px; font-weight: bold; "
            "background: #4CAF50; color: white;"
        )
        layout.addWidget(self.analyze_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status
        self.upload_status = QLabel("")
        self.upload_status.setWordWrap(True)
        self.upload_status.setStyleSheet("padding: 10px; font-size: 12px;")
        layout.addWidget(self.upload_status)
        
        layout.addStretch()
        
        return widget
    
    def on_exhaustive_changed(self, state):
        """Handle exhaustive checkbox state change."""
        enabled = state == Qt.Checked
        self.passes_spinbox.setEnabled(enabled)
        self.exhaustive_info.setVisible(enabled)
        
        if enabled:
            self.analyze_btn.setText("Analyze Contract (Exhaustive)")
            self.analyze_btn.setStyleSheet(
                "padding: 15px; font-size: 16px; font-weight: bold; "
                "background: #2196F3; color: white;"
            )
        else:
            self.analyze_btn.setText("Analyze Contract")
            self.analyze_btn.setStyleSheet(
                "padding: 15px; font-size: 16px; font-weight: bold; "
                "background: #4CAF50; color: white;"
            )
    
    def create_analysis_tab(self):
        """Create the analysis results tab with structured view."""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Create structured analysis view
        self.structured_view = StructuredAnalysisView()
        layout.addWidget(self.structured_view)
        
        # Keep the old layout for backward compatibility (hidden by default)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVisible(False)  # Hidden by default
        scroll_content = QWidget()
        self.analysis_layout = QVBoxLayout()
        scroll_content.setLayout(self.analysis_layout)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        # Initial message
        self.no_analysis_label = QLabel("No contract analyzed yet.\nGo to Upload tab to analyze a contract.")
        self.no_analysis_label.setAlignment(Qt.AlignCenter)
        self.no_analysis_label.setStyleSheet("padding: 50px; font-size: 14px; color: #666;")
        self.analysis_layout.addWidget(self.no_analysis_label)
        
        return widget
    
    def create_chat_tab(self):
        """Create the chat/Q&A tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Chat history
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("padding: 10px; font-size: 13px;")
        layout.addWidget(self.chat_history)
        
        # Input area
        input_layout = QHBoxLayout()
        
        self.question_input = QLineEdit()
        self.question_input.setPlaceholderText("Ask a question about the contract...")
        self.question_input.setStyleSheet("padding: 10px; font-size: 14px;")
        self.question_input.returnPressed.connect(self.send_question)
        input_layout.addWidget(self.question_input)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_question)
        self.send_btn.setStyleSheet("padding: 10px; font-size: 14px; min-width: 100px;")
        input_layout.addWidget(self.send_btn)
        
        layout.addLayout(input_layout)
        
        # Initial message
        self.chat_history.append("💬 <b>Welcome to CR2A Chat!</b><br>")
        self.chat_history.append("Analyze a contract first, then ask questions here.<br>")
        self.chat_history.append("<i>Example questions:</i><br>")
        self.chat_history.append("• Who are the parties?<br>")
        self.chat_history.append("• What is the contract value?<br>")
        self.chat_history.append("• When does it expire?<br>")
        
        return widget
    
    def create_menu_bar(self):
        """Create the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        settings_action = QAction("Settings...", self)
        settings_action.triggered.connect(self.open_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        # Export submenu
        export_menu = file_menu.addMenu("Export")
        
        export_analysis_action = QAction("Export Analysis Report...", self)
        export_analysis_action.triggered.connect(self.export_analysis_report)
        export_menu.addAction(export_analysis_action)
        
        export_chat_action = QAction("Export Chat Log...", self)
        export_chat_action.triggered.connect(self.export_chat_log)
        export_menu.addAction(export_chat_action)
        
        export_all_action = QAction("Export All...", self)
        export_all_action.triggered.connect(self.export_all)
        export_menu.addAction(export_all_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def open_settings(self):
        """Open settings dialog."""
        dialog = SettingsDialog(self, self.config_manager)
        if dialog.exec_() == QDialog.Accepted:
            # Reload API key and reinitialize engines
            self.init_engines()
            QMessageBox.information(
                self,
                "Settings Saved",
                "Settings have been saved successfully.\nEngines reinitialized with new API key."
            )
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About CR2A",
            "CR2A - Contract Review & Analysis\n\n"
            "Version 1.0\n\n"
            "A PyQt5-based contract analysis tool powered by OpenAI.\n\n"
            "© 2024 CR2A Project"
        )
    
    def export_analysis_report(self):
        """Export analysis report to a text file."""
        if not self.current_analysis:
            QMessageBox.warning(self, "No Analysis", "No analysis to export. Please analyze a contract first.")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Analysis Report",
            "analysis_report.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if not filename:
            return
        
        try:
            report = self._generate_analysis_report()
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)
            QMessageBox.information(self, "Export Complete", f"Analysis report exported to:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export report:\n{str(e)}")
    
    def export_chat_log(self):
        """Export chat log to a text file."""
        chat_text = self.chat_history.toPlainText()
        if not chat_text.strip():
            QMessageBox.warning(self, "No Chat", "No chat history to export.")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Chat Log",
            "chat_log.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("CR2A Chat Log\n")
                f.write("=" * 50 + "\n\n")
                f.write(chat_text)
            QMessageBox.information(self, "Export Complete", f"Chat log exported to:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export chat log:\n{str(e)}")
    
    def export_all(self):
        """Export both analysis report and chat log."""
        if not self.current_analysis:
            QMessageBox.warning(self, "No Analysis", "No analysis to export. Please analyze a contract first.")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export All",
            "cr2a_export.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if not filename:
            return
        
        try:
            report = self._generate_analysis_report()
            chat_text = self.chat_history.toPlainText()
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)
                f.write("\n\n")
                f.write("=" * 60 + "\n")
                f.write("CHAT LOG\n")
                f.write("=" * 60 + "\n\n")
                f.write(chat_text)
            
            QMessageBox.information(self, "Export Complete", f"Full export saved to:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export:\n{str(e)}")
    
    def _generate_analysis_report(self):
        """Generate a text report from the current analysis."""
        lines = []
        lines.append("CR2A CONTRACT ANALYSIS REPORT")
        lines.append("=" * 60)
        lines.append("")
        
        # Check if this is a verified result
        is_verified = hasattr(self.current_analysis, 'verification_metadata')
        
        if is_verified:
            lines.extend(self._generate_verified_report(self.current_analysis))
        else:
            lines.extend(self._generate_standard_report(self.current_analysis))
        
        return "\n".join(lines)
    
    def _generate_standard_report(self, result):
        """Generate report for standard AnalysisResult."""
        lines = []
        
        # Metadata
        if result.metadata:
            lines.append("DOCUMENT INFORMATION")
            lines.append("-" * 40)
            lines.append(f"Filename: {result.metadata.filename}")
            lines.append(f"Pages: {result.metadata.page_count}")
            lines.append(f"File Size: {result.metadata.file_size_bytes / 1024:.1f} KB")
            lines.append(f"Analyzed: {result.metadata.analyzed_at.strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("")
        
        # Clauses
        if result.clauses:
            lines.append(f"CLAUSES ({len(result.clauses)} found)")
            lines.append("-" * 40)
            for clause in result.clauses:
                lines.append(f"[{clause.risk_level.upper()}] {clause.type}")
                lines.append(f"  Page {clause.page}: {clause.text}")
                lines.append("")
        
        # Risks
        if result.risks:
            lines.append(f"RISKS ({len(result.risks)} found)")
            lines.append("-" * 40)
            for risk in result.risks:
                lines.append(f"[{risk.severity.upper()}] {risk.description}")
                lines.append(f"  Recommendation: {risk.recommendation}")
                lines.append("")
        
        # Compliance Issues
        if result.compliance_issues:
            lines.append(f"COMPLIANCE ISSUES ({len(result.compliance_issues)} found)")
            lines.append("-" * 40)
            for issue in result.compliance_issues:
                lines.append(f"[{issue.severity.upper()}] {issue.regulation}")
                lines.append(f"  {issue.issue}")
                lines.append("")
        
        return lines
    
    def _generate_verified_report(self, result):
        """Generate report for VerifiedAnalysisResult."""
        lines = []
        
        # Verification Summary
        meta = result.verification_metadata
        lines.append("VERIFICATION SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Analysis Passes: {meta.num_passes}")
        lines.append(f"Findings Before Verification: {meta.total_findings_before_verification}")
        lines.append(f"Findings After Verification: {meta.total_findings_after_verification}")
        lines.append(f"Hallucinations Detected: {meta.hallucinations_detected}")
        lines.append(f"Conflicts Found: {meta.conflicts_found}")
        lines.append(f"Conflicts Resolved: {meta.conflicts_resolved}")
        lines.append(f"Average Confidence: {meta.average_confidence_score:.1%}")
        lines.append(f"Duration: {meta.verification_duration_seconds:.1f}s")
        lines.append(f"Chunks Processed: {meta.chunks_processed}")
        lines.append("")
        
        # Coverage Report
        if result.coverage_report:
            cov = result.coverage_report
            lines.append("COVERAGE REPORT")
            lines.append("-" * 40)
            lines.append(f"Coverage: {cov.coverage_percentage:.1%}")
            if cov.is_below_threshold:
                lines.append(f"WARNING: Below threshold of {cov.threshold:.1%}")
            if cov.clause_types_found:
                lines.append(f"Found: {', '.join(cov.clause_types_found)}")
            if cov.clause_types_not_found:
                lines.append(f"Not Found: {', '.join(cov.clause_types_not_found)}")
            if cov.clause_types_uncertain:
                lines.append(f"Uncertain: {', '.join(cov.clause_types_uncertain)}")
            lines.append("")
        
        # Verified Clauses
        if result.verified_clauses:
            lines.append(f"VERIFIED CLAUSES ({len(result.verified_clauses)} found)")
            lines.append("-" * 40)
            for finding in result.verified_clauses:
                status = "PRESENT" if finding.presence_status.name == "PRESENT" else finding.presence_status.name
                clause_type = finding.finding_data.get('type', 'Unknown')
                clause_text = finding.finding_data.get('text', '')
                
                lines.append(f"[{finding.confidence_score:.0%}] [{status}] {clause_type}")
                lines.append(f"  {clause_text}")
                if finding.is_hallucinated:
                    lines.append("  ⚠️ POTENTIAL HALLUCINATION")
                lines.append("")
        
        # Verified Risks
        if result.verified_risks:
            lines.append(f"VERIFIED RISKS ({len(result.verified_risks)} found)")
            lines.append("-" * 40)
            for finding in result.verified_risks:
                description = finding.finding_data.get('description', 'Unknown')
                severity = finding.finding_data.get('severity', 'unknown')
                
                lines.append(f"[{finding.confidence_score:.0%}] [{severity.upper()}] {description}")
                lines.append("")
        
        # Conflicts
        if result.conflicts:
            lines.append(f"CONFLICTS ({len(result.conflicts)} found)")
            lines.append("-" * 40)
            for conflict in result.conflicts:
                status = "RESOLVED" if conflict.is_resolved else "UNRESOLVED"
                lines.append(f"[{status}] {conflict.explanation}")
                if conflict.is_resolved:
                    lines.append(f"  Resolution: {conflict.resolution_method}")
                lines.append("")
        
        return lines

    def init_engines(self):
        """Initialize analysis and query engines."""
        # Try to get API key from config manager first, then environment variable
        api_key = None
        if self.config_manager:
            api_key = self.config_manager.get_openai_key()
        
        if not api_key:
            api_key = os.environ.get('OPENAI_API_KEY')
        
        if not api_key:
            # Show settings dialog to configure API key
            reply = QMessageBox.question(
                self,
                "API Key Required",
                "OpenAI API key is not configured.\n\n"
                "Would you like to configure it now?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.open_settings()
            return
        
        try:
            self.analysis_engine = AnalysisEngine(openai_api_key=api_key)
            openai_client = OpenAIClient(api_key=api_key)
            self.query_engine = QueryEngine(openai_client)
            self.statusBar().showMessage("Engines initialized successfully")
        except Exception as e:
            error_msg = str(e)
            # Check if it's an API key error
            if "401" in error_msg or "Incorrect API key" in error_msg or "invalid_api_key" in error_msg:
                QMessageBox.critical(
                    self,
                    "Invalid API Key",
                    f"The API key appears to be invalid:\n\n{error_msg}\n\n"
                    "Please check your API key in File → Settings.\n\n"
                    "You can obtain a valid API key from:\n"
                    "https://platform.openai.com/api-keys"
                )
            else:
                QMessageBox.critical(
                    self,
                    "Initialization Error",
                    f"Failed to initialize engines:\n{str(e)}"
                )
    
    def browse_file(self):
        """Open file browser."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Contract File",
            "",
            "All Supported (*.pdf *.docx *.txt);;PDF Files (*.pdf);;Word Files (*.docx);;Text Files (*.txt)"
        )
        
        if filename:
            self.current_file = filename
            self.file_label.setText(os.path.basename(filename))
            self.analyze_btn.setEnabled(True)
            self.upload_status.setText(f"✓ File selected: {os.path.basename(filename)}")
    
    def analyze_contract(self):
        """Start contract analysis."""
        if not self.analysis_engine:
            QMessageBox.warning(self, "Error", "Analysis engine not initialized. Check API key.")
            return
        
        if not self.current_file:
            QMessageBox.warning(self, "Error", "No file selected")
            return
        
        # Get exhaustive mode settings
        exhaustive = self.exhaustive_checkbox.isChecked()
        num_passes = self.passes_spinbox.value()
        
        # Disable button and show progress
        self.analyze_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        if exhaustive:
            self.upload_status.setText(f"🔄 Running exhaustive analysis ({num_passes} passes)... This may take several minutes...")
        else:
            self.upload_status.setText("🔄 Analyzing contract... This may take 30-60 seconds...")
        self.statusBar().showMessage("Analyzing contract...")
        
        # Extract and store contract text for later verification
        try:
            self.contract_text = self.analysis_engine.uploader.extract_text(self.current_file)
        except Exception as e:
            self.contract_text = None
        
        # Start analysis in background thread
        self.analysis_thread = AnalysisThread(
            self.analysis_engine, 
            self.current_file,
            exhaustive=exhaustive,
            num_passes=num_passes
        )
        self.analysis_thread.finished.connect(self.on_analysis_complete)
        self.analysis_thread.error.connect(self.on_analysis_error)
        self.analysis_thread.progress.connect(self.on_analysis_progress)
        self.analysis_thread.start()
    
    def on_analysis_progress(self, status, percent):
        """Handle analysis progress update."""
        self.progress_bar.setValue(percent)
        self.upload_status.setText(f"🔄 {status}")
    
    def on_analysis_complete(self, result):
        """Handle analysis completion."""
        self.current_analysis = result
        
        # Clear the history record ID since this is a new analysis (not from history)
        self.current_history_record_id = None
        
        # Hide progress
        self.progress_bar.setVisible(False)
        self.analyze_btn.setEnabled(True)
        self.upload_status.setText("✓ Analysis complete! View results in the Analysis tab.")
        self.statusBar().showMessage("Analysis complete")
        
        # Auto-save to history store
        self._auto_save_analysis(result)
        
        # Display results
        self.display_analysis(result)
        
        # Switch to analysis tab
        self.tabs.setCurrentIndex(1)
        
        QMessageBox.information(self, "Success", "Contract analysis complete!\n\nView results in the Analysis tab or ask questions in the Chat tab.")
    
    def _auto_save_analysis(self, result):
        """
        Auto-save analysis result to history store and differential storage.
        
        This method saves the analysis to both the history store (for backward compatibility)
        and the differential storage (for versioning). It also handles duplicate detection
        and version updates.
        
        Args:
            result: The AnalysisResult to save
        """
        # Save to differential storage if available (versioning)
        if self.differential_storage and self.contract_identity_detector:
            try:
                self._save_to_differential_storage(result)
            except Exception as e:
                logger.error("Failed to save to differential storage: %s", e, exc_info=True)
                # Continue to save to history_store even if versioning fails
        
        # Save to history store (backward compatibility)
        if self.history_store is None:
            logger.info("History store not available, skipping history save")
            return
        
        if self.history_tab is None:
            logger.info("History tab not available, skipping history save")
            return
        
        try:
            # Save to history store
            record_id = self.history_store.save(result)
            logger.info("Auto-saved analysis with ID: %s", record_id)
            
            # Refresh history tab to show updated list from differential storage
            if self.differential_storage:
                self.history_tab.refresh()
                logger.info("Refreshed history tab with versioned data")
            else:
                # Fallback to old method if versioning not available
                summary = self.history_store.get_summary(record_id)
                if summary:
                    self.history_tab.add_record(summary)
                    logger.info("Added record to History tab: %s", record_id)
                else:
                    logger.warning("Failed to get summary for record: %s", record_id)
            
        except Exception as e:
            logger.error("Failed to auto-save analysis: %s", e)
            QMessageBox.warning(
                self,
                "Auto-Save Warning",
                f"Analysis completed successfully, but failed to save to history:\n\n{str(e)}\n\n"
                "You can still view and use the analysis results.\n"
                "The analysis will not be available in the History tab."
            )
    
    def _save_to_differential_storage(self, result):
        """
        Save analysis result to differential storage with versioning.
        
        Handles duplicate detection and version updates.
        
        Args:
            result: The AnalysisResult to save
        """
        import uuid
        from datetime import datetime
        from pathlib import Path
        from src.differential_storage import Contract, Clause, VersionMetadata
        from src.analysis_models import ComprehensiveAnalysisResult
        
        logger.info("Saving to differential storage...")
        
        # Convert result to ComprehensiveAnalysisResult if needed
        if isinstance(result, dict):
            analysis_result = ComprehensiveAnalysisResult.from_dict(result)
        else:
            analysis_result = result
        
        # Check for duplicate contracts
        file_hash = self.contract_identity_detector.compute_file_hash(self.current_file)
        filename = Path(self.current_file).name
        matches = self.contract_identity_detector.find_potential_matches(file_hash, filename)
        
        if matches:
            # Found potential duplicate
            match = matches[0]
            logger.info("Found potential duplicate: %s (version %d)", match.contract_id, match.current_version)
            
            # Ask user if this is an update
            if match.match_type == 'hash':
                message = (
                    f"This file appears to be identical to a previously analyzed contract:\n\n"
                    f"Contract: {match.filename}\n"
                    f"Current Version: {match.current_version}\n\n"
                    f"Is this an updated version of the same contract?"
                )
            else:
                message = (
                    f"This file has a similar name to a previously analyzed contract:\n\n"
                    f"Contract: {match.filename}\n"
                    f"Similarity: {match.similarity_score:.0%}\n"
                    f"Current Version: {match.current_version}\n\n"
                    f"Is this an updated version of the same contract?"
                )
            
            reply = QMessageBox.question(
                self,
                "Duplicate Contract Detected",
                message,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # User confirmed it's an update - store as new version
                self._store_contract_version(match.contract_id, match.current_version, analysis_result)
                return
        
        # No duplicate or user said it's different - store as new contract
        self._store_new_contract(analysis_result, file_hash, filename)
    
    def _store_new_contract(self, analysis_result, file_hash, filename):
        """Store a new contract with version 1."""
        import uuid
        from datetime import datetime
        from src.differential_storage import Contract, Clause
        
        contract_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        contract = Contract(
            contract_id=contract_id,
            filename=filename,
            file_hash=file_hash,
            current_version=1,
            created_at=timestamp,
            updated_at=timestamp
        )
        
        # Extract clauses from analysis
        clauses = self._extract_clauses_from_analysis(analysis_result, contract_id, 1, timestamp)
        
        # Store
        self.differential_storage.store_new_contract(contract, clauses)
        logger.info("Stored new contract: %s (version 1)", contract_id)
    
    def _store_contract_version(self, contract_id, current_version, new_analysis):
        """Store a new version of an existing contract."""
        from src.differential_storage import Clause, VersionMetadata
        from datetime import datetime
        
        # Reconstruct old version
        old_analysis_dict = self.version_manager.reconstruct_version(contract_id, current_version)
        
        try:
            from src.analysis_models import ComprehensiveAnalysisResult
            old_analysis = ComprehensiveAnalysisResult.from_dict(old_analysis_dict)
        except Exception as e:
            logger.error("Failed to reconstruct previous version: %s", e)
            QMessageBox.warning(
                self,
                "Version Update Warning",
                "Could not compare with previous version. Storing as new contract instead."
            )
            # Fall back to storing as new
            file_hash = self.contract_identity_detector.compute_file_hash(self.current_file)
            from pathlib import Path
            filename = Path(self.current_file).name
            self._store_new_contract(new_analysis, file_hash, filename)
            return
        
        # Compare versions
        contract_diff = self.change_comparator.compare_contracts(old_analysis, new_analysis)
        
        # Get next version
        new_version = self.version_manager.get_next_version(contract_id)
        
        # Assign clause versions
        versioned_contract = self.version_manager.assign_clause_versions(
            contract_diff, contract_id, new_version
        )
        
        # Store new version
        self.differential_storage.store_contract_version(
            contract_id, new_version,
            versioned_contract.clauses,
            versioned_contract.version_metadata
        )
        logger.info("Stored contract version %d: %s", new_version, contract_id)
    
    def _extract_clauses_from_analysis(self, analysis, contract_id, version, timestamp):
        """Extract clauses from analysis result for storage."""
        import uuid
        from src.differential_storage import Clause
        
        clauses = []
        
        # Extract contract overview as a special clause
        if hasattr(analysis, 'contract_overview') and analysis.contract_overview:
            overview_dict = analysis.contract_overview.to_dict() if hasattr(analysis.contract_overview, 'to_dict') else analysis.contract_overview
            clause = Clause(
                clause_id=str(uuid.uuid4()),
                contract_id=contract_id,
                clause_version=version,
                clause_identifier="contract_overview",
                content=str(overview_dict),
                metadata=overview_dict,
                created_at=timestamp,
                is_deleted=False,
                deleted_at=None
            )
            clauses.append(clause)
        
        # Extract clauses from each section
        sections = [
            'administrative_and_commercial_terms',
            'technical_and_performance_terms',
            'legal_risk_and_enforcement',
            'regulatory_and_compliance_terms',
            'data_technology_and_deliverables'
        ]
        
        for section_name in sections:
            if hasattr(analysis, section_name):
                section = getattr(analysis, section_name)
                if section:
                    section_dict = section.to_dict() if hasattr(section, 'to_dict') else section
                    if isinstance(section_dict, dict):
                        for category_name, clause_data in section_dict.items():
                            if clause_data:
                                clause_dict = clause_data.to_dict() if hasattr(clause_data, 'to_dict') else clause_data
                                clause = Clause(
                                    clause_id=str(uuid.uuid4()),
                                    contract_id=contract_id,
                                    clause_version=version,
                                    clause_identifier=f"{section_name}.{category_name}",
                                    content=str(clause_dict.get('Clause Language', clause_dict.get('clause_language', ''))),
                                    metadata=clause_dict,
                                    created_at=timestamp,
                                    is_deleted=False,
                                    deleted_at=None
                                )
                                clauses.append(clause)
        
        return clauses
    
    def on_analysis_error(self, error):
        """Handle analysis error."""
        self.progress_bar.setVisible(False)
        self.analyze_btn.setEnabled(True)
        self.upload_status.setText(f"❌ Analysis failed: {error}")
        self.statusBar().showMessage("Analysis failed")
        
        QMessageBox.critical(self, "Analysis Error", f"Analysis failed:\n\n{error}")
    
    def display_analysis(self, result):
        """Display analysis results using structured view."""
        # Hide the "no analysis" message
        if hasattr(self, 'no_analysis_label'):
            self.no_analysis_label.setVisible(False)
        
        # Log what we're receiving
        logger.info(f"display_analysis called with type: {type(result)}")
        logger.info(f"Result has to_dict: {hasattr(result, 'to_dict')}")
        
        # Try to get a dict representation for debugging
        try:
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
                logger.info(f"Result dict keys: {list(result_dict.keys())}")
            elif hasattr(result, '__dict__'):
                logger.info(f"Result __dict__ keys: {list(result.__dict__.keys())}")
        except Exception as e:
            logger.error(f"Error getting result keys: {e}")
        
        # Display in structured view
        self.structured_view.display_analysis(result)
        
        # Store current analysis for chat
        self.current_analysis = result
    
    def _display_standard_analysis(self, result):
        """Display standard (non-verified) analysis results."""
        # Metadata
        if result.metadata:
            metadata_text = (
                f"Filename: {result.metadata.filename}\n"
                f"Pages: {result.metadata.page_count}\n"
                f"File Size: {result.metadata.file_size_bytes / 1024:.1f} KB\n"
                f"Analyzed: {result.metadata.analyzed_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            group = self.create_group("📄 Document Information", metadata_text)
            self.analysis_layout.addWidget(group)
        
        # Clauses
        if result.clauses:
            clauses_text = ""
            for clause in result.clauses[:10]:  # Show first 10
                clauses_text += f"[{clause.risk_level.upper()}] {clause.type}\n"
                clauses_text += f"Page {clause.page}: {clause.text[:100]}...\n\n"
            group = self.create_group(f"📋 Clauses ({len(result.clauses)} found)", clauses_text.strip())
            self.analysis_layout.addWidget(group)
        
        # Risks
        if result.risks:
            risks_text = ""
            for risk in result.risks[:5]:  # Show first 5
                risks_text += f"[{risk.severity.upper()}] {risk.description}\n"
                risks_text += f"Recommendation: {risk.recommendation}\n\n"
            group = self.create_group(f"⚠️ Identified Risks ({len(result.risks)} found)", risks_text.strip())
            self.analysis_layout.addWidget(group)
        
        # Compliance Issues
        if result.compliance_issues:
            compliance_text = ""
            for issue in result.compliance_issues:
                compliance_text += f"[{issue.severity.upper()}] {issue.regulation}\n"
                compliance_text += f"{issue.issue}\n\n"
            group = self.create_group(f"⚖️ Compliance Issues ({len(result.compliance_issues)} found)", compliance_text.strip())
            self.analysis_layout.addWidget(group)
        
        # Redlining Suggestions
        if result.redlining_suggestions:
            redlining_text = ""
            for suggestion in result.redlining_suggestions[:3]:  # Show first 3
                redlining_text += f"Clause: {suggestion.clause_id}\n"
                redlining_text += f"Rationale: {suggestion.rationale}\n\n"
            group = self.create_group(f"✏️ Redlining Suggestions ({len(result.redlining_suggestions)} found)", redlining_text.strip())
            self.analysis_layout.addWidget(group)
    
    def _display_verified_analysis(self, result):
        """Display verified analysis results with confidence scores."""
        # Verification Summary
        meta = result.verification_metadata
        summary_text = (
            f"✅ Exhaustive Analysis Complete\n\n"
            f"Analysis Passes: {meta.num_passes}\n"
            f"Findings Before Verification: {meta.total_findings_before_verification}\n"
            f"Findings After Verification: {meta.total_findings_after_verification}\n"
            f"Hallucinations Detected: {meta.hallucinations_detected}\n"
            f"Conflicts Found: {meta.conflicts_found}\n"
            f"Conflicts Resolved: {meta.conflicts_resolved}\n"
            f"Average Confidence: {meta.average_confidence_score:.1%}\n"
            f"Duration: {meta.verification_duration_seconds:.1f}s\n"
            f"Chunks Processed: {meta.chunks_processed}"
        )
        group = self.create_group("🔍 Verification Summary", summary_text)
        group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; padding: 10px; background: #e8f5e9; }")
        self.analysis_layout.addWidget(group)
        
        # Coverage Report
        if result.coverage_report:
            coverage = result.coverage_report
            coverage_text = f"Coverage: {coverage.coverage_percentage:.1%}\n\n"
            
            if coverage.clause_types_found:
                coverage_text += f"✅ Found ({len(coverage.clause_types_found)}):\n"
                coverage_text += ", ".join(coverage.clause_types_found[:10])
                if len(coverage.clause_types_found) > 10:
                    coverage_text += f"... (+{len(coverage.clause_types_found) - 10} more)"
                coverage_text += "\n\n"
            
            if coverage.clause_types_not_found:
                coverage_text += f"❌ Not Found ({len(coverage.clause_types_not_found)}):\n"
                coverage_text += ", ".join(coverage.clause_types_not_found[:10])
                coverage_text += "\n\n"
            
            if coverage.clause_types_uncertain:
                coverage_text += f"❓ Uncertain ({len(coverage.clause_types_uncertain)}):\n"
                coverage_text += ", ".join(coverage.clause_types_uncertain[:10])
            
            style = "QGroupBox { font-weight: bold; font-size: 14px; padding: 10px; "
            if coverage.is_below_threshold:
                style += "background: #fff3e0; }"  # Orange warning
            else:
                style += "background: #e3f2fd; }"  # Blue info
            
            group = self.create_group("📊 Coverage Report", coverage_text.strip())
            group.setStyleSheet(style)
            self.analysis_layout.addWidget(group)
        
        # Verified Clauses
        if result.verified_clauses:
            clauses_text = ""
            for finding in result.verified_clauses[:10]:
                status_icon = self._get_presence_icon(finding.presence_status)
                confidence_bar = self._get_confidence_bar(finding.confidence_score)
                
                finding_data = finding.finding_data
                clause_type = finding_data.get('type', 'Unknown')
                clause_text = finding_data.get('text', '')[:100]
                
                clauses_text += f"{status_icon} [{finding.confidence_score:.0%}] {clause_type}\n"
                clauses_text += f"   {confidence_bar}\n"
                clauses_text += f"   {clause_text}...\n"
                if finding.is_hallucinated:
                    clauses_text += "   ⚠️ POTENTIAL HALLUCINATION\n"
                clauses_text += "\n"
            
            group = self.create_group(f"📋 Verified Clauses ({len(result.verified_clauses)} found)", clauses_text.strip())
            self.analysis_layout.addWidget(group)
        
        # Verified Risks
        if result.verified_risks:
            risks_text = ""
            for finding in result.verified_risks[:5]:
                status_icon = self._get_presence_icon(finding.presence_status)
                
                finding_data = finding.finding_data
                description = finding_data.get('description', 'Unknown risk')
                severity = finding_data.get('severity', 'unknown')
                
                risks_text += f"{status_icon} [{finding.confidence_score:.0%}] [{severity.upper()}]\n"
                risks_text += f"   {description}\n\n"
            
            group = self.create_group(f"⚠️ Verified Risks ({len(result.verified_risks)} found)", risks_text.strip())
            self.analysis_layout.addWidget(group)
        
        # Conflicts
        if result.conflicts:
            conflicts_text = ""
            for conflict in result.conflicts[:5]:
                if conflict.is_resolved:
                    conflicts_text += f"✅ RESOLVED: {conflict.resolution_method}\n"
                else:
                    conflicts_text += f"❓ UNRESOLVED\n"
                conflicts_text += f"   {conflict.explanation}\n\n"
            
            group = self.create_group(f"⚔️ Conflicts ({len(result.conflicts)} found)", conflicts_text.strip())
            self.analysis_layout.addWidget(group)
    
    def _get_presence_icon(self, status):
        """Get icon for presence status."""
        if status == PresenceStatus.PRESENT:
            return "✅"
        elif status == PresenceStatus.ABSENT:
            return "❌"
        else:
            return "❓"
    
    def _get_confidence_bar(self, confidence):
        """Get visual confidence bar."""
        filled = int(confidence * 10)
        empty = 10 - filled
        return "█" * filled + "░" * empty
    
    def create_group(self, title, content):
        """Create a group box for displaying data."""
        group = QGroupBox(title)
        group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; padding: 10px; }")
        layout = QVBoxLayout()
        
        if isinstance(content, dict):
            text = "\n".join(f"{k}: {v}" for k, v in content.items())
        else:
            text = str(content)
        
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("padding: 10px; background: #f9f9f9; border: 1px solid #ddd;")
        layout.addWidget(label)
        
        group.setLayout(layout)
        return group
    
    def send_question(self):
        """Send a question to the query engine."""
        question = self.question_input.text().strip()
        if not question:
            return
        
        if not self.current_analysis:
            QMessageBox.warning(self, "No Analysis", "Please analyze a contract first.")
            return
        
        if not self.query_engine:
            QMessageBox.warning(self, "Error", "Query engine not initialized.")
            return
        
        # Display question
        self.chat_history.append(f"<br><b>❓ You:</b> {question}<br>")
        self.question_input.clear()
        self.send_btn.setEnabled(False)
        self.statusBar().showMessage("Processing query...")
        
        # Convert analysis to dict - handle both standard and verified results
        if hasattr(self.current_analysis, 'verified_clauses'):
            # VerifiedAnalysisResult - build context from verified findings
            # This includes all verified clauses, not just the base_result
            analysis_dict = self._build_verified_context(self.current_analysis)
            print(f"DEBUG: Built verified context with {len(analysis_dict.get('clauses', []))} clauses")
        elif hasattr(self.current_analysis, 'base_result'):
            # Fallback to base_result
            analysis_dict = self.current_analysis.base_result
            print(f"DEBUG: Using base_result with {len(analysis_dict.get('clauses', []))} clauses")
        else:
            # Standard AnalysisResult
            analysis_dict = self.current_analysis.to_dict()
            print(f"DEBUG: Using standard result with {len(analysis_dict.get('clauses', []))} clauses")
        
        # Start query in background thread
        self.query_thread = QueryThread(self.query_engine, question, analysis_dict)
        self.query_thread.finished.connect(self.on_query_complete)
        self.query_thread.error.connect(self.on_query_error)
        self.query_thread.start()
    
    def _build_verified_context(self, result):
        """Build context dictionary from VerifiedAnalysisResult."""
        # Extract clause data from verified findings
        clauses = []
        for i, finding in enumerate(result.verified_clauses):
            clause_data = finding.finding_data.copy()
            clause_data['confidence'] = finding.confidence_score
            clause_data['presence_status'] = str(finding.presence_status)
            # Ensure clause has an ID for risk matching
            if 'id' not in clause_data:
                clause_data['id'] = f"clause_{i+1}"
            clauses.append(clause_data)
        
        # Extract risk data from verified findings
        risks = []
        for i, finding in enumerate(result.verified_risks):
            risk_data = finding.finding_data.copy()
            risk_data['confidence'] = finding.confidence_score
            # Ensure risk has an ID
            if 'id' not in risk_data:
                risk_data['id'] = f"risk_{i+1}"
            risks.append(risk_data)
        
        # Extract compliance data
        compliance_issues = []
        for finding in result.verified_compliance_issues:
            compliance_issues.append(finding.finding_data)
        
        # Extract redlining data
        redlining = []
        for finding in result.verified_redlining_suggestions:
            redlining.append(finding.finding_data)
        
        # Get metadata from base_result if available
        metadata = result.base_result.get('contract_metadata', {})
        
        print(f"DEBUG _build_verified_context: {len(clauses)} clauses, {len(risks)} risks")
        if clauses:
            print(f"DEBUG First clause: {clauses[0]}")
        
        return {
            'contract_metadata': metadata,
            'clauses': clauses,
            'risks': risks,
            'compliance_issues': compliance_issues,
            'redlining_suggestions': redlining
        }
    
    def on_query_complete(self, answer):
        """Handle query completion."""
        self.chat_history.append(f"<b>💡 Answer:</b><br>{answer}<br>")
        self.send_btn.setEnabled(True)
        self.statusBar().showMessage("Ready")
    
    def on_query_error(self, error):
        """Handle query error."""
        self.chat_history.append(f"<b>❌ Error:</b> {error}<br>")
        self.send_btn.setEnabled(True)
        self.statusBar().showMessage("Query failed")


class SettingsDialog(QDialog):
    """Settings dialog for API key configuration."""
    
    def __init__(self, parent, config_manager):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the dialog UI."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Instructions
        instructions = QLabel(
            "Configure your OpenAI API key below.\n\n"
            "You can obtain an API key from:\n"
            "https://platform.openai.com/api-keys"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("padding: 10px; background: #f0f0f0; border-radius: 5px;")
        layout.addWidget(instructions)
        
        # Form layout
        form_layout = QFormLayout()
        layout.addLayout(form_layout)
        
        # API Key input
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("sk-...")
        
        # Load current API key if available
        if self.config_manager:
            current_key = self.config_manager.get_openai_key()
            if current_key:
                self.api_key_input.setText(current_key)
        
        form_layout.addRow("OpenAI API Key:", self.api_key_input)
        
        # Show/Hide password button
        show_hide_layout = QHBoxLayout()
        self.show_key_btn = QPushButton("Show")
        self.show_key_btn.setMaximumWidth(80)
        self.show_key_btn.clicked.connect(self.toggle_key_visibility)
        show_hide_layout.addWidget(self.show_key_btn)
        show_hide_layout.addStretch()
        form_layout.addRow("", show_hide_layout)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def toggle_key_visibility(self):
        """Toggle API key visibility."""
        if self.api_key_input.echoMode() == QLineEdit.Password:
            self.api_key_input.setEchoMode(QLineEdit.Normal)
            self.show_key_btn.setText("Hide")
        else:
            self.api_key_input.setEchoMode(QLineEdit.Password)
            self.show_key_btn.setText("Show")
    
    def save_settings(self):
        """Save settings to config file."""
        api_key = self.api_key_input.text().strip()
        
        if not api_key:
            QMessageBox.warning(self, "Invalid Input", "Please enter an API key.")
            return
        
        if not api_key.startswith("sk-"):
            reply = QMessageBox.question(
                self,
                "Confirm API Key",
                "The API key doesn't start with 'sk-'. Are you sure this is correct?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        try:
            if self.config_manager:
                self.config_manager.set_openai_key(api_key)
                self.config_manager.save_config()
            self.accept()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save settings:\n{str(e)}"
            )


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look
    
    window = CR2A_GUI()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

