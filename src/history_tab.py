"""
History Tab Module

Provides the History tab UI component for displaying past analyses.
Users can view, select, and delete analysis records from the history.
"""

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QPushButton, QMessageBox, QGroupBox, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from src.history_store import HistoryStore
from src.history_models import AnalysisRecord


logger = logging.getLogger(__name__)


class HistoryTab(QWidget):
    """
    History tab widget for displaying past analyses.
    
    This widget displays a scrollable list of past analysis records,
    allowing users to select records to view or delete them.
    
    Signals:
        analysis_selected(str): Emitted when user selects a record (emits record_id)
        analysis_deleted(str): Emitted when user deletes a record (emits record_id)
    """
    
    # Signals
    analysis_selected = pyqtSignal(str)  # Emits record_id when selected
    analysis_deleted = pyqtSignal(str)   # Emits record_id when deleted
    
    def __init__(self, history_store: HistoryStore, parent=None):
        """
        Initialize history tab.
        
        Args:
            history_store: HistoryStore instance for data access
            parent: Parent widget
        """
        super().__init__(parent)
        self.history_store = history_store
        
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
            
            # Load records from storage
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
        
        # Middle row: statistics
        stats_layout = QHBoxLayout()
        
        clause_label = QLabel(f"📋 {record.clause_count} clauses")
        clause_label.setStyleSheet("color: #555; font-size: 11px;")
        stats_layout.addWidget(clause_label)
        
        risk_label = QLabel(f"⚠️ {record.risk_count} risks")
        risk_label.setStyleSheet("color: #555; font-size: 11px;")
        stats_layout.addWidget(risk_label)
        
        stats_layout.addStretch()
        
        layout.addLayout(stats_layout)
        
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
