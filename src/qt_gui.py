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
    QCheckBox, QSpinBox, QRadioButton, QComboBox, QButtonGroup,
    QSplitter
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
from src.analysis_engine import AnalysisEngine, PreparedContract
from src.query_engine import QueryEngine
from src.local_model_client import LocalModelClient
from src.config_manager import ConfigManager
from src.history_store import HistoryStore, HistoryStoreError
from src.history_tab import HistoryTab
from src.specs_tab import SpecsTab
from src.bid_review_tab import BidReviewTab
from src.structured_analysis_view import StructuredAnalysisView


class AnalysisThread(QThread):
    """Background thread for contract analysis."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(str, int)

    def __init__(self, engine, filepath):
        super().__init__()
        self.engine = engine
        self.filepath = filepath

    def run(self):
        try:
            def progress_callback(status, percent):
                self.progress.emit(status, percent)

            result = self.engine.analyze_contract(
                self.filepath,
                progress_callback=progress_callback
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class BatchAnalysisThread(QThread):
    """Background thread for batch folder analysis."""
    progress = pyqtSignal(str, int, int, int)  # message, current, total, percent
    file_complete = pyqtSignal(str, object)     # filename, result (or None on error)
    finished = pyqtSignal(list)                 # list of results
    error = pyqtSignal(str, str)                # filename, error_message

    def __init__(self, engine, files):
        super().__init__()
        self.engine = engine
        self.files = files
        self.cancelled = False

    def cancel(self):
        """Cancel batch processing."""
        self.cancelled = True

    def run(self):
        results = []

        for idx, file_path in enumerate(self.files):
            if self.cancelled:
                break

            current = idx + 1
            total = len(self.files)
            filename = file_path.name

            # Update progress
            self.progress.emit(
                f"Analyzing {filename}...",
                current,
                total,
                int((current / total) * 100)
            )

            try:
                # Analyze file
                result = self.engine.analyze_contract(
                    str(file_path),
                    progress_callback=None  # No sub-progress for batch
                )

                results.append({
                    'file': filename,
                    'result': result,
                    'status': 'success'
                })

                self.file_complete.emit(filename, result)

            except Exception as e:
                error_msg = str(e)
                results.append({
                    'file': filename,
                    'result': None,
                    'status': 'error',
                    'error': error_msg
                })

                self.error.emit(filename, error_msg)

                # Continue with next file (don't abort entire batch)
                logger.error(f"Failed to analyze {filename}: {error_msg}")

        # Emit final results
        self.finished.emit(results)


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


class PrepareContractThread(QThread):
    """Background thread for contract preparation (text extraction + regex, no AI)."""
    finished = pyqtSignal(object)  # PreparedContract
    error = pyqtSignal(str)
    progress = pyqtSignal(str, int)

    def __init__(self, engine, filepath):
        super().__init__()
        self.engine = engine
        self.filepath = filepath

    def run(self):
        try:
            def progress_callback(status, percent):
                self.progress.emit(status, percent)

            result = self.engine.prepare_contract(
                self.filepath,
                progress_callback=progress_callback
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class PrepareFolderThread(QThread):
    """Background thread for loading multiple files as combined context (no AI)."""
    finished = pyqtSignal(object)  # PreparedContract (combined)
    progress = pyqtSignal(str, int)
    error = pyqtSignal(str)

    def __init__(self, engine, files):
        super().__init__()
        self.engine = engine
        self.files = files

    def run(self):
        try:
            from analyzer.template_patterns import (
                extract_all_template_clauses, parse_contract_sections, detect_exclude_zones
            )
            from src.document_retriever import DocumentRetriever

            combined_text_parts = []
            combined_file_info = {
                'filename': f"{len(self.files)} files",
                'file_count': len(self.files),
                'files': [],
            }

            total = len(self.files)
            for idx, file_path in enumerate(self.files):
                filename = file_path.name
                pct = int(((idx) / total) * 60)  # 0-60% for extraction
                self.progress.emit(f"Extracting text from {filename}...", pct)

                try:
                    text = self.engine.uploader.extract_text(str(file_path))
                    if text and text.strip():
                        # Add file separator so AI knows which file content came from
                        combined_text_parts.append(
                            f"\n{'='*60}\n"
                            f"FILE: {filename}\n"
                            f"{'='*60}\n\n"
                            f"{text}"
                        )
                        file_info = self.engine.uploader.get_file_info(str(file_path))
                        combined_file_info['files'].append({
                            'filename': filename,
                            'path': str(file_path),
                            'size': file_info.get('file_size', 0),
                        })
                except Exception as e:
                    logger.warning(f"Failed to extract text from {filename}: {e}")

            if not combined_text_parts:
                self.error.emit("No text could be extracted from any file in the folder")
                return

            contract_text = "\n".join(combined_text_parts)
            logger.info(f"Combined {len(combined_text_parts)} files, {len(contract_text)} total characters")

            self.progress.emit("Parsing contract structure...", 65)
            exclude_zones = detect_exclude_zones(contract_text)
            section_index = parse_contract_sections(contract_text, exclude_zones=exclude_zones)

            self.progress.emit("Running pattern matching...", 75)
            extracted_clauses = extract_all_template_clauses(contract_text, section_index=section_index)
            regex_count = sum(len(v) for v in extracted_clauses.values())
            logger.info(f"Regex found {regex_count} clauses across {len(extracted_clauses)} categories")

            self.progress.emit("Building search index...", 90)
            retriever = DocumentRetriever()
            indexed = retriever.index_contract(contract_text, section_index, extracted_clauses)

            self.progress.emit("All files loaded!", 100)

            prepared = PreparedContract(
                file_path=str(self.files[0]),  # Primary file for storage
                contract_text=contract_text,
                file_info=combined_file_info,
                section_index=section_index,
                exclude_zones=exclude_zones,
                extracted_clauses=extracted_clauses,
                indexed=indexed,
            )
            self.finished.emit(prepared)

        except Exception as e:
            self.error.emit(str(e))


class SingleCategoryThread(QThread):
    """Background thread for analyzing a single clause category."""
    finished = pyqtSignal(str, str, object, str, str)  # cat_key, display_name, clause_block, prompt, response
    not_found = pyqtSignal(str, str, str)  # cat_key, prompt, response
    error = pyqtSignal(str, str)  # cat_key, error_msg
    progress = pyqtSignal(str, int)

    def __init__(self, engine, prepared, cat_key):
        super().__init__()
        self.engine = engine
        self.prepared = prepared
        self.cat_key = cat_key

    def run(self):
        try:
            def progress_callback(status, percent):
                self.progress.emit(status, percent)

            result = self.engine.analyze_single_category(
                self.prepared,
                self.cat_key,
                progress_callback=progress_callback
            )
            if result:
                section_key, display_name, clause_block, prompt, response = result
                if clause_block is not None:
                    self.finished.emit(self.cat_key, display_name, clause_block, prompt, response)
                else:
                    self.not_found.emit(self.cat_key, prompt or '', response or '')
            else:
                self.not_found.emit(self.cat_key, '', '')
        except Exception as e:
            self.error.emit(self.cat_key, str(e))


class AnalyzeAllThread(QThread):
    """Background thread for analyzing all categories sequentially."""
    category_complete = pyqtSignal(str, str, object, str, str)  # cat_key, display_name, clause_block, prompt, response
    category_not_found = pyqtSignal(str, str, str)  # cat_key, prompt, response
    category_error = pyqtSignal(str, str)  # cat_key, error_msg
    all_finished = pyqtSignal()
    progress = pyqtSignal(str, int)

    def __init__(self, engine, prepared):
        super().__init__()
        self.engine = engine
        self.prepared = prepared
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    def run(self):
        # Analyze ALL categories — tri-layer retrieval (keyword + TF-IDF)
        # can find relevant sections even without regex pattern matches
        categories = list(self.engine.CATEGORY_MAP.items())
        total = len(categories)

        self.progress.emit(
            f"Analyzing {total} categories...", 0
        )

        for i, (cat_key, (section_key, display_name)) in enumerate(categories):
            if self.cancelled:
                break

            pct = int(100 * i / total) if total else 100
            self.progress.emit(f"Analyzing {display_name} ({i + 1}/{total})...", pct)

            try:
                result = self.engine.analyze_single_category(
                    self.prepared, cat_key
                )
                if result:
                    _, disp, clause_block, prompt, response = result
                    if clause_block is not None:
                        self.category_complete.emit(cat_key, disp, clause_block, prompt, response)
                    else:
                        self.category_not_found.emit(cat_key, prompt or '', response or '')
                else:
                    self.category_not_found.emit(cat_key, '', '')
            except Exception as e:
                self.category_error.emit(cat_key, str(e))

        self.progress.emit("Analysis complete!", 100)
        self.all_finished.emit()


class CR2A_GUI(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.analysis_engine = None
        self.query_engine = None
        self.retriever = None
        self.current_analysis = None
        self.current_file = None
        self.config_manager = None
        self.contract_text = None  # Store extracted text for verification
        self.history_store = None  # History store for persistent analysis records
        self.current_history_record_id = None  # Track the record_id of currently loaded historical analysis

        # Folder upload support
        self.current_folder = None  # Folder path for batch processing
        self.folder_files = []  # List of files in folder
        self.upload_mode = "file"  # "file" or "folder"
        self.project_storage = None  # ProjectStorage instance for project-based storage
        self.chat_history_manager = None  # ChatHistoryManager for project chat history
        self.session_manager = None  # SessionManager for session persistence

        # Per-item on-demand analysis state
        self.prepared_contract = None  # PreparedContract after loading
        self.category_results = {}  # {cat_key: clause_block_dict} accumulated results
        self.active_category_thread = None  # Running SingleCategoryThread
        self.analyze_all_thread = None  # Running AnalyzeAllThread

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
                # If history tab already exists, update its storage and refresh
                if self.history_tab is not None:
                    self.history_tab.history_store = self.history_store
                    self.history_tab.differential_storage = self.differential_storage
                    if self.differential_storage:
                        from src.version_manager import VersionManager
                        self.history_tab.version_manager = VersionManager(self.differential_storage)
                    else:
                        self.history_tab.version_manager = None
                    self.history_tab.refresh()
                    logger.info("History tab updated with new storage (versioning: %s)",
                               "enabled" if self.differential_storage else "disabled")
                    return

                # Create History tab with optional differential_storage
                self.history_tab = HistoryTab(
                    self.history_store,
                    differential_storage=self.differential_storage
                )

                # Add tab after Contract tab
                self.tabs.addTab(self.history_tab, "History")

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
        displays it in the Contract tab, enables the Chat tab for querying,
        and switches to the Contract tab.
        
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
            
            # Display in Contract tab
            self.display_analysis(analysis_result)
            
            # Enable Chat tab for querying (it's already enabled by default, but ensure it's accessible)
            # The chat tab is always enabled, but we can update the chat history to indicate a new analysis is loaded
            self.chat_history.append(
                f"<br><b>Historical Analysis Loaded:</b> {analysis_result.metadata.filename}<br>"
                f"<i>You can now ask questions about this analysis.</i><br>"
            )
            
            # Switch to Contract tab (merged upload + analysis at index 0)
            self.tabs.setCurrentIndex(0)
            
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
                "<br><b>Notice:</b> The currently loaded analysis has been deleted from history.<br>"
                "<i>Please analyze a new contract or select another analysis from history.</i><br>"
            )
            
            # Update status bar
            self.statusBar().showMessage("Current analysis was deleted from history")
            
            logger.info("Cleared current analysis after deletion")
    
    def _clear_analysis_display(self):
        """Clear the analysis display."""
        # Clear existing content in backward-compat layout
        while self.analysis_layout.count():
            child = self.analysis_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Clear the structured view
        self.structured_view._clear_all_boxes()
        self.structured_view.enable_analyze_buttons(False)
    
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

        # --- Global file selection bar (always visible above tabs) ---
        file_bar = QHBoxLayout()
        file_bar.setSpacing(6)

        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("padding: 6px; border: 1px solid #ccc; background: #f5f5f5; font-size: 12px;")
        self.file_label.setMinimumWidth(200)
        file_bar.addWidget(self.file_label, stretch=1)

        browse_file_btn = QPushButton("Browse File...")
        browse_file_btn.clicked.connect(self.browse_file)
        browse_file_btn.setStyleSheet("padding: 6px 12px; font-size: 12px;")
        browse_file_btn.setToolTip("Select a single contract file")
        file_bar.addWidget(browse_file_btn)

        browse_folder_btn = QPushButton("Browse Folder...")
        browse_folder_btn.clicked.connect(self.browse_folder)
        browse_folder_btn.setStyleSheet("padding: 6px 12px; font-size: 12px;")
        browse_folder_btn.setToolTip("Select a folder for batch analysis")
        file_bar.addWidget(browse_folder_btn)

        self.load_btn = QPushButton("Load Contract")
        self.load_btn.clicked.connect(self.load_contract)
        self.load_btn.setEnabled(False)
        self.load_btn.setStyleSheet(
            "padding: 6px 16px; font-size: 13px; font-weight: bold; "
            "background: #4CAF50; color: white;"
        )
        self.load_btn.setToolTip("Extract text and run pattern matching (fast, no AI)")
        file_bar.addWidget(self.load_btn)

        # Load All button (only shown in folder mode)
        self.load_all_btn = QPushButton("Load All")
        self.load_all_btn.clicked.connect(self._load_folder)
        self.load_all_btn.setEnabled(False)
        self.load_all_btn.setVisible(False)
        self.load_all_btn.setStyleSheet(
            "padding: 6px 16px; font-size: 13px; font-weight: bold; "
            "background: #4CAF50; color: white;"
        )
        self.load_all_btn.setToolTip("Load all files as context for analysis")
        file_bar.addWidget(self.load_all_btn)

        layout.addLayout(file_bar)

        # Upload mode / status row
        status_row = QHBoxLayout()
        self.upload_mode_label = QLabel("")
        self.upload_mode_label.setStyleSheet("color: #666; font-size: 10px; font-style: italic; padding: 2px 5px;")
        status_row.addWidget(self.upload_mode_label)

        self.upload_status = QLabel("")
        self.upload_status.setWordWrap(True)
        self.upload_status.setStyleSheet("padding: 2px 5px; font-size: 11px; color: #555;")
        status_row.addWidget(self.upload_status, stretch=1)
        layout.addLayout(status_row)

        # Global progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(16)
        layout.addWidget(self.progress_bar)

        # Top-level splitter: tabs on left, chat on right
        self.main_splitter = QSplitter(Qt.Horizontal)

        # LEFT: Tab widget
        self.tabs = QTabWidget()
        self.main_splitter.addWidget(self.tabs)

        # Bid Review tab (default - first tab)
        self.bid_review_tab = BidReviewTab()
        self.bid_review_tab.analysis_requested.connect(self.on_bid_review_analysis_requested)
        self.bid_review_tab.item_analyzed.connect(self._on_bid_item_session_save)
        self.bid_review_tab.review_finished.connect(self._on_bid_review_session_save)
        self.tabs.addTab(self.bid_review_tab, "Bid Review")

        # Contract tab (analysis sidebar)
        self.contract_tab = self.create_contract_tab()
        self.tabs.addTab(self.contract_tab, "Contract")

        # Specs tab (technical specification extraction)
        self.specs_tab = SpecsTab()
        self.specs_tab.analysis_requested.connect(self.on_specs_analysis_requested)
        self.specs_tab.analysis_finished.connect(self._on_specs_finished)
        self.tabs.addTab(self.specs_tab, "Specs")

        # History tab (will be initialized after history_store is ready)
        self.history_tab = None

        # RIGHT: Chat panel (always visible)
        chat_panel = self._create_chat_panel()
        self.main_splitter.addWidget(chat_panel)

        self.main_splitter.setSizes([700, 500])
        self.main_splitter.setStretchFactor(0, 1)  # Tabs stretch
        self.main_splitter.setStretchFactor(1, 0)  # Chat stays fixed width

        layout.addWidget(self.main_splitter, stretch=1)

        # Welcome message in chat
        self._log_to_chat('system', 'Welcome to CR2A Contract Review & Analysis')
        self._log_to_chat('log', 'Browse and load a contract file above to begin analysis.')
        self._log_to_chat('log', 'Ask questions about the contract in the input box below.')

        # Status bar
        self.statusBar().showMessage("Ready")
    
    def _create_chat_panel(self):
        """Create the chat/log panel widget (always visible, independent of tabs)."""
        chat_panel = QWidget()
        chat_layout = QVBoxLayout()
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(4)
        chat_panel.setLayout(chat_layout)

        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("padding: 8px; font-size: 13px;")
        chat_layout.addWidget(self.chat_history)

        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        self.question_input = QLineEdit()
        self.question_input.setPlaceholderText("Ask a question about the contract...")
        self.question_input.setStyleSheet("padding: 8px; font-size: 13px;")
        self.question_input.returnPressed.connect(self.send_question)
        input_layout.addWidget(self.question_input)
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_question)
        self.send_btn.setStyleSheet("padding: 8px 16px; font-size: 13px;")
        input_layout.addWidget(self.send_btn)
        chat_layout.addLayout(input_layout)

        return chat_panel

    def create_contract_tab(self):
        """Create the Contract tab with analysis sidebar."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        widget.setLayout(layout)

        # Analyze All button for comprehensive contract analysis
        btn_bar = QHBoxLayout()
        self.analyze_all_btn = QPushButton("Analyze All")
        self.analyze_all_btn.clicked.connect(self.analyze_all)
        self.analyze_all_btn.setEnabled(False)
        self.analyze_all_btn.setStyleSheet(
            "padding: 6px 16px; font-size: 13px; font-weight: bold; "
            "background: #1976D2; color: white;"
        )
        self.analyze_all_btn.setToolTip("Run AI analysis on all clause categories")
        btn_bar.addWidget(self.analyze_all_btn)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        # Analysis sidebar (StructuredAnalysisView)
        self.structured_view = StructuredAnalysisView()
        self.structured_view.analyze_requested.connect(self.on_category_analyze_requested)
        self.structured_view.setMinimumWidth(280)
        layout.addWidget(self.structured_view, stretch=1)

        # Hidden backward-compat layout (for _clear_analysis_display)
        self.analysis_layout = QVBoxLayout()
        hidden_widget = QWidget()
        hidden_widget.setLayout(self.analysis_layout)
        hidden_widget.setVisible(False)
        layout.addWidget(hidden_widget)

        self.no_analysis_label = QLabel("")
        self.no_analysis_label.setVisible(False)
        self.analysis_layout.addWidget(self.no_analysis_label)

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
            "A PyQt5-based contract analysis tool powered by local AI (Llama 3.2).\n\n"
            "© 2024 CR2A Project"
        )
    
    def _has_any_results(self):
        """Check if any analysis results exist across all tabs."""
        if self.get_or_build_current_analysis():
            return True
        if self.bid_review_tab and self.bid_review_tab.item_results:
            return True
        if self.specs_tab and self.specs_tab.results_text.toPlainText().strip():
            return True
        return False

    def export_analysis_report(self):
        """Export analysis report to a text file."""
        if not self._has_any_results():
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
        if not self._has_any_results():
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
        """Generate a text report from the current analysis, including all tabs."""
        lines = []
        lines.append("CR2A CONTRACT ANALYSIS REPORT")
        lines.append("=" * 60)
        lines.append("")

        # Contract analysis (Sections I-VII)
        if self.current_analysis:
            is_comprehensive = hasattr(self.current_analysis, 'administrative_and_commercial_terms')
            if is_comprehensive:
                lines.extend(self._generate_comprehensive_report(self.current_analysis))
            else:
                lines.extend(self._generate_standard_report(self.current_analysis))

        # Bid Review results
        bid_lines = self._generate_bid_review_report()
        if bid_lines:
            lines.append("")
            lines.extend(bid_lines)

        # Specs tab results
        specs_lines = self._generate_specs_report()
        if specs_lines:
            lines.append("")
            lines.extend(specs_lines)

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

    def _generate_comprehensive_report(self, result):
        """Generate report for ComprehensiveAnalysisResult."""
        lines = []

        # Contract Overview
        if result.contract_overview:
            overview = result.contract_overview
            lines.append("CONTRACT OVERVIEW")
            lines.append("-" * 40)
            lines.append(f"Project Title: {overview.project_title}")
            lines.append(f"Solicitation No: {overview.solicitation_no}")
            lines.append(f"Owner: {overview.owner}")
            lines.append(f"Contractor: {overview.contractor}")
            lines.append(f"Scope: {overview.scope}")
            lines.append(f"Risk Level: {overview.general_risk_level}")
            lines.append(f"Bid Model: {overview.bid_model}")
            if overview.notes:
                lines.append(f"Notes: {overview.notes}")
            lines.append("")

        # Metadata
        if result.metadata:
            lines.append("DOCUMENT INFORMATION")
            lines.append("-" * 40)
            lines.append(f"Filename: {result.metadata.filename}")
            lines.append(f"Pages: {result.metadata.page_count}")
            lines.append(f"File Size: {result.metadata.file_size_bytes / 1024:.1f} KB")
            lines.append(f"Analyzed: {result.metadata.analyzed_at.strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("")

        # Section name mappings for display
        section_titles = {
            'administrative_and_commercial_terms': 'SECTION II: ADMINISTRATIVE & COMMERCIAL TERMS',
            'technical_and_performance_terms': 'SECTION III: TECHNICAL & PERFORMANCE TERMS',
            'legal_risk_and_enforcement': 'SECTION IV: LEGAL RISK & ENFORCEMENT',
            'regulatory_and_compliance_terms': 'SECTION V: REGULATORY & COMPLIANCE TERMS',
            'data_technology_and_deliverables': 'SECTION VI: DATA, TECHNOLOGY & DELIVERABLES',
        }

        sections = [
            ('administrative_and_commercial_terms', result.administrative_and_commercial_terms),
            ('technical_and_performance_terms', result.technical_and_performance_terms),
            ('legal_risk_and_enforcement', result.legal_risk_and_enforcement),
            ('regulatory_and_compliance_terms', result.regulatory_and_compliance_terms),
            ('data_technology_and_deliverables', result.data_technology_and_deliverables),
        ]

        for section_name, section in sections:
            if section is None:
                continue

            # Count non-None clause blocks in this section
            clause_blocks = []
            for field_name, value in section.__dict__.items():
                if field_name.startswith('_') or value is None:
                    continue
                if hasattr(value, 'clause_location'):
                    clause_blocks.append((field_name, value))

            if not clause_blocks:
                continue

            title = section_titles.get(section_name, section_name.replace('_', ' ').upper())
            lines.append(f"{title} ({len(clause_blocks)} clauses)")
            lines.append("=" * 60)
            lines.append("")

            for field_name, clause_block in clause_blocks:
                category_name = field_name.replace('_', ' ').title()
                lines.append(f"  {category_name}")
                lines.append(f"  {'-' * 40}")

                if clause_block.clause_location:
                    lines.append(f"  Location: {clause_block.clause_location}")

                if clause_block.clause_summary:
                    lines.append(f"  Summary: {clause_block.clause_summary}")

                lines.append("")

        # Supplemental Operational Risks
        if result.supplemental_operational_risks:
            lines.append(f"SECTION VII: SUPPLEMENTAL OPERATIONAL RISKS ({len(result.supplemental_operational_risks)} items)")
            lines.append("=" * 60)
            lines.append("")
            for i, risk_block in enumerate(result.supplemental_operational_risks, 1):
                lines.append(f"  Risk #{i}")
                lines.append(f"  {'-' * 40}")
                if risk_block.clause_location:
                    lines.append(f"  Location: {risk_block.clause_location}")
                if risk_block.clause_summary:
                    lines.append(f"  Summary: {risk_block.clause_summary}")
                lines.append("")

        return lines

    def _generate_bid_review_report(self):
        """Generate bid review section for the export report."""
        if not self.bid_review_tab:
            return []
        items = self.bid_review_tab.item_results
        if not items:
            return []

        from analyzer.bid_spec_patterns import BID_ITEM_MAP
        from src.bid_review_tab import SECTION_DEFS

        lines = []
        lines.append("BID SPECIFICATION REVIEW CHECKLIST")
        lines.append("=" * 60)
        lines.append("")

        for section_title, section_key, item_keys in SECTION_DEFS:
            section_items = [(k, items[k]) for k in item_keys if k in items]
            if not section_items:
                continue
            lines.append(f"  {section_title}")
            lines.append(f"  {'-' * 40}")
            for item_key, item in section_items:
                _, display_name = BID_ITEM_MAP.get(item_key, ("", item_key))
                value = item.value if hasattr(item, 'value') else str(item)
                conf = item.confidence if hasattr(item, 'confidence') else ''
                location = item.location if hasattr(item, 'location') else ''
                notes = item.notes if hasattr(item, 'notes') else ''
                line = f"    {display_name}: {value}"
                if location:
                    line += f"  [{location}]"
                if conf and conf != 'not_found':
                    line += f"  ({conf})"
                lines.append(line)
                if notes:
                    lines.append(f"      Notes: {notes}")
            lines.append("")

        found = sum(1 for item in items.values() if hasattr(item, 'found') and item.found)
        lines.append(f"  Total: {found}/{len(items)} items found")
        lines.append("")
        return lines

    def _generate_specs_report(self):
        """Generate specs section for the export report."""
        if not self.specs_tab:
            return []
        specs_text = self.specs_tab.results_text.toPlainText()
        if not specs_text or not specs_text.strip():
            return []

        lines = []
        lines.append("TECHNICAL SPECIFICATIONS")
        lines.append("=" * 60)
        lines.append("")
        lines.append(specs_text)
        lines.append("")
        return lines

    def init_engines(self):
        """Initialize analysis and query engines with local AI model."""
        try:
            model_name = self.config_manager.get_local_model_name() if self.config_manager else "llama-3.2-3b-q4"

            logger.info(f"Initializing local AI engine: {model_name}")

            # Check if model needs to be downloaded
            from src.model_manager import ModelManager
            model_mgr = ModelManager()

            if not model_mgr.is_model_cached(model_name):
                logger.info(f"Model {model_name} not cached, showing first-run dialog")

                first_run_dialog = FirstRunDialog(model_name, self)
                result = first_run_dialog.exec_()

                if result != QDialog.Accepted:
                    logger.info("First-run download cancelled")
                    self.statusBar().showMessage("Model download required. Go to Settings to configure.")
                    return

                logger.info("Model downloaded via first-run dialog, continuing initialization")

            self.statusBar().showMessage(f"Initializing local AI ({model_name})...")

            self.analysis_engine = AnalysisEngine(
                local_model_name=model_name
            )

            from src.document_retriever import DocumentRetriever
            self.retriever = DocumentRetriever()
            self.query_engine = QueryEngine(
                self.analysis_engine.ai_client,
                retriever=self.retriever
            )

            self.statusBar().showMessage(f"Ready (Local AI: {model_name})")
            logger.info("Local AI engine initialized successfully")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to initialize AI engine: {error_msg}", exc_info=True)

            QMessageBox.critical(
                self,
                "AI Initialization Error",
                f"Failed to initialize local AI model:\n\n{error_msg}\n\n"
                "Options:\n"
                "1. Try a different model in Settings\n"
                "2. Check available memory (need 8GB+ RAM)\n"
                "3. Ensure model is downloaded (Settings → Manage Models)"
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
            self.upload_mode = "file"
            self.current_file = filename
            self.current_folder = None
            self.folder_files = []

            self.file_label.setText(os.path.basename(filename))
            self.upload_mode_label.setText("Mode: Single File")
            self.load_btn.setEnabled(True)
            self.load_btn.setVisible(True)
            self.load_all_btn.setVisible(False)
            self.analyze_all_btn.setEnabled(False)
            self.upload_status.setText(f"File selected: {os.path.basename(filename)} — Click 'Load Contract' to begin.")

    def browse_folder(self):
        """Open folder browser for batch processing."""
        from pathlib import Path

        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Contract Folder",
            "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )

        if not folder_path:
            return

        folder = Path(folder_path)

        # Find all supported files in folder
        supported_exts = ['.pdf', '.docx', '.txt']
        files = []
        for ext in supported_exts:
            files.extend(folder.glob(f"*{ext}"))

        if not files:
            QMessageBox.warning(
                self,
                "No Files Found",
                f"No supported contract files found in:\n{folder_path}\n\n"
                f"Supported formats: PDF, DOCX, TXT"
            )
            return

        # Sort files by name
        files = sorted(files, key=lambda f: f.name.lower())

        # Warn for large batches
        if len(files) > 50:
            reply = QMessageBox.question(
                self,
                "Large Batch Warning",
                f"Found {len(files)} files. This may take several hours and incur significant API costs.\n\n"
                f"Do you want to continue?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        # Update state
        self.upload_mode = "folder"
        self.current_folder = folder_path
        self.folder_files = files
        self.current_file = None

        # Update UI - folder mode shows Load All button
        self.file_label.setText(f"{folder.name} ({len(files)} files)")
        self.upload_mode_label.setText(f"Mode: Folder ({len(files)} files)")
        self.load_btn.setVisible(False)
        self.load_all_btn.setVisible(True)
        self.load_all_btn.setEnabled(True)
        self.analyze_all_btn.setEnabled(False)

        # Show file list
        file_list = "\n".join([f"  • {f.name}" for f in files[:10]])
        if len(files) > 10:
            file_list += f"\n  ... and {len(files) - 10} more"

        self.upload_status.setText(f"Ready to load {len(files)} files:\n{file_list}")

    def _load_folder(self):
        """Load all folder files as combined context (no AI). Same as Load Contract but for multiple files."""
        if not self.analysis_engine:
            QMessageBox.warning(self, "Error", "Analysis engine not initialized. Check API key.")
            return

        if not self.folder_files:
            QMessageBox.warning(self, "Error", "No folder selected.")
            return

        # Reset previous state
        self.prepared_contract = None
        self.category_results = {}
        self.current_analysis = None
        if self.specs_tab:
            self.specs_tab.clear()

        # Initialize project storage for the folder
        from pathlib import Path
        from src.project_storage import ProjectStorage
        try:
            source_path = Path(self.current_folder)
            self.project_storage = ProjectStorage(source_path)
            valid, error = self.project_storage.is_valid_project_directory()
            if valid:
                self.project_storage.initialize_structure()
                self._reinit_storage_for_project()
                if self.session_manager:
                    self.session_manager.set_contract_info(
                        contract_file=f"{len(self.folder_files)} files",
                        contract_file_path=self.current_folder,
                        upload_mode=self.upload_mode,
                    )
        except Exception as e:
            logger.warning(f"Project storage init failed: {e}")

        # Update UI
        self.load_all_btn.setEnabled(False)
        self.analyze_all_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.upload_status.setText("Loading files...")
        self.statusBar().showMessage(f"Loading {len(self.folder_files)} files...")

        # Start preparation in background
        self.prepare_folder_thread = PrepareFolderThread(
            self.analysis_engine, self.folder_files
        )
        self.prepare_folder_thread.finished.connect(self.on_prepare_complete)
        self.prepare_folder_thread.error.connect(self.on_prepare_error)
        self.prepare_folder_thread.progress.connect(self.on_analysis_progress)
        self.prepare_folder_thread.start()

    def analyze_contract(self):
        """Start contract analysis (single file or folder batch)."""
        from pathlib import Path
        from src.project_storage import ProjectStorage

        if not self.analysis_engine:
            QMessageBox.warning(self, "Error", "Analysis engine not initialized. Check API key.")
            return

        # Determine source path based on mode
        source_path = None
        if self.upload_mode == "file":
            if not self.current_file:
                QMessageBox.warning(self, "Error", "No file selected")
                return
            source_path = Path(self.current_file)
        elif self.upload_mode == "folder":
            if not self.current_folder:
                QMessageBox.warning(self, "Error", "No folder selected")
                return
            source_path = Path(self.current_folder)
        else:
            QMessageBox.warning(self, "Error", f"Unknown upload mode: {self.upload_mode}")
            return

        # Initialize project storage
        try:
            self.project_storage = ProjectStorage(source_path)
            valid, error = self.project_storage.is_valid_project_directory()
            if not valid:
                QMessageBox.critical(
                    self,
                    "Permission Error",
                    f"Cannot create project storage:\n\n{error}"
                )
                return

            self.project_storage.initialize_structure()
            self._reinit_storage_for_project()

            logger.info(f"Project storage initialized at: {self.project_storage.project_root}")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Storage Error",
                f"Failed to initialize project storage:\n{e}\n\n"
                f"Make sure the folder is writable."
            )
            logger.error(f"Failed to initialize project storage: {e}", exc_info=True)
            return

        # Proceed with analysis based on mode
        if self.upload_mode == "file":
            self._analyze_single_file()
        elif self.upload_mode == "folder":
            self._analyze_folder_batch()

    def _reinit_storage_for_project(self):
        """Reinitialize storage components to use project paths."""
        from src.version_database import VersionDatabase
        from src.differential_storage import DifferentialStorage
        from src.history_store import HistoryStore
        from src.chat_history_manager import ChatHistoryManager

        try:
            # Reinitialize version database with project path
            self.version_db = VersionDatabase(
                db_path=self.project_storage.versions_db_path
            )

            # Reinitialize differential storage
            self.differential_storage = DifferentialStorage(self.version_db)

            # Reinitialize history store with project analyses directory
            self.history_store = HistoryStore(
                storage_dir=self.project_storage.analyses_dir
            )

            # Initialize chat history manager
            self.chat_history_manager = ChatHistoryManager(
                self.project_storage.chat_history_path
            )

            # Update query engine with chat history manager
            if self.query_engine:
                self.query_engine.chat_history_manager = self.chat_history_manager

            # Initialize session manager for auto-save/restore
            from src.session_manager import SessionManager
            self.session_manager = SessionManager(self.project_storage.storage_root)

            # Reinitialize History tab with new project-specific history store
            self.init_history_tab()

            logger.info("Storage components reinitialized for project mode")
            logger.info(f"History now saving to: {self.project_storage.analyses_dir}")

        except Exception as e:
            logger.error(f"Failed to reinitialize storage: {e}", exc_info=True)
            raise

    def _analyze_single_file(self):
        """Analyze a single file."""
        # Disable button and show progress
        self.load_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.upload_status.setText("Analyzing contract... This may take several minutes...")
        self.statusBar().showMessage("Analyzing contract...")

        # Extract and store contract text for later verification
        try:
            self.contract_text = self.analysis_engine.uploader.extract_text(self.current_file)
        except Exception as e:
            self.contract_text = None

        # Start analysis in background thread
        self.analysis_thread = AnalysisThread(
            self.analysis_engine,
            self.current_file
        )
        self.analysis_thread.finished.connect(self.on_analysis_complete)
        self.analysis_thread.error.connect(self.on_analysis_error)
        self.analysis_thread.progress.connect(self.on_analysis_progress)
        self.analysis_thread.start()

    def _analyze_folder_batch(self):
        """Analyze all files in a folder sequentially."""
        # Disable UI during processing
        self.load_all_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.upload_status.setText("Starting batch analysis...")
        self.statusBar().showMessage(f"Batch analyzing {len(self.folder_files)} files...")

        # Create batch analysis thread
        self.batch_thread = BatchAnalysisThread(
            self.analysis_engine,
            self.folder_files
        )

        self.batch_thread.progress.connect(self._on_batch_progress)
        self.batch_thread.file_complete.connect(self._on_file_complete)
        self.batch_thread.finished.connect(self._on_batch_finished)
        self.batch_thread.error.connect(self._on_batch_error)

        self.batch_thread.start()

    def _on_batch_progress(self, message, current, total, percent):
        """Handle batch progress updates."""
        self.progress_bar.setValue(percent)
        self.upload_status.setText(f"Batch Analysis: {current}/{total}\n{message}")
        self.statusBar().showMessage(f"Processing: {current}/{total} files ({percent}%)")

    def _on_file_complete(self, filename, result):
        """Handle completion of individual file in batch."""
        if result:
            logger.info(f"Completed analysis: {filename}")
            # Auto-save will happen automatically from the batch thread
        else:
            logger.warning(f"Analysis failed: {filename}")

    def _on_batch_finished(self, results):
        """Handle completion of entire batch."""
        # Count successes and failures
        successes = [r for r in results if r['status'] == 'success']
        failures = [r for r in results if r['status'] == 'error']

        # Re-enable UI
        self.load_all_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        # Show summary
        summary = f"Batch Analysis Complete!\n\n"
        summary += f"Successful: {len(successes)}/{len(results)}\n"

        if failures:
            summary += f"Failed: {len(failures)}\n\n"
            summary += "Failed files:\n"
            for failure in failures[:5]:
                error_msg = failure.get('error', 'Unknown error')[:50]
                summary += f"  • {failure['file']}: {error_msg}...\n"
            if len(failures) > 5:
                summary += f"  ... and {len(failures) - 5} more\n"

        QMessageBox.information(self, "Batch Analysis Complete", summary)

        # Refresh history tab if it exists
        if self.history_tab:
            self.history_tab.refresh()

        self.upload_status.setText("Batch analysis complete. Select a new file or folder to continue.")
        self.statusBar().showMessage("Ready")

    def _on_batch_error(self, filename, error_msg):
        """Handle individual file error in batch."""
        logger.error(f"Error analyzing {filename}: {error_msg}")
        # Don't show popup for individual errors (will be shown in summary)
    
    def on_analysis_progress(self, status, percent):
        """Handle analysis progress update."""
        self.progress_bar.setValue(percent)
        self.upload_status.setText(f"{status}")
    
    def on_analysis_complete(self, result):
        """Handle analysis completion."""
        self.current_analysis = result
        
        # Clear the history record ID since this is a new analysis (not from history)
        self.current_history_record_id = None
        
        # Hide progress
        self.progress_bar.setVisible(False)
        self.load_btn.setEnabled(True)
        self.upload_status.setText("Analysis complete!")
        self.statusBar().showMessage("Analysis complete")
        
        # Auto-save to history store
        self._auto_save_analysis(result)
        
        # Display results
        self.display_analysis(result)

        # Load chat history for this contract
        self._load_chat_history_for_contract()

        # Contract tab is already at index 0 (merged)
        self.tabs.setCurrentIndex(0)

        QMessageBox.information(self, "Success", "Contract analysis complete!\n\nView results in the Contract tab or ask questions in the Chat tab.")
    
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
        
        # When differential storage is active, it handles persistence and versioning;
        # skip the legacy history_store save to avoid duplicate entries.
        if self.differential_storage:
            if self.history_tab:
                self.history_tab.refresh()
                logger.info("Refreshed history tab with versioned data")
            return

        # Save to history store (legacy fallback when no differential storage)
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

        # Refresh history tab to reflect the new version
        if self.history_tab:
            self.history_tab.refresh()
            logger.info("Refreshed history tab after storing version %d", new_version)
    
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
                                    content=str(clause_dict.get('Clause Location') or clause_dict.get('clause_location') or clause_dict.get('Clause Language') or clause_dict.get('clause_language', '')),
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
        self.load_btn.setEnabled(True)
        self.upload_status.setText(f"Analysis failed: {error}")
        self.statusBar().showMessage("Analysis failed")

        QMessageBox.critical(self, "Analysis Error", f"Analysis failed:\n\n{error}")

    # --- Per-item on-demand analysis methods ---

    def load_contract(self):
        """Load contract: extract text + run regex (no AI). Triggered by 'Load Contract' button."""
        if not self.analysis_engine:
            QMessageBox.warning(self, "Error", "Analysis engine not initialized.")
            return

        if not self.current_file:
            QMessageBox.warning(self, "Error", "No file selected.")
            return

        # Reset previous state
        self.prepared_contract = None
        self.category_results = {}
        self.current_analysis = None
        if self.specs_tab:
            self.specs_tab.clear()

        # Update UI
        self.load_btn.setEnabled(False)
        self.analyze_all_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.upload_status.setText("Loading contract...")
        self.statusBar().showMessage("Loading contract...")

        # Extract text for chat/verification
        try:
            self.contract_text = self.analysis_engine.uploader.extract_text(self.current_file)
        except Exception:
            self.contract_text = None

        # Initialize project storage
        from pathlib import Path
        from src.project_storage import ProjectStorage
        try:
            source_path = Path(self.current_file)
            self.project_storage = ProjectStorage(source_path)
            valid, error = self.project_storage.is_valid_project_directory()
            if valid:
                self.project_storage.initialize_structure()
                self._reinit_storage_for_project()
                # Record contract info in session
                if self.session_manager:
                    self.session_manager.set_contract_info(
                        contract_file=os.path.basename(self.current_file),
                        contract_file_path=self.current_file,
                        upload_mode=self.upload_mode,
                    )
        except Exception as e:
            logger.warning(f"Project storage init failed: {e}")

        # Start preparation in background
        self.prepare_thread = PrepareContractThread(
            self.analysis_engine, self.current_file
        )
        self.prepare_thread.finished.connect(self.on_prepare_complete)
        self.prepare_thread.error.connect(self.on_prepare_error)
        self.prepare_thread.progress.connect(self.on_analysis_progress)
        self.prepare_thread.start()

    def on_prepare_complete(self, prepared):
        """Handle contract preparation completion."""
        self.prepared_contract = prepared
        self.contract_text = prepared.contract_text  # Store for bid review and chat
        self.progress_bar.setVisible(False)
        self.load_btn.setEnabled(True)
        self.load_all_btn.setEnabled(True)
        self.analyze_all_btn.setEnabled(True)

        # Count regex hits
        regex_count = sum(len(v) for v in prepared.extracted_clauses.values())
        cat_count = len(prepared.extracted_clauses)

        filename = prepared.file_info.get('filename', 'Unknown')
        text_len = len(prepared.contract_text) if prepared.contract_text else 0
        section_count = len(prepared.section_index) if prepared.section_index else 0

        # Wire retriever's indexed contract to the query engine for chat search
        if hasattr(self, 'retriever') and prepared.indexed:
            self.retriever._indexed = prepared.indexed
            if self.query_engine:
                self.query_engine.retriever = self.retriever
                self.query_engine.indexed_contract = prepared.indexed

        self._log_to_chat('system', f'Contract loaded: {filename}')
        self._log_to_chat('log', f'Extracted {text_len:,} characters, parsed {section_count} sections')
        self._log_to_chat('log', f'Indexed {section_count} sections for search (regex + keyword + TF-IDF)')
        self._log_to_chat('log', f'Pattern matching found {regex_count} clause matches across {cat_count} categories')
        self._log_to_chat('log', "Click 'Analyze' on individual items or 'Analyze All' to run AI analysis.")

        self.upload_status.setText(
            f"Contract loaded! {regex_count} pattern matches across {cat_count} categories. "
            f"Click 'Analyze' on individual items or 'Analyze All' to run AI analysis."
        )
        self.statusBar().showMessage(f"Contract loaded: {filename}")

        # Enable Specs tab now that contract is loaded
        if self.specs_tab:
            self.specs_tab.set_contract_loaded(True)

        # Enable Bid Review tab now that contract is loaded
        if self.bid_review_tab:
            # Prepare bid engine so per-item Analyze buttons work immediately
            if self.analysis_engine and self.analysis_engine.ai_client:
                from src.bid_review_engine import BidReviewEngine
                bid_engine = BidReviewEngine(self.analysis_engine.ai_client)
                bid_prepared = bid_engine.prepare_bid_review(
                    contract_text=self.contract_text,
                    file_path=self.file_label.text() if hasattr(self, 'file_label') else "",
                    page_count=getattr(self, '_page_count', 0),
                    file_size_bytes=getattr(self, '_file_size_bytes', 0),
                )
                self.bid_review_tab.set_engine_and_prepared(bid_engine, bid_prepared)
            self.bid_review_tab.set_contract_loaded(True)

        # Set up the structured view for per-item analysis
        self.structured_view.set_category_key_map(self.analysis_engine.CATEGORY_MAP)
        self.structured_view.set_regex_indicators(
            prepared.extracted_clauses, self.analysis_engine.CATEGORY_MAP
        )
        self.structured_view.enable_analyze_buttons(True)

        # Clear all boxes first
        self.structured_view._clear_all_boxes()

        # Attempt to restore previous session for this contract
        self._try_restore_session()

    def on_prepare_error(self, error):
        """Handle contract preparation error."""
        self.progress_bar.setVisible(False)
        self.load_btn.setEnabled(True)
        self.load_all_btn.setEnabled(True)
        self.upload_status.setText(f"Load failed: {error}")
        self.statusBar().showMessage("Load failed")
        QMessageBox.critical(self, "Load Error", f"Failed to load contract:\n\n{error}")

    def on_category_analyze_requested(self, cat_key):
        """Handle click on per-category Analyze button."""
        if not self.prepared_contract:
            QMessageBox.warning(self, "Error", "No contract loaded. Click 'Load Contract' first.")
            return

        if not self.analysis_engine:
            QMessageBox.warning(self, "Error", "Analysis engine not initialized.")
            return

        # Prevent double-clicks while analyzing
        if self.active_category_thread and self.active_category_thread.isRunning():
            self.upload_status.setText("Please wait for the current analysis to finish...")
            return

        # Prevent concurrent model access with bid review (llama_cpp not thread-safe)
        bid_thread = getattr(self.bid_review_tab, '_current_thread', None) if self.bid_review_tab else None
        if bid_thread and bid_thread.isRunning():
            QMessageBox.warning(
                self, "Please Wait",
                "A bid review analysis is in progress.\n"
                "Please wait for it to finish before analyzing contract categories."
            )
            return

        # Update status
        self.structured_view.update_category_status(
            cat_key, "loading", self.analysis_engine.CATEGORY_MAP
        )
        self.statusBar().showMessage(f"Analyzing {cat_key}...")

        # Start single-category analysis in background
        self.active_category_thread = SingleCategoryThread(
            self.analysis_engine, self.prepared_contract, cat_key
        )
        self.active_category_thread.finished.connect(self.on_category_complete)
        self.active_category_thread.not_found.connect(self.on_category_not_found)
        self.active_category_thread.error.connect(self.on_category_error)
        self.active_category_thread.progress.connect(self.on_analysis_progress)
        self.active_category_thread.start()

    def on_category_complete(self, cat_key, display_name, clause_block, prompt='', response=''):
        """Handle single category analysis completion."""
        # Store result
        self.category_results[cat_key] = clause_block

        # Auto-save to session
        if self.session_manager:
            self.session_manager.update_category_result(cat_key, clause_block)
            self.session_manager.save()

        # Update the view
        self.structured_view.fill_single_category(
            cat_key, clause_block, self.analysis_engine.CATEGORY_MAP
        )
        self.structured_view.update_category_status(
            cat_key, "analyzed", self.analysis_engine.CATEGORY_MAP
        )

        # Log to chat panel
        summary = clause_block.get('Clause Summary', '') if isinstance(clause_block, dict) else ''
        location = clause_block.get('Clause Location', '') if isinstance(clause_block, dict) else ''
        self._log_to_chat('summary', f'{summary}\nLocation: {location}', f'Analyzed: {display_name}')

        if prompt:
            self._log_to_chat('prompt', prompt[:1200] + ('...' if len(prompt) > 1200 else ''), 'Prompt sent to AI:')
        if response:
            self._log_to_chat('response', response[:1200] + ('...' if len(response) > 1200 else ''), 'AI response:')

        # Build current analysis for chat/export
        self._rebuild_current_analysis()

        # On first category completion, extract contract overview in background
        if len(self.category_results) == 1 and not getattr(self, '_overview_extracted', False):
            self._extract_overview_async()

        self.statusBar().showMessage(f"Analyzed: {display_name}")
        self.upload_status.setText(
            f"Analyzed: {display_name} ({len(self.category_results)} categories done)"
        )

    def _extract_overview_async(self):
        """Extract contract overview in background thread (AI call)."""
        if not self.analysis_engine or not self.contract_text:
            return
        # Prevent concurrent AI access
        if self.active_category_thread and self.active_category_thread.isRunning():
            return
        bid_thread = getattr(self.bid_review_tab, '_current_thread', None) if self.bid_review_tab else None
        if bid_thread and bid_thread.isRunning():
            return

        from PyQt5.QtCore import QThread, pyqtSignal

        class OverviewThread(QThread):
            finished = pyqtSignal(object)
            def __init__(self, engine, text):
                super().__init__()
                self.engine = engine
                self.text = text
            def run(self):
                try:
                    overview = self.engine._extract_contract_overview(self.text)
                    self.finished.emit(overview)
                except Exception as e:
                    logger.warning("Overview extraction failed: %s", e)
                    self.finished.emit(None)

        def on_overview_done(overview):
            self._overview_extracted = True
            if overview:
                self.structured_view._fill_contract_overview(overview)
                # Rebuild analysis with overview
                self._rebuild_current_analysis(include_overview=False)
                if self.current_analysis and hasattr(self.current_analysis, 'contract_overview'):
                    from src.analysis_models import ContractOverview
                    self.current_analysis.contract_overview = ContractOverview.from_dict(overview) if isinstance(overview, dict) else overview
                logger.info("Contract overview displayed")

        self._overview_thread = OverviewThread(self.analysis_engine, self.contract_text)
        self._overview_thread.finished.connect(on_overview_done)
        self._overview_thread.start()

    def on_category_not_found(self, cat_key, prompt='', response=''):
        """Handle category not found by AI."""
        self.structured_view.update_category_status(
            cat_key, "not_found", self.analysis_engine.CATEGORY_MAP
        )

        # Auto-save to session
        if self.session_manager:
            self.session_manager.mark_category_not_found(cat_key)
            self.session_manager.save()
        mapping = self.analysis_engine.CATEGORY_MAP.get(cat_key)
        name = mapping[1] if mapping else cat_key
        self._log_to_chat('log', f'Not found in contract: {name}')
        if prompt:
            self._log_to_chat('prompt', prompt[:1200] + ('...' if len(prompt) > 1200 else ''), f'Prompt sent to AI ({name}):')
        if response:
            self._log_to_chat('response', response[:1200] + ('...' if len(response) > 1200 else ''), f'AI response ({name}):')
        self.statusBar().showMessage(f"Not found: {name}")

    def on_category_error(self, cat_key, error_msg):
        """Handle single category analysis error."""
        self.structured_view.update_category_status(
            cat_key, "error", self.analysis_engine.CATEGORY_MAP
        )
        mapping = self.analysis_engine.CATEGORY_MAP.get(cat_key)
        name = mapping[1] if mapping else cat_key
        self._log_to_chat('error', f'{name}: {error_msg}', 'Analysis Error')
        self.statusBar().showMessage(f"Error analyzing {name}: {error_msg}")
        logger.error(f"Category analysis error for {cat_key}: {error_msg}")

    def analyze_all(self):
        """Analyze all categories sequentially. Triggered by 'Analyze All' button."""
        if not self.prepared_contract:
            QMessageBox.warning(self, "Error", "No contract loaded. Click 'Load Contract' first.")
            return

        if not self.analysis_engine:
            QMessageBox.warning(self, "Error", "Analysis engine not initialized.")
            return

        # Disable buttons during analysis
        self.analyze_all_btn.setEnabled(False)
        self.load_btn.setEnabled(False)
        self.structured_view.enable_analyze_buttons(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.upload_status.setText("Running AI analysis on all categories...")

        self.analyze_all_thread = AnalyzeAllThread(
            self.analysis_engine, self.prepared_contract
        )
        self.analyze_all_thread.category_complete.connect(self.on_category_complete)
        self.analyze_all_thread.category_not_found.connect(self.on_category_not_found)
        self.analyze_all_thread.category_error.connect(self.on_category_error)
        self.analyze_all_thread.all_finished.connect(self.on_analyze_all_finished)
        self.analyze_all_thread.progress.connect(self.on_analysis_progress)
        self.analyze_all_thread.start()

    def on_analyze_all_finished(self):
        """Handle completion of Analyze All."""
        self.progress_bar.setVisible(False)
        self.analyze_all_btn.setEnabled(True)
        self.load_btn.setEnabled(True)
        self.structured_view.enable_analyze_buttons(True)

        count = len(self.category_results)
        self.upload_status.setText(
            f"Analysis complete! {count} categories analyzed."
        )
        self.statusBar().showMessage("Analysis complete")

        # Build and save the full result (safe to extract overview now — no AI thread running)
        self._rebuild_current_analysis(include_overview=True)

        # Auto-save
        if self.current_analysis:
            self._auto_save_analysis(self.current_analysis)
            self._load_chat_history_for_contract()

    def on_specs_analysis_requested(self):
        """Handle spec analysis request from Specs tab."""
        if not self.contract_text:
            QMessageBox.warning(
                self, "No Contract",
                "No contract text available. Load a contract first."
            )
            return

        if not self.analysis_engine or not self.analysis_engine.ai_client:
            QMessageBox.warning(
                self, "Error",
                "Analysis engine or AI client not initialized."
            )
            return

        self.specs_tab.start_analysis(
            self.analysis_engine.ai_client,
            self.contract_text
        )

    def _on_specs_finished(self, text):
        """Handle specs analysis completion — log to chat."""
        # Count lines/sections for a summary
        lines = [l for l in text.split('\n') if l.strip()]
        preview = '\n'.join(lines[:10])
        if len(lines) > 10:
            preview += f'\n... ({len(lines) - 10} more lines)'
        self._log_to_chat('summary', preview, f'Specs Analysis ({len(lines)} lines)')

    def on_bid_review_analysis_requested(self):
        """Handle bid review analysis request from Bid Review tab."""
        if not self.contract_text:
            QMessageBox.warning(
                self, "No Contract",
                "No contract text available. Load a contract first."
            )
            return

        if not self.analysis_engine or not self.analysis_engine.ai_client:
            QMessageBox.warning(
                self, "Error",
                "Analysis engine or AI client not initialized."
            )
            return

        # Prevent concurrent model access (llama_cpp not thread-safe)
        if self.active_category_thread and self.active_category_thread.isRunning():
            QMessageBox.warning(
                self, "Please Wait",
                "A contract analysis is in progress on the Contract tab.\n"
                "Please wait for it to finish before running bid review."
            )
            return

        # Reuse engine/prepared if already set during contract load, else create
        bid_engine = self.bid_review_tab.bid_engine
        prepared = self.bid_review_tab.prepared
        if not bid_engine or not prepared:
            from src.bid_review_engine import BidReviewEngine
            bid_engine = BidReviewEngine(self.analysis_engine.ai_client)
            prepared = bid_engine.prepare_bid_review(
                contract_text=self.contract_text,
                file_path=self.file_label.text() if hasattr(self, 'file_label') else "",
                page_count=getattr(self, '_page_count', 0),
                file_size_bytes=getattr(self, '_file_size_bytes', 0),
            )

        # Start analysis on the tab
        self.bid_review_tab.start_analysis(bid_engine, prepared)

    def _on_bid_item_session_save(self, item_key, display_name, item):
        """Auto-save a single bid review item and log to chat."""
        if self.session_manager and hasattr(item, 'to_dict'):
            self.session_manager.update_bid_review_item(item_key, item.to_dict())
            self.session_manager.save()

        # Log to chat
        value = item.value if hasattr(item, 'value') else str(item)
        conf = item.confidence if hasattr(item, 'confidence') else ''
        location = item.location if hasattr(item, 'location') else ''
        notes = item.notes if hasattr(item, 'notes') else ''
        detail = f"{display_name}: {value}"
        if location:
            detail += f"\nLocation: {location}"
        if notes:
            detail += f"\nNotes: {notes}"
        self._log_to_chat('summary', detail, f'Bid Review ({conf})')

    def _on_bid_review_session_save(self, result):
        """Auto-save complete bid review result and log summary to chat."""
        if self.session_manager and result and hasattr(result, 'to_dict'):
            self.session_manager.update_bid_review_result(result.to_dict())
            self.session_manager.save()

        # Log summary to chat
        items = self.bid_review_tab.item_results if self.bid_review_tab else {}
        found = sum(1 for item in items.values() if hasattr(item, 'found') and item.found)
        total = len(items)
        self._log_to_chat('system', f'Bid Review complete: {found}/{total} items found ({round(found/total*100) if total else 0}%)')

    def _try_restore_session(self):
        """Attempt to restore a previous session for the loaded contract.

        Called at the end of on_prepare_complete(). At this point prepared_contract,
        structured_view, analysis_engine, and session_manager are all ready.
        """
        if not self.session_manager:
            return

        if not self.session_manager.load():
            return  # No session file or corrupt

        if not self.session_manager.has_session_for(self.current_file):
            logger.info("Session file is for a different contract, skipping restore")
            self.session_manager.clear()
            return

        # --- Restore category_results ---
        saved_categories = self.session_manager.category_results
        if saved_categories:
            self.category_results = dict(saved_categories)
            logger.info("Restored %d category results from session", len(self.category_results))

            for cat_key, clause_block in self.category_results.items():
                self.structured_view.fill_single_category(
                    cat_key, clause_block, self.analysis_engine.CATEGORY_MAP
                )
                self.structured_view.update_category_status(
                    cat_key, "analyzed", self.analysis_engine.CATEGORY_MAP
                )

        # --- Mark not-found categories ---
        for cat_key in self.session_manager.categories_not_found:
            self.structured_view.update_category_status(
                cat_key, "not_found", self.analysis_engine.CATEGORY_MAP
            )

        # --- Rebuild current_analysis for chat/export ---
        if self.category_results:
            self._rebuild_current_analysis()

        # --- Restore bid review items ---
        bid_items = self.session_manager.bid_review_item_results
        bid_result_dict = self.session_manager.bid_review_result
        if bid_items and self.bid_review_tab:
            self._restore_bid_review(bid_result_dict, bid_items)

        # --- Load chat history into panel ---
        self._load_chat_history_for_contract()

        # --- Update status ---
        n_cats = len(self.category_results)
        n_nf = len(self.session_manager.categories_not_found)
        n_bid = len(bid_items) if bid_items else 0
        parts = []
        if n_cats:
            parts.append(f"{n_cats} categories analyzed")
        if n_nf:
            parts.append(f"{n_nf} not found")
        if n_bid:
            parts.append(f"{n_bid} bid items")
        if parts:
            summary = ", ".join(parts)
            self.upload_status.setText(f"Session restored: {summary}. Chat enabled.")
            self.statusBar().showMessage("Previous session restored")
            self._log_to_chat('system', f"Previous session restored ({summary}). You can ask questions or continue analyzing.")

    def _restore_bid_review(self, result_dict, item_results_dict):
        """Restore bid review tab from saved session data."""
        from src.bid_review_models import ChecklistItem
        from analyzer.bid_spec_patterns import BID_ITEM_MAP

        for item_key, item_dict in item_results_dict.items():
            try:
                item = ChecklistItem.from_dict(item_dict)
                self.bid_review_tab.item_results[item_key] = item

                # Get display_name from BID_ITEM_MAP
                _, display_name = BID_ITEM_MAP.get(item_key, ("", item_key))

                # Reuse the tab's own display logic
                self.bid_review_tab._on_item_complete(item_key, display_name, item)
            except Exception as e:
                logger.warning("Failed to restore bid item %s: %s", item_key, e)

        # Restore full BidChecklistResult if available
        if result_dict:
            try:
                from src.bid_review_models import BidChecklistResult
                self.bid_review_tab._current_result = BidChecklistResult.from_dict(result_dict)
                self.bid_review_tab.analyze_all_btn.setText("Re-analyze Checklist")
            except Exception as e:
                logger.warning("Failed to restore bid review result: %s", e)

        self.bid_review_tab._update_stats()

    def _rebuild_current_analysis(self, include_overview=False):
        """Rebuild ComprehensiveAnalysisResult from accumulated category_results.

        Args:
            include_overview: If True, run AI to extract contract overview.
                Only set this when no other AI inference is running (e.g. after
                Analyze All finishes), because llama_cpp is NOT thread-safe.
        """
        if not self.prepared_contract or not self.category_results:
            return

        try:
            overview = None
            if include_overview and self.contract_text and self.analysis_engine:
                try:
                    overview = self.analysis_engine._extract_contract_overview(self.contract_text)
                except Exception as e:
                    logger.warning(f"Failed to extract contract overview: {e}")

            self.current_analysis = self.analysis_engine.build_comprehensive_result(
                self.prepared_contract,
                self.category_results,
                overview=overview
            )
        except Exception as e:
            logger.error(f"Failed to build comprehensive result: {e}")

    def get_or_build_current_analysis(self):
        """Get or build the current analysis for export/chat."""
        if self.current_analysis:
            return self.current_analysis
        self._rebuild_current_analysis()
        return self.current_analysis

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
            group = self.create_group("Document Information", metadata_text)
            self.analysis_layout.addWidget(group)
        
        # Clauses
        if result.clauses:
            clauses_text = ""
            for clause in result.clauses[:10]:  # Show first 10
                clauses_text += f"[{clause.risk_level.upper()}] {clause.type}\n"
                clauses_text += f"Page {clause.page}: {clause.text[:100]}...\n\n"
            group = self.create_group(f"Clauses ({len(result.clauses)} found)", clauses_text.strip())
            self.analysis_layout.addWidget(group)
        
        # Risks
        if result.risks:
            risks_text = ""
            for risk in result.risks[:5]:  # Show first 5
                risks_text += f"[{risk.severity.upper()}] {risk.description}\n"
                risks_text += f"Recommendation: {risk.recommendation}\n\n"
            group = self.create_group(f"Identified Risks ({len(result.risks)} found)", risks_text.strip())
            self.analysis_layout.addWidget(group)
        
        # Compliance Issues
        if result.compliance_issues:
            compliance_text = ""
            for issue in result.compliance_issues:
                compliance_text += f"[{issue.severity.upper()}] {issue.regulation}\n"
                compliance_text += f"{issue.issue}\n\n"
            group = self.create_group(f"Compliance Issues ({len(result.compliance_issues)} found)", compliance_text.strip())
            self.analysis_layout.addWidget(group)
        
        # Redlining Suggestions
        if result.redlining_suggestions:
            redlining_text = ""
            for suggestion in result.redlining_suggestions[:3]:  # Show first 3
                redlining_text += f"Clause: {suggestion.clause_id}\n"
                redlining_text += f"Rationale: {suggestion.rationale}\n\n"
            group = self.create_group(f" Redlining Suggestions ({len(result.redlining_suggestions)} found)", redlining_text.strip())
            self.analysis_layout.addWidget(group)
    
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
    
    # =========================================================================
    # Chat panel logging
    # =========================================================================

    def _log_to_chat(self, msg_type: str, content: str, title: str = None):
        """
        Append a styled message to the chat panel.

        Args:
            msg_type: 'system', 'log', 'prompt', 'response', 'summary',
                      'user', 'answer', 'error'
            content: Message text (plain text, will be HTML-escaped)
            title: Optional bold title line
        """
        import html
        safe = html.escape(content)

        styles = {
            'system':   'color: #555; font-style: italic; padding: 4px 8px;',
            'log':      'color: #888; font-size: 11px; padding: 2px 8px;',
            'prompt':   'background: #e3f2fd; border-left: 3px solid #1976D2; padding: 6px 10px; margin: 4px 0; font-family: monospace; font-size: 11px; white-space: pre-wrap;',
            'response': 'background: #e8f5e9; border-left: 3px solid #4CAF50; padding: 6px 10px; margin: 4px 0; font-family: monospace; font-size: 11px; white-space: pre-wrap;',
            'summary':  'padding: 4px 8px;',
            'user':     'padding: 4px 8px;',
            'answer':   'padding: 4px 8px;',
            'error':    'color: #c62828; padding: 4px 8px;',
        }

        style = styles.get(msg_type, 'padding: 4px 8px;')

        if title:
            safe_title = html.escape(title)
            html_msg = f'<div style="{style}"><b>{safe_title}</b><br>{safe}</div>'
        else:
            html_msg = f'<div style="{style}">{safe}</div>'

        self.chat_history.append(html_msg)
        # Auto-scroll to bottom
        scrollbar = self.chat_history.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def send_question(self):
        """Send a question to the query engine."""
        question = self.question_input.text().strip()
        if not question:
            return

        if not self.query_engine:
            QMessageBox.warning(self, "Error", "Query engine not initialized.")
            return

        # Try to build/get current analysis, fall back to minimal context
        analysis = self.get_or_build_current_analysis()
        if analysis:
            analysis_dict = analysis.to_dict()
        elif self.contract_text:
            # No analysis yet, but contract is loaded — provide minimal metadata
            # so the DocumentRetriever can still search the raw text
            analysis_dict = {
                'metadata': {
                    'filename': os.path.basename(self.current_file) if self.current_file else 'unknown',
                    'schema_version': 'minimal',
                },
            }
        else:
            QMessageBox.warning(self, "No Contract", "Please load a contract first.")
            return

        # Display question
        self._log_to_chat('user', question, 'You:')
        self.question_input.clear()
        self.send_btn.setEnabled(False)
        self.statusBar().showMessage("Processing query...")

        # Start query in background thread
        self.query_thread = QueryThread(self.query_engine, question, analysis_dict)
        self.query_thread.finished.connect(self.on_query_complete)
        self.query_thread.error.connect(self.on_query_error)
        self.query_thread.start()
    
    def on_query_complete(self, answer):
        """Handle query completion."""
        self._log_to_chat('answer', answer, 'Answer:')
        self.send_btn.setEnabled(True)
        self.statusBar().showMessage("Ready")

    def on_query_error(self, error):
        """Handle query error."""
        self._log_to_chat('error', str(error), 'Error:')
        self.send_btn.setEnabled(True)
        self.statusBar().showMessage("Query failed")

    def _load_chat_history_for_contract(self):
        """Load and display chat history for the current contract."""
        if not self.chat_history_manager:
            logger.debug("No chat history manager available")
            return

        try:
            # Get contract filename from analysis metadata or current_file
            filename = ''
            if self.current_analysis:
                if hasattr(self.current_analysis, 'metadata'):
                    filename = self.current_analysis.metadata.filename
                else:
                    metadata = self.current_analysis.get('metadata', {})
                    filename = metadata.get('filename', '')
            if not filename and self.current_file:
                filename = os.path.basename(self.current_file)

            if not filename:
                logger.warning("No filename in analysis metadata")
                return

            # Load chats for this contract
            chats = self.chat_history_manager.get_chats_for_contract(filename)

            if not chats:
                logger.info(f"No chat history found for {filename}")
                return

            # Clear existing chat display
            self.chat_history.clear()

            # Display welcome message
            self.chat_history.append("<b>Welcome to CR2A Chat!</b><br>")
            self.chat_history.append(f"<i>Loaded {len(chats)} previous conversation(s) for {filename}</i><br>")

            # Display all previous chats with user attribution
            for chat in chats:
                username = chat.get('username', 'unknown')
                computer_name = chat.get('computer_name', 'unknown')
                question = chat.get('question', '')
                answer = chat.get('answer', '')

                # Display question
                self.chat_history.append(f"<br><b>User ({username}@{computer_name}):</b> {question}<br>")

                # Display answer
                self.chat_history.append(f"<b>Answer:</b><br>{answer}<br>")

            logger.info(f"Loaded {len(chats)} chat entries for {filename}")

        except Exception as e:
            logger.error(f"Failed to load chat history: {e}", exc_info=True)


class SettingsDialog(QDialog):
    """Settings dialog for local AI model configuration."""

    def __init__(self, parent, config_manager):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(500)

        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """Initialize the dialog UI."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # =====================================================================
        # AI Model Configuration
        # =====================================================================
        model_group = QGroupBox("AI Model (Local)")
        model_layout = QVBoxLayout()
        model_group.setLayout(model_layout)

        # Model selection
        model_form = QFormLayout()

        self.model_combo = QComboBox()
        self.model_combo.addItem("Llama 3.2 3B Instruct (Q4_K_M) - Recommended", "llama-3.2-3b-q4")
        self.model_combo.addItem("Llama 3.1 8B Instruct (Q4_K_M) - Higher Quality", "llama-3.1-8b-q4")
        self.model_combo.addItem("Llama 3.1 8B Instruct (Q3_K_M) - 8B Lighter", "llama-3.1-8b-q3")
        self.model_combo.setToolTip(
            "3B Q4_K_M: ~3GB RAM, fast on CPU (recommended)\n"
            "8B Q4_K_M: ~6GB RAM, higher quality but slower on CPU\n"
            "8B Q3_K_M: ~5GB RAM, lighter 8B option"
        )
        model_form.addRow("Model:", self.model_combo)

        # CPU threads
        self.threads_spinner = QSpinBox()
        self.threads_spinner.setRange(1, 32)
        self.threads_spinner.setValue(0)  # 0 = auto-detect
        self.threads_spinner.setSpecialValueText("Auto-detect")
        self.threads_spinner.setToolTip("Number of CPU threads to use for inference (0 = auto-detect)")
        model_form.addRow("CPU Threads:", self.threads_spinner)

        model_layout.addLayout(model_form)

        # Manage Models button
        manage_btn_layout = QHBoxLayout()
        self.manage_models_btn = QPushButton("Manage Models...")
        self.manage_models_btn.setToolTip("Download, delete, or register custom models")
        self.manage_models_btn.clicked.connect(self.open_model_manager)
        manage_btn_layout.addWidget(self.manage_models_btn)
        manage_btn_layout.addStretch()
        model_layout.addLayout(manage_btn_layout)

        layout.addWidget(model_group)

        # =====================================================================
        # Dialog Buttons
        # =====================================================================
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_settings(self):
        """Load current settings from config manager."""
        if not self.config_manager:
            return

        model_name = self.config_manager.get_local_model_name()
        index = self.model_combo.findData(model_name)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)

        threads = self.config_manager.get_local_model_threads()
        if threads is not None:
            self.threads_spinner.setValue(threads)
        else:
            self.threads_spinner.setValue(0)

    def open_model_manager(self):
        """Open Model Management Dialog."""
        dialog = ModelManagementDialog(self)
        dialog.exec_()

    def save_settings(self):
        """Save settings to config file."""
        if not self.config_manager:
            QMessageBox.critical(self, "Error", "Configuration manager not available.")
            return

        try:
            model_name = self.model_combo.currentData()
            self.config_manager.set_local_model_name(model_name)

            threads = self.threads_spinner.value()
            if threads == 0:
                threads = None
            self.config_manager.set_local_model_threads(threads)

            self.config_manager.save_config()
            self.accept()

        except Exception as e:
            logger.error(f"Failed to save settings: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save settings:\n{str(e)}"
            )


class ModelManagementDialog(QDialog):
    """Dialog for managing local AI models (download, delete, register custom)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model_manager = None
        self.setWindowTitle("Model Manager")
        self.setModal(True)
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)

        self.init_model_manager()
        self.init_ui()
        self.refresh_model_lists()

    def init_model_manager(self):
        """Initialize ModelManager instance."""
        try:
            from src.model_manager import ModelManager
            self.model_manager = ModelManager()
            logger.info("ModelManager initialized in dialog")
        except Exception as e:
            logger.error(f"Failed to initialize ModelManager: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Initialization Error",
                f"Failed to initialize Model Manager:\n\n{str(e)}\n\n"
                "Model management features will not be available."
            )
            self.model_manager = None

    def init_ui(self):
        """Initialize the dialog UI."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # =====================================================================
        # Available Models Section (models that can be downloaded)
        # =====================================================================
        available_group = QGroupBox("Available Models (Download)")
        available_layout = QVBoxLayout()
        available_group.setLayout(available_layout)

        self.available_list = QTextEdit()
        self.available_list.setReadOnly(True)
        self.available_list.setMaximumHeight(150)
        available_layout.addWidget(self.available_list)

        # Download button
        download_btn_layout = QHBoxLayout()
        self.download_btn = QPushButton("Download Selected Model")
        self.download_btn.clicked.connect(self.download_selected_model)
        download_btn_layout.addWidget(self.download_btn)
        download_btn_layout.addStretch()
        available_layout.addLayout(download_btn_layout)

        layout.addWidget(available_group)

        # =====================================================================
        # Cached Models Section (models already downloaded)
        # =====================================================================
        cached_group = QGroupBox("Cached Models")
        cached_layout = QVBoxLayout()
        cached_group.setLayout(cached_layout)

        self.cached_list = QTextEdit()
        self.cached_list.setReadOnly(True)
        self.cached_list.setMaximumHeight(150)
        cached_layout.addWidget(self.cached_list)

        # Delete button
        delete_btn_layout = QHBoxLayout()
        self.delete_btn = QPushButton("Delete Selected Model")
        self.delete_btn.clicked.connect(self.delete_selected_model)
        delete_btn_layout.addWidget(self.delete_btn)
        delete_btn_layout.addStretch()
        cached_layout.addLayout(delete_btn_layout)

        layout.addWidget(cached_group)

        # =====================================================================
        # Custom Model Registration
        # =====================================================================
        custom_group = QGroupBox("Custom Models")
        custom_layout = QVBoxLayout()
        custom_group.setLayout(custom_layout)

        custom_info = QLabel(
            "Have a fine-tuned model? Register it here for use in CR2A.\n"
            "Requirements: GGUF format (Q4_K_M quantization recommended)"
        )
        custom_info.setWordWrap(True)
        custom_info.setStyleSheet("color: #666; padding: 5px;")
        custom_layout.addWidget(custom_info)

        register_btn_layout = QHBoxLayout()
        self.register_btn = QPushButton("Register Custom Model...")
        self.register_btn.clicked.connect(self.register_custom_model)
        register_btn_layout.addWidget(self.register_btn)
        register_btn_layout.addStretch()
        custom_layout.addLayout(register_btn_layout)

        layout.addWidget(custom_group)

        # =====================================================================
        # Storage Information
        # =====================================================================
        storage_group = QGroupBox("Storage Information")
        storage_layout = QVBoxLayout()
        storage_group.setLayout(storage_layout)

        self.storage_label = QLabel("Models directory: ...")
        self.storage_label.setWordWrap(True)
        storage_layout.addWidget(self.storage_label)

        self.size_label = QLabel("Total cache size: ...")
        storage_layout.addWidget(self.size_label)

        layout.addWidget(storage_group)

        # =====================================================================
        # Progress Bar (hidden by default)
        # =====================================================================
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)

        # =====================================================================
        # Dialog Buttons
        # =====================================================================
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.accept)
        layout.addWidget(button_box)

    def refresh_model_lists(self):
        """Refresh the available and cached model lists."""
        if not self.model_manager:
            return

        try:
            # Get registry models (available for download)
            registry_models = self.model_manager.get_registry_models()

            available_text = ""
            for model in registry_models:
                status = "Downloaded" if model['is_cached'] else "Available"
                recommended = " (Recommended)" if model.get('recommended', False) else ""
                available_text += (
                    f"{status} - {model['name']}{recommended}\n"
                    f"  {model['description']}\n"
                    f"  Size: {model['size_mb']}MB\n\n"
                )

            self.available_list.setText(available_text.strip())

            # Get cached models
            cached_models = self.model_manager.list_models()

            cached_text = ""
            if cached_models:
                for model in cached_models:
                    custom_tag = " [Custom]" if model['is_custom'] else ""
                    recommended_tag = " " if model.get('recommended', False) else ""
                    cached_text += (
                        f"{model['display_name']}{recommended_tag}{custom_tag}\n"
                        f"  Path: {model['path']}\n"
                        f"  Size: {model['size_mb']:.1f}MB\n\n"
                    )
            else:
                cached_text = "No models cached yet. Download a model to get started."

            self.cached_list.setText(cached_text.strip())

            # Update storage info
            total_size = self.model_manager.get_total_cache_size()
            self.storage_label.setText(f"Models directory: {self.model_manager.models_dir}")
            self.size_label.setText(f"Total cache size: {total_size:.1f}MB ({total_size/1024:.2f}GB)")

        except Exception as e:
            logger.error(f"Failed to refresh model lists: {e}", exc_info=True)
            QMessageBox.warning(
                self,
                "Refresh Error",
                f"Failed to refresh model lists:\n\n{str(e)}"
            )

    def download_selected_model(self):
        """Download the selected model."""
        if not self.model_manager:
            QMessageBox.warning(self, "Error", "Model Manager not initialized.")
            return

        # Get model selection from user
        model_name, ok = self._select_model_dialog(
            "Download Model",
            "Select a model to download:",
            downloadable_only=True
        )

        if not ok or not model_name:
            return

        # Check if already cached
        if self.model_manager.is_model_cached(model_name):
            QMessageBox.information(
                self,
                "Already Downloaded",
                f"Model '{model_name}' is already downloaded and cached."
            )
            return

        # Confirm download
        model_info = self.model_manager.MODEL_REGISTRY.get(model_name)
        if not model_info:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Download",
            f"Download {model_info['name']}?\n\n"
            f"Size: {model_info['size_mb']}MB (~{model_info['size_mb']/1024:.2f}GB)\n"
            f"Time: ~5-15 minutes (depending on connection)\n\n"
            "This is a one-time download.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Start download
        self._download_model(model_name)

    def _select_model_dialog(self, title, message, downloadable_only=False):
        """Show a dialog to select a model."""
        from PyQt5.QtWidgets import QInputDialog

        if not self.model_manager:
            return None, False

        # Get available models
        if downloadable_only:
            models = [
                (name, info['name'])
                for name, info in self.model_manager.MODEL_REGISTRY.items()
                if not self.model_manager.is_model_cached(name)
            ]
        else:
            models = [
                (name, info['name'])
                for name, info in self.model_manager.MODEL_REGISTRY.items()
            ]

        if not models:
            QMessageBox.information(
                self,
                "No Models",
                "All models are already downloaded." if downloadable_only else "No models available."
            )
            return None, False

        # Create selection dialog
        model_names = [display_name for _, display_name in models]
        model_ids = [model_id for model_id, _ in models]

        selection, ok = QInputDialog.getItem(
            self,
            title,
            message,
            model_names,
            0,
            False
        )

        if ok and selection:
            # Find the model ID
            index = model_names.index(selection)
            return model_ids[index], True

        return None, False

    def _download_model(self, model_name):
        """Download a model with progress tracking."""
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText("Preparing download...")

        # Disable buttons
        self.download_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.register_btn.setEnabled(False)

        def progress_callback(status, percent):
            """Update progress bar."""
            self.progress_bar.setValue(percent)
            self.progress_label.setText(status)
            QApplication.processEvents()  # Keep UI responsive

        try:
            # Download model
            model_path = self.model_manager.download_model(model_name, progress_callback)

            # Success
            self.progress_bar.setVisible(False)
            self.progress_label.setVisible(False)

            QMessageBox.information(
                self,
                "Download Complete",
                f"Model downloaded successfully!\n\n"
                f"Path: {model_path}\n\n"
                f"You can now select this model in Settings."
            )

            # Refresh lists
            self.refresh_model_lists()

        except Exception as e:
            logger.error(f"Download failed: {e}", exc_info=True)
            self.progress_bar.setVisible(False)
            self.progress_label.setVisible(False)

            QMessageBox.critical(
                self,
                "Download Failed",
                f"Failed to download model:\n\n{str(e)}\n\n"
                "Please check your internet connection and try again."
            )

        finally:
            # Re-enable buttons
            self.download_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)
            self.register_btn.setEnabled(True)

    def delete_selected_model(self):
        """Delete a cached model."""
        if not self.model_manager:
            QMessageBox.warning(self, "Error", "Model Manager not initialized.")
            return

        # Get cached models
        cached_models = self.model_manager.list_models()

        if not cached_models:
            QMessageBox.information(
                self,
                "No Models",
                "No models are cached. Nothing to delete."
            )
            return

        # Create selection dialog
        from PyQt5.QtWidgets import QInputDialog

        model_names = [model['display_name'] for model in cached_models]
        model_ids = [model['name'] for model in cached_models]

        selection, ok = QInputDialog.getItem(
            self,
            "Delete Model",
            "Select a model to delete:",
            model_names,
            0,
            False
        )

        if not ok or not selection:
            return

        # Find the model ID
        index = model_names.index(selection)
        model_id = model_ids[index]

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Delete model '{selection}'?\n\n"
            "This will free up disk space but you'll need to re-download\n"
            "the model if you want to use it again.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Delete model
        try:
            success = self.model_manager.delete_model(model_id)

            if success:
                QMessageBox.information(
                    self,
                    "Deleted",
                    f"Model '{selection}' has been deleted."
                )
                self.refresh_model_lists()
            else:
                QMessageBox.warning(
                    self,
                    "Not Found",
                    f"Model '{selection}' was not found."
                )

        except Exception as e:
            logger.error(f"Delete failed: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Delete Failed",
                f"Failed to delete model:\n\n{str(e)}"
            )

    def register_custom_model(self):
        """Register a custom fine-tuned model."""
        if not self.model_manager:
            QMessageBox.warning(self, "Error", "Model Manager not initialized.")
            return

        # Get model display name
        from PyQt5.QtWidgets import QInputDialog

        display_name, ok = QInputDialog.getText(
            self,
            "Model Name",
            "Enter a display name for your custom model:",
            QLineEdit.Normal,
            "My Custom Model"
        )

        if not ok or not display_name.strip():
            return

        # Get model file path
        model_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Model File",
            "",
            "GGUF Models (*.gguf);;All Files (*)"
        )

        if not model_path:
            return

        # Register model
        try:
            from pathlib import Path
            registered_path = self.model_manager.register_custom_model(
                display_name,
                Path(model_path)
            )

            QMessageBox.information(
                self,
                "Model Registered",
                f"Custom model registered successfully!\n\n"
                f"Name: {display_name}\n"
                f"Path: {registered_path}\n\n"
                f"You can now select this model in Settings."
            )

            # Refresh lists
            self.refresh_model_lists()

        except Exception as e:
            logger.error(f"Registration failed: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Registration Failed",
                f"Failed to register custom model:\n\n{str(e)}"
            )


class FirstRunDialog(QDialog):
    """Dialog shown on first use to download the selected local AI model."""

    def __init__(self, model_name, parent=None):
        super().__init__(parent)
        self.model_name = model_name
        self.model_manager = None
        self.download_success = False

        self.setWindowTitle("First-Time Setup - Download Model")
        self.setModal(True)
        self.setMinimumWidth(500)

        self.init_model_manager()
        self.init_ui()

    def init_model_manager(self):
        """Initialize ModelManager instance."""
        try:
            from src.model_manager import ModelManager
            self.model_manager = ModelManager()
        except Exception as e:
            logger.error(f"Failed to initialize ModelManager: {e}", exc_info=True)
            self.model_manager = None

    def init_ui(self):
        """Initialize the dialog UI."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Get model info
        model_info = None
        if self.model_manager:
            model_info = self.model_manager.MODEL_REGISTRY.get(self.model_name)

        if not model_info:
            # Fallback if model not found
            model_info = {
                'name': self.model_name,
                'size_mb': 2800,
                'description': 'Local AI model'
            }

        # =====================================================================
        # Header Message
        # =====================================================================
        header = QLabel(" First-Time Setup")
        header.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # =====================================================================
        # Information Message
        # =====================================================================
        info_text = (
            f"To use Local AI, CR2A needs to download the AI model.\n\n"
            f"Model: {model_info['name']}\n"
            f"Size: ~{model_info['size_mb']/1024:.1f}GB\n"
            f"Download Time: ~5-15 minutes (depending on connection)\n\n"
            f"This is a one-time download. The model will be cached locally\n"
            f"and reused for all future analyses.\n\n"
            f"Note: Analysis with local AI runs entirely offline with no API costs."
        )

        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("padding: 15px; background: #f0f0f0; border-radius: 5px;")
        layout.addWidget(info_label)

        # =====================================================================
        # Progress Bar (hidden initially)
        # =====================================================================
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("padding: 5px; color: #666;")
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)

        # =====================================================================
        # Buttons
        # =====================================================================
        button_layout = QHBoxLayout()

        self.download_btn = QPushButton("Download Model")
        self.download_btn.setStyleSheet(
            "padding: 10px; font-size: 14px; font-weight: bold; "
            "background: #4CAF50; color: white;"
        )
        self.download_btn.clicked.connect(self.start_download)
        button_layout.addWidget(self.download_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("padding: 10px; font-size: 14px;")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def start_download(self):
        """Start downloading the model."""
        if not self.model_manager:
            QMessageBox.critical(
                self,
                "Error",
                "Model Manager not initialized. Cannot download model."
            )
            return

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText("Preparing download...")

        # Disable buttons during download
        self.download_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)

        def progress_callback(status, percent):
            """Update progress bar."""
            self.progress_bar.setValue(percent)
            self.progress_label.setText(status)
            QApplication.processEvents()  # Keep UI responsive

        try:
            # Download model
            model_path = self.model_manager.download_model(
                self.model_name,
                progress_callback
            )

            # Success
            self.download_success = True
            logger.info(f"Model downloaded successfully: {model_path}")

            QMessageBox.information(
                self,
                "Download Complete",
                f"Model downloaded successfully!\n\n"
                f"CR2A is now ready to use Local AI for contract analysis.\n\n"
                f"Path: {model_path}"
            )

            self.accept()

        except Exception as e:
            logger.error(f"Download failed: {e}", exc_info=True)

            # Hide progress
            self.progress_bar.setVisible(False)
            self.progress_label.setVisible(False)

            # Re-enable buttons
            self.download_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)

            # Show error
            reply = QMessageBox.critical(
                self,
                "Download Failed",
                f"Failed to download model:\n\n{str(e)}\n\n"
                "Options:\n"
                "- Try downloading again\n"
                "- Cancel and configure later\n\n"
                "Would you like to try again?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.start_download()

def main():
    """Main entry point."""
    import faulthandler
    from pathlib import Path

    # Write native crash tracebacks (segfaults) to a file
    crash_log_path = Path.home() / "AppData" / "Roaming" / "CR2A" / "crash.log"
    crash_log_path.parent.mkdir(parents=True, exist_ok=True)
    crash_log_file = open(crash_log_path, "w")
    faulthandler.enable(file=crash_log_file)
    logger.info(f"Faulthandler enabled, crash log: {crash_log_path}")

    # Global exception hook for uncaught Python exceptions
    def global_exception_hook(exc_type, exc_value, exc_tb):
        import traceback
        msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.critical(f"Uncaught exception:\n{msg}")
        with open(crash_log_path, "a") as f:
            f.write(f"\n--- Uncaught Python exception ---\n{msg}\n")
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = global_exception_hook

    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look

    window = CR2A_GUI()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

