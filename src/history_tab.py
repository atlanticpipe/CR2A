"""
History Tab Module

Provides the History tab UI component for displaying past analyses.
Users can view, select, and delete analysis records from the history.
Supports contract versioning with version selection and comparison.
"""

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QPushButton, QMessageBox, QGroupBox, QFrame, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from typing import Optional, Dict

from src.history_store import HistoryStore
from src.history_models import AnalysisRecord
from src.differential_storage import DifferentialStorage
from src.version_manager import VersionManager
from src.version_comparison_view import VersionComparisonView


logger = logging.getLogger(__name__)


class HistoryTab(QWidget):
    """
    History tab widget for displaying past analyses.
    
    This widget displays a scrollable list of past analysis records,
    allowing users to select records to view or delete them.
    Supports contract versioning with version selection.
    
    Signals:
        analysis_selected(str): Emitted when user selects a record (emits record_id)
        analysis_deleted(str): Emitted when user deletes a record (emits record_id)
        version_selected(str, int): Emitted when user selects a specific version (contract_id, version)
    """
    
    # Signals
    analysis_selected = pyqtSignal(str)  # Emits record_id when selected
    analysis_deleted = pyqtSignal(str)   # Emits record_id when deleted
    version_selected = pyqtSignal(str, int)  # Emits contract_id, version when version selected
    
    def __init__(self, history_store: HistoryStore, 
                 differential_storage: Optional[DifferentialStorage] = None,
                 parent=None):
        """
        Initialize history tab.
        
        Args:
            history_store: HistoryStore instance for data access
            differential_storage: Optional DifferentialStorage for version info
            parent: Parent widget
        """
        super().__init__(parent)
        self.history_store = history_store
        self.differential_storage = differential_storage
        self.version_manager = VersionManager(differential_storage) if differential_storage else None
        
        self.init_ui()
        self.refresh()
    
    def init_ui(self):
        """Initialize the user interface."""
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Title and instructions
        title = QLabel("Analysis History")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("padding: 10px;")
        layout.addWidget(title)
        
        instructions = QLabel(
            "View and manage your past contract analyses.\n"
            "Click on an analysis to view its full results."
        )
        instructions.setWordWrap(True)
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setStyleSheet("padding: 5px; font-size: 12px; color: #666;")
        layout.addWidget(instructions)
        
        # Scroll area for history list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        # Container widget for scroll area
        scroll_content = QWidget()
        self.history_layout = QVBoxLayout()
        self.history_layout.setSpacing(10)
        scroll_content.setLayout(self.history_layout)
        scroll.setWidget(scroll_content)
        
        layout.addWidget(scroll)
        
        # Placeholder for empty state
        self.empty_label = QLabel(
            "📭 No analysis history yet.\n\n"
            "Analyze a contract in the Upload tab to get started."
        )
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(
            "padding: 50px; font-size: 14px; color: #999;"
        )
        self.history_layout.addWidget(self.empty_label)
        
        # Add stretch at the end
        self.history_layout.addStretch()
    
    def refresh(self) -> None:
        """Refresh the history list from storage."""
        try:
            # Clear existing items (except empty label and stretch)
            while self.history_layout.count() > 0:
                item = self.history_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            # Load records - prefer differential_storage if available
            if self.differential_storage:
                logger.info("Loading history from differential storage (versioning enabled)")
                records = self._load_from_differential_storage()
            else:
                logger.info("Loading history from history store (versioning disabled)")
                records = self.history_store.load_all()
            
            if not records:
                # Show empty state
                self.empty_label = QLabel(
                    "📭 No analysis history yet.\n\n"
                    "Analyze a contract in the Upload tab to get started."
                )
                self.empty_label.setAlignment(Qt.AlignCenter)
                self.empty_label.setStyleSheet(
                    "padding: 50px; font-size: 14px; color: #999;"
                )
                self.history_layout.addWidget(self.empty_label)
            else:
                # Display records
                for record in records:
                    record_widget = self._create_record_widget(record)
                    self.history_layout.addWidget(record_widget)
            
            # Add stretch at the end
            self.history_layout.addStretch()
            
            logger.info("History list refreshed with %d records", len(records))
            
        except Exception as e:
            logger.error("Failed to refresh history list: %s", e)
            QMessageBox.warning(
                self,
                "Refresh Error",
                f"Failed to refresh history list:\n{str(e)}"
            )
    
    def _load_from_differential_storage(self):
        """
        Load analysis records from differential storage.
        
        Converts Contract objects from differential storage into AnalysisRecord
        objects for display in the history list.
        
        Returns:
            List of AnalysisRecord objects
        """
        from src.history_models import AnalysisRecord
        
        try:
            # Get all contracts from differential storage
            contracts = self.differential_storage.get_all_contracts()
            logger.info("Retrieved %d contracts from differential storage", len(contracts))
            
            # Convert to AnalysisRecord format
            records = []
            for contract in contracts:
                # Create a pseudo-record for display
                # Use contract_id as record_id for compatibility
                record = AnalysisRecord(
                    id=contract.contract_id,
                    filename=contract.filename,
                    timestamp=contract.updated_at,  # Use updated_at to show latest version time
                    file_path=None,  # Not stored in version database
                    summary=f"Version {contract.current_version}"
                )
                records.append(record)
            
            # Sort by timestamp (newest first)
            records.sort(key=lambda r: r.timestamp, reverse=True)
            
            return records
            
        except Exception as e:
            logger.error("Failed to load from differential storage: %s", e, exc_info=True)
            return []
    
    def add_record(self, record: AnalysisRecord) -> None:
        """
        Add a new record to the list without full refresh.
        
        This method adds a new record at the top of the list (newest first)
        and removes the empty state message if present.
        
        Args:
            record: The new analysis record to add
        """
        try:
            # Remove empty label if it exists
            for i in range(self.history_layout.count()):
                item = self.history_layout.itemAt(i)
                if item and item.widget() and isinstance(item.widget(), QLabel):
                    widget = item.widget()
                    if "No analysis history yet" in widget.text():
                        self.history_layout.removeWidget(widget)
                        widget.deleteLater()
                        break
            
            # Create and insert the new record widget at the top
            record_widget = self._create_record_widget(record)
            self.history_layout.insertWidget(0, record_widget)
            
            logger.info("Added record to history list: %s", record.id)
            
        except Exception as e:
            logger.error("Failed to add record to history list: %s", e)
    
    def remove_record(self, record_id: str) -> None:
        """
        Remove a record from the list.
        
        Args:
            record_id: ID of record to remove
        """
        try:
            # Find and remove the widget with matching record_id
            for i in range(self.history_layout.count()):
                item = self.history_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if hasattr(widget, 'record_id') and widget.record_id == record_id:
                        self.history_layout.removeWidget(widget)
                        widget.deleteLater()
                        logger.info("Removed record from history list: %s", record_id)
                        break
            
            # Check if list is now empty and show empty state
            has_records = False
            for i in range(self.history_layout.count()):
                item = self.history_layout.itemAt(i)
                if item and item.widget() and hasattr(item.widget(), 'record_id'):
                    has_records = True
                    break
            
            if not has_records:
                self.empty_label = QLabel(
                    "📭 No analysis history yet.\n\n"
                    "Analyze a contract in the Upload tab to get started."
                )
                self.empty_label.setAlignment(Qt.AlignCenter)
                self.empty_label.setStyleSheet(
                    "padding: 50px; font-size: 14px; color: #999;"
                )
                self.history_layout.insertWidget(0, self.empty_label)
            
        except Exception as e:
            logger.error("Failed to remove record from history list: %s", e)
    
    def _create_record_widget(self, record: AnalysisRecord) -> QWidget:
        """
        Create a widget for displaying a single analysis record.
        
        Args:
            record: The analysis record to display
            
        Returns:
            QWidget containing the record display
        """
        # Create a frame for the record
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet(
            "QFrame {"
            "    background: #f9f9f9;"
            "    border: 1px solid #ddd;"
            "    border-radius: 5px;"
            "    padding: 10px;"
            "}"
            "QFrame:hover {"
            "    background: #f0f0f0;"
            "    border: 1px solid #999;"
            "}"
        )
        
        # Store record_id as an attribute for later reference
        frame.record_id = record.id
        
        layout = QVBoxLayout()
        frame.setLayout(layout)
        
        # Top row: filename and date
        top_layout = QHBoxLayout()
        
        filename_label = QLabel(f"📄 {record.filename}")
        filename_label.setFont(QFont("Arial", 12, QFont.Bold))
        filename_label.setStyleSheet("color: #333;")
        top_layout.addWidget(filename_label)
        
        top_layout.addStretch()
        
        date_label = QLabel(record.analyzed_at.strftime("%Y-%m-%d %H:%M:%S"))
        date_label.setStyleSheet("color: #666; font-size: 11px;")
        top_layout.addWidget(date_label)
        
        layout.addLayout(top_layout)
        
        # Middle row: statistics and version info
        stats_layout = QHBoxLayout()
        
        clause_label = QLabel(f"📋 {record.clause_count} clauses")
        clause_label.setStyleSheet("color: #555; font-size: 11px;")
        stats_layout.addWidget(clause_label)
        
        risk_label = QLabel(f"⚠️ {record.risk_count} risks")
        risk_label.setStyleSheet("color: #555; font-size: 11px;")
        stats_layout.addWidget(risk_label)
        
        # Add version information if available
        if self.differential_storage:
            try:
                # Try to get contract by file hash or filename
                contract = self._get_contract_for_record(record)
                
                if contract:
                    # Show current version
                    version_label = QLabel(f"📌 Version {contract.current_version}")
                    version_label.setStyleSheet("color: #0066cc; font-size: 11px; font-weight: bold;")
                    stats_layout.addWidget(version_label)
                    
                    # Count clauses with multiple versions
                    versioned_clause_count = self._count_versioned_clauses(contract.contract_id)
                    if versioned_clause_count > 0:
                        versioned_label = QLabel(f"🔄 {versioned_clause_count} versioned")
                        versioned_label.setStyleSheet("color: #ff9800; font-size: 11px;")
                        stats_layout.addWidget(versioned_label)
            except Exception as e:
                logger.warning("Failed to get version info for record %s: %s", record.id, e)
        
        stats_layout.addStretch()
        
        layout.addLayout(stats_layout)
        
        # Version selector row (if versioning is available)
        if self.differential_storage:
            try:
                contract = self._get_contract_for_record(record)
                if contract and contract.current_version > 1:
                    version_layout = QHBoxLayout()
                    
                    version_selector_label = QLabel("View version:")
                    version_selector_label.setStyleSheet("color: #666; font-size: 10px;")
                    version_layout.addWidget(version_selector_label)
                    
                    version_combo = QComboBox()
                    version_combo.setStyleSheet(
                        "QComboBox {"
                        "    padding: 3px 8px;"
                        "    font-size: 10px;"
                        "    border: 1px solid #ccc;"
                        "    border-radius: 3px;"
                        "}"
                    )
                    
                    # Add all versions
                    for v in range(1, contract.current_version + 1):
                        version_combo.addItem(f"v{v}", v)
                    
                    # Set current version as default
                    version_combo.setCurrentIndex(contract.current_version - 1)
                    
                    # Connect version selection
                    version_combo.currentIndexChanged.connect(
                        lambda idx: self._on_version_selected(contract.contract_id, version_combo.itemData(idx))
                    )
                    
                    version_layout.addWidget(version_combo)
                    
                    # Add Compare Versions button (Requirement 6.1)
                    compare_btn = QPushButton("Compare Versions")
                    compare_btn.setStyleSheet(
                        "QPushButton {"
                        "    padding: 3px 10px;"
                        "    font-size: 10px;"
                        "    background: #2196F3;"
                        "    color: white;"
                        "    border: none;"
                        "    border-radius: 3px;"
                        "}"
                        "QPushButton:hover {"
                        "    background: #1976D2;"
                        "}"
                    )
                    compare_btn.clicked.connect(
                        lambda: self._on_compare_versions_clicked(contract.contract_id)
                    )
                    version_layout.addWidget(compare_btn)
                    
                    version_layout.addStretch()
                    
                    layout.addLayout(version_layout)
            except Exception as e:
                logger.warning("Failed to create version selector for record %s: %s", record.id, e)
        
        # Bottom row: action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        view_btn = QPushButton("View Analysis")
        view_btn.setStyleSheet(
            "QPushButton {"
            "    padding: 5px 15px;"
            "    font-size: 11px;"
            "    background: #4CAF50;"
            "    color: white;"
            "    border: none;"
            "    border-radius: 3px;"
            "}"
            "QPushButton:hover {"
            "    background: #45a049;"
            "}"
        )
        view_btn.clicked.connect(lambda: self._on_view_clicked(record.id))
        button_layout.addWidget(view_btn)
        
        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet(
            "QPushButton {"
            "    padding: 5px 15px;"
            "    font-size: 11px;"
            "    background: #f44336;"
            "    color: white;"
            "    border: none;"
            "    border-radius: 3px;"
            "}"
            "QPushButton:hover {"
            "    background: #da190b;"
            "}"
        )
        delete_btn.clicked.connect(lambda: self._on_delete_clicked(record.id, record.filename))
        button_layout.addWidget(delete_btn)
        
        layout.addLayout(button_layout)
        
        return frame
    
    def _on_view_clicked(self, record_id: str) -> None:
        """
        Handle view button click.
        
        Args:
            record_id: ID of the record to view
        """
        logger.info("View clicked for record: %s", record_id)
        self.analysis_selected.emit(record_id)
    
    def _on_delete_clicked(self, record_id: str, filename: str) -> None:
        """
        Handle delete button click.
        
        Shows a confirmation dialog before deleting.
        
        Args:
            record_id: ID of the record to delete
            filename: Filename for display in confirmation dialog
        """
        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete this analysis?\n\n"
            f"File: {filename}\n\n"
            f"This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Delete from storage
                success = self.history_store.delete(record_id)
                
                if success:
                    # Remove from UI
                    self.remove_record(record_id)
                    
                    # Emit signal
                    self.analysis_deleted.emit(record_id)
                    
                    logger.info("Deleted record: %s", record_id)
                    
                    QMessageBox.information(
                        self,
                        "Deleted",
                        "Analysis deleted successfully."
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Not Found",
                        "Analysis record not found."
                    )
                    
            except Exception as e:
                logger.error("Failed to delete record: %s. Error: %s", record_id, e)
                QMessageBox.critical(
                    self,
                    "Delete Error",
                    f"Failed to delete analysis:\n{str(e)}"
                )
    
    def _on_version_selected(self, contract_id: str, version: int) -> None:
        """
        Handle version selection from dropdown.
        
        Args:
            contract_id: ID of the contract
            version: Selected version number
        """
        logger.info("Version selected: contract %s, version %d", contract_id, version)
        self.version_selected.emit(contract_id, version)
    
    def _on_compare_versions_clicked(self, contract_id: str) -> None:
        """
        Handle compare versions button click.
        
        Opens the version comparison view for the contract.
        Implements Requirement 6.1: Comparison view option.
        
        Args:
            contract_id: ID of the contract to compare
        """
        logger.info("Opening version comparison for contract: %s", contract_id)
        
        try:
            # Create and show comparison view
            comparison_view = VersionComparisonView(
                contract_id=contract_id,
                differential_storage=self.differential_storage,
                parent=self
            )
            
            # Show as a modal dialog
            comparison_view.setWindowTitle("Version Comparison")
            comparison_view.setMinimumSize(1000, 700)
            comparison_view.setWindowModality(Qt.ApplicationModal)
            comparison_view.show()
            
        except Exception as e:
            logger.error("Failed to open version comparison: %s", e)
            QMessageBox.critical(
                self,
                "Comparison Error",
                f"Failed to open version comparison:\n{str(e)}"
            )
    
    def _get_contract_for_record(self, record: AnalysisRecord):
        """
        Get contract metadata for an analysis record.
        
        Args:
            record: Analysis record
            
        Returns:
            Contract object or None if not found
        """
        if not self.differential_storage:
            return None
        
        try:
            # Try to find contract by filename (simplified approach)
            # In a real implementation, you'd need a mapping from record_id to contract_id
            # For now, we'll search by filename
            all_contracts = self.differential_storage.get_all_contracts()
            
            for contract in all_contracts:
                if contract.filename == record.filename:
                    return contract
            
            return None
        except Exception as e:
            logger.error("Failed to get contract for record %s: %s", record.id, e)
            return None
    
    def _count_versioned_clauses(self, contract_id: str) -> int:
        """
        Count the number of clauses that have multiple versions.
        
        Args:
            contract_id: ID of the contract
            
        Returns:
            Count of clauses with multiple versions
        """
        if not self.differential_storage:
            return 0
        
        try:
            all_clauses = self.differential_storage.get_clauses(contract_id)
            
            # Group by clause_identifier and count unique versions
            clause_versions = {}
            for clause in all_clauses:
                identifier = clause.clause_identifier or clause.clause_id
                if identifier not in clause_versions:
                    clause_versions[identifier] = set()
                clause_versions[identifier].add(clause.clause_version)
            
            # Count clauses with more than one version
            versioned_count = sum(1 for versions in clause_versions.values() if len(versions) > 1)
            
            return versioned_count
        except Exception as e:
            logger.error("Failed to count versioned clauses for contract %s: %s", contract_id, e)
            return 0
    
    def retrieve_version(self, contract_id: str, version: int) -> Optional[Dict]:
        """
        Retrieve and reconstruct a specific version of a contract.
        
        Uses VersionManager.reconstruct_version() to get historical state.
        Implements Requirements 5.5, 7.1.
        
        Args:
            contract_id: ID of the contract
            version: Version number to retrieve
            
        Returns:
            Dictionary containing the reconstructed contract state or None if failed
        """
        if not self.version_manager:
            logger.error("Version manager not available")
            return None
        
        try:
            logger.info("Retrieving contract %s version %d", contract_id, version)
            
            # Use VersionManager to reconstruct the version
            reconstructed = self.version_manager.reconstruct_version(contract_id, version)
            
            logger.info("Successfully retrieved version %d with %d clauses", 
                       version, len(reconstructed.get('clauses', [])))
            
            return reconstructed
            
        except Exception as e:
            logger.error("Failed to retrieve version %s v%d: %s", contract_id, version, e)
            QMessageBox.critical(
                self,
                "Version Retrieval Error",
                f"Failed to retrieve version {version}:\n{str(e)}"
            )
            return None
    
    def display_version(self, contract_id: str, version: int) -> None:
        """
        Display a specific version of a contract.
        
        This method retrieves the version and emits a signal for the parent
        to handle the display.
        
        Args:
            contract_id: ID of the contract
            version: Version number to display
        """
        reconstructed = self.retrieve_version(contract_id, version)
        
        if reconstructed:
            # Emit signal with the reconstructed version data
            # The parent component (e.g., analysis screen) will handle display
            self.version_selected.emit(contract_id, version)
