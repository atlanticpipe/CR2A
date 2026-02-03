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

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from analysis_engine import AnalysisEngine
from query_engine import QueryEngine
from openai_fallback_client import OpenAIClient
from config_manager import ConfigManager
from exhaustiveness_models import VerifiedAnalysisResult, PresenceStatus


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
        
        self.init_ui()
        self.init_config()
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
        """Create the analysis results tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Scroll area for results
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
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
        
        # Hide progress
        self.progress_bar.setVisible(False)
        self.analyze_btn.setEnabled(True)
        self.upload_status.setText("✓ Analysis complete! View results in the Analysis tab.")
        self.statusBar().showMessage("Analysis complete")
        
        # Display results
        self.display_analysis(result)
        
        # Switch to analysis tab
        self.tabs.setCurrentIndex(1)
        
        QMessageBox.information(self, "Success", "Contract analysis complete!\n\nView results in the Analysis tab or ask questions in the Chat tab.")
    
    def on_analysis_error(self, error):
        """Handle analysis error."""
        self.progress_bar.setVisible(False)
        self.analyze_btn.setEnabled(True)
        self.upload_status.setText(f"❌ Analysis failed: {error}")
        self.statusBar().showMessage("Analysis failed")
        
        QMessageBox.critical(self, "Analysis Error", f"Analysis failed:\n\n{error}")
    
    def display_analysis(self, result):
        """Display analysis results."""
        # Clear existing content
        while self.analysis_layout.count():
            child = self.analysis_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Check if this is a verified result by checking for verification_metadata attribute
        # This is more robust than isinstance which can fail with import issues
        is_verified = hasattr(result, 'verification_metadata') and result.verification_metadata is not None
        
        if is_verified:
            self._display_verified_analysis(result)
        else:
            self._display_standard_analysis(result)
        
        self.analysis_layout.addStretch()
    
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

