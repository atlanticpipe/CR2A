"""
Version Comparison View Module

Provides UI component for comparing two versions of a contract with
color-coded highlighting and change summaries.
Implements Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6.
"""

import difflib
import logging
from typing import Optional, Tuple, List
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QScrollArea, QFrame, QTextEdit, QGroupBox,
    QSplitter
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QTextCharFormat, QColor, QTextCursor

from src.differential_storage import DifferentialStorage
from src.version_manager import VersionManager
from src.change_comparator import ChangeComparator, ClauseChangeType


logger = logging.getLogger(__name__)


class VersionComparisonView(QWidget):
    """
    Widget for comparing two versions of a contract.
    
    Provides:
    - Version selection dropdowns
    - Color-coded change highlighting (green=added, yellow=modified, red=deleted)
    - Text diff with detailed changes
    - Change summary statistics
    
    Implements Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6.
    
    Signals:
        comparison_closed: Emitted when user closes the comparison view
    """
    
    comparison_closed = pyqtSignal()
    
    def __init__(
        self,
        contract_id: str,
        differential_storage: DifferentialStorage,
        parent=None
    ):
        """
        Initialize version comparison view.
        
        Args:
            contract_id: ID of the contract to compare
            differential_storage: Storage instance for accessing contract data
            parent: Parent widget
        """
        super().__init__(parent)
        self.contract_id = contract_id
        self.storage = differential_storage
        self.version_manager = VersionManager(differential_storage)
        self.comparator = ChangeComparator()
        
        self.init_ui()
        self.load_versions()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Title
        title = QLabel("Version Comparison")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("padding: 10px;")
        layout.addWidget(title)
        
        # Version selection row (Requirement 6.1)
        self._create_version_selector(layout)
        
        # Change summary row (Requirement 6.6)
        self._create_change_summary(layout)
        
        # Comparison display area
        self._create_comparison_display(layout)
        
        # Close button
        close_btn = QPushButton("Close Comparison")
        close_btn.setStyleSheet(
            "QPushButton {"
            "    padding: 8px 20px;"
            "    font-size: 12px;"
            "    background: #666;"
            "    color: white;"
            "    border: none;"
            "    border-radius: 4px;"
            "}"
            "QPushButton:hover {"
            "    background: #555;"
            "}"
        )
        close_btn.clicked.connect(self._on_close)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)
    
    def _create_version_selector(self, parent_layout):
        """Create version selection UI."""
        selector_frame = QFrame()
        selector_frame.setStyleSheet(
            "QFrame {"
            "    background: #f5f5f5;"
            "    border: 1px solid #ddd;"
            "    border-radius: 5px;"
            "    padding: 10px;"
            "}"
        )
        selector_layout = QHBoxLayout()
        selector_frame.setLayout(selector_layout)
        
        # Version 1 selector
        selector_layout.addWidget(QLabel("Compare:"))
        
        self.version1_combo = QComboBox()
        self.version1_combo.setStyleSheet(
            "QComboBox {"
            "    padding: 5px 10px;"
            "    font-size: 11px;"
            "    border: 1px solid #ccc;"
            "    border-radius: 3px;"
            "    min-width: 100px;"
            "}"
        )
        self.version1_combo.currentIndexChanged.connect(self._on_version_changed)
        selector_layout.addWidget(self.version1_combo)
        
        selector_layout.addWidget(QLabel("with"))
        
        # Version 2 selector
        self.version2_combo = QComboBox()
        self.version2_combo.setStyleSheet(
            "QComboBox {"
            "    padding: 5px 10px;"
            "    font-size: 11px;"
            "    border: 1px solid #ccc;"
            "    border-radius: 3px;"
            "    min-width: 100px;"
            "}"
        )
        self.version2_combo.currentIndexChanged.connect(self._on_version_changed)
        selector_layout.addWidget(self.version2_combo)
        
        selector_layout.addStretch()
        
        # Compare button
        compare_btn = QPushButton("Compare Versions")
        compare_btn.setStyleSheet(
            "QPushButton {"
            "    padding: 6px 15px;"
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
        compare_btn.clicked.connect(self._on_compare_clicked)
        selector_layout.addWidget(compare_btn)
        
        parent_layout.addWidget(selector_frame)
    
    def _create_change_summary(self, parent_layout):
        """Create change summary display."""
        summary_frame = QFrame()
        summary_frame.setStyleSheet(
            "QFrame {"
            "    background: #fff;"
            "    border: 1px solid #ddd;"
            "    border-radius: 5px;"
            "    padding: 10px;"
            "}"
        )
        summary_layout = QHBoxLayout()
        summary_frame.setLayout(summary_layout)
        
        summary_layout.addWidget(QLabel("Changes:"))
        
        # Modified count (yellow)
        self.modified_label = QLabel("0 modified")
        self.modified_label.setStyleSheet(
            "padding: 3px 8px;"
            "background: #fff9c4;"
            "border: 1px solid #f9a825;"
            "border-radius: 3px;"
            "font-weight: bold;"
        )
        summary_layout.addWidget(self.modified_label)
        
        # Added count (green)
        self.added_label = QLabel("0 added")
        self.added_label.setStyleSheet(
            "padding: 3px 8px;"
            "background: #c8e6c9;"
            "border: 1px solid #4caf50;"
            "border-radius: 3px;"
            "font-weight: bold;"
        )
        summary_layout.addWidget(self.added_label)
        
        # Deleted count (red)
        self.deleted_label = QLabel("0 deleted")
        self.deleted_label.setStyleSheet(
            "padding: 3px 8px;"
            "background: #ffcdd2;"
            "border: 1px solid #f44336;"
            "border-radius: 3px;"
            "font-weight: bold;"
        )
        summary_layout.addWidget(self.deleted_label)
        
        summary_layout.addStretch()
        
        parent_layout.addWidget(summary_frame)
    
    def _create_comparison_display(self, parent_layout):
        """Create the main comparison display area."""
        # Scroll area for comparison results
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        # Container for comparison content
        scroll_content = QWidget()
        self.comparison_layout = QVBoxLayout()
        self.comparison_layout.setSpacing(10)
        scroll_content.setLayout(self.comparison_layout)
        scroll.setWidget(scroll_content)
        
        parent_layout.addWidget(scroll, stretch=1)
        
        # Initial message
        self.empty_label = QLabel(
            "Select two versions and click 'Compare Versions' to see differences."
        )
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(
            "padding: 50px; font-size: 13px; color: #999;"
        )
        self.comparison_layout.addWidget(self.empty_label)
    
    def load_versions(self):
        """Load available versions for the contract."""
        try:
            contract = self.storage.get_contract(self.contract_id)
            
            if not contract:
                logger.error("Contract not found: %s", self.contract_id)
                return
            
            # Populate version dropdowns
            for v in range(1, contract.current_version + 1):
                self.version1_combo.addItem(f"Version {v}", v)
                self.version2_combo.addItem(f"Version {v}", v)
            
            # Set default selection (compare latest with previous)
            if contract.current_version >= 2:
                self.version1_combo.setCurrentIndex(contract.current_version - 2)
                self.version2_combo.setCurrentIndex(contract.current_version - 1)
            
        except Exception as e:
            logger.error("Failed to load versions: %s", e)
    
    def _on_version_changed(self):
        """Handle version selection change."""
        # Clear comparison when versions change
        self._clear_comparison()
    
    def _on_compare_clicked(self):
        """Handle compare button click."""
        version1 = self.version1_combo.currentData()
        version2 = self.version2_combo.currentData()
        
        if version1 is None or version2 is None:
            logger.warning("No versions selected for comparison")
            return
        
        if version1 == version2:
            logger.warning("Cannot compare version with itself")
            return
        
        # Perform comparison
        self.compare_versions(version1, version2)
    
    def compare_versions(self, version1: int, version2: int):
        """
        Compare two versions and display results.
        
        Implements Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6.
        
        Args:
            version1: First version number
            version2: Second version number
        """
        logger.info("Comparing versions %d and %d", version1, version2)
        
        try:
            # Clear previous comparison
            self._clear_comparison()
            
            # Reconstruct both versions
            v1_data = self.version_manager.reconstruct_version(self.contract_id, version1)
            v2_data = self.version_manager.reconstruct_version(self.contract_id, version2)
            
            # Extract clauses
            v1_clauses = {c['clause_identifier']: c for c in v1_data['clauses']}
            v2_clauses = {c['clause_identifier']: c for c in v2_data['clauses']}
            
            # Get all unique clause identifiers
            all_identifiers = sorted(set(v1_clauses.keys()) | set(v2_clauses.keys()))
            
            # Track changes for summary
            modified_count = 0
            added_count = 0
            deleted_count = 0
            
            # Compare each clause
            for identifier in all_identifiers:
                v1_clause = v1_clauses.get(identifier)
                v2_clause = v2_clauses.get(identifier)
                
                # Determine change type
                if v1_clause and v2_clause:
                    # Both exist - check if modified
                    v1_content = v1_clause['content']
                    v2_content = v2_clause['content']
                    
                    similarity = self.comparator.calculate_text_similarity(v1_content, v2_content)
                    
                    if similarity < self.comparator.UNCHANGED_THRESHOLD:
                        # Modified (Requirement 6.3)
                        self._add_modified_clause(identifier, v1_content, v2_content)
                        modified_count += 1
                    # Skip unchanged clauses for cleaner display
                    
                elif v2_clause and not v1_clause:
                    # Added (Requirement 6.2)
                    self._add_added_clause(identifier, v2_clause['content'])
                    added_count += 1
                    
                elif v1_clause and not v2_clause:
                    # Deleted (Requirement 6.4)
                    self._add_deleted_clause(identifier, v1_clause['content'])
                    deleted_count += 1
            
            # Update summary (Requirement 6.6)
            self._update_summary(modified_count, added_count, deleted_count)
            
            logger.info(
                "Comparison complete: %d modified, %d added, %d deleted",
                modified_count, added_count, deleted_count
            )
            
        except Exception as e:
            logger.error("Failed to compare versions: %s", e)
            error_label = QLabel(f"Error comparing versions: {str(e)}")
            error_label.setStyleSheet("color: red; padding: 20px;")
            self.comparison_layout.addWidget(error_label)
    
    def _add_modified_clause(self, identifier: str, old_content: str, new_content: str):
        """
        Add a modified clause to the comparison display.
        
        Implements Requirements 6.3, 6.5: Yellow highlighting and text diff.
        """
        clause_frame = self._create_clause_frame(
            identifier,
            "MODIFIED",
            "#fff9c4",
            "#f9a825"
        )
        
        # Create text diff (Requirement 6.5)
        diff_widget = self._create_diff_widget(old_content, new_content)
        clause_frame.layout().addWidget(diff_widget)
        
        self.comparison_layout.addWidget(clause_frame)
    
    def _add_added_clause(self, identifier: str, content: str):
        """
        Add an added clause to the comparison display.
        
        Implements Requirement 6.2: Green highlighting for additions.
        """
        clause_frame = self._create_clause_frame(
            identifier,
            "ADDED",
            "#c8e6c9",
            "#4caf50"
        )
        
        # Display new content
        content_text = QTextEdit()
        content_text.setPlainText(content)
        content_text.setReadOnly(True)
        content_text.setMaximumHeight(150)
        content_text.setStyleSheet(
            "QTextEdit {"
            "    background: #e8f5e9;"
            "    border: 1px solid #4caf50;"
            "    border-radius: 3px;"
            "    padding: 5px;"
            "    font-size: 10px;"
            "}"
        )
        clause_frame.layout().addWidget(content_text)
        
        self.comparison_layout.addWidget(clause_frame)
    
    def _add_deleted_clause(self, identifier: str, content: str):
        """
        Add a deleted clause to the comparison display.
        
        Implements Requirement 6.4: Red highlighting for deletions.
        """
        clause_frame = self._create_clause_frame(
            identifier,
            "DELETED",
            "#ffcdd2",
            "#f44336"
        )
        
        # Display old content
        content_text = QTextEdit()
        content_text.setPlainText(content)
        content_text.setReadOnly(True)
        content_text.setMaximumHeight(150)
        content_text.setStyleSheet(
            "QTextEdit {"
            "    background: #ffebee;"
            "    border: 1px solid #f44336;"
            "    border-radius: 3px;"
            "    padding: 5px;"
            "    font-size: 10px;"
            "    text-decoration: line-through;"
            "}"
        )
        clause_frame.layout().addWidget(content_text)
        
        self.comparison_layout.addWidget(clause_frame)
    
    def _create_clause_frame(
        self,
        identifier: str,
        change_type: str,
        bg_color: str,
        border_color: str
    ) -> QFrame:
        """Create a frame for displaying a clause comparison."""
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{"
            f"    background: {bg_color};"
            f"    border: 2px solid {border_color};"
            f"    border-radius: 5px;"
            f"    padding: 10px;"
            f"}}"
        )
        
        layout = QVBoxLayout()
        frame.setLayout(layout)
        
        # Header with identifier and change type
        header_layout = QHBoxLayout()
        
        identifier_label = QLabel(identifier)
        identifier_label.setFont(QFont("Arial", 11, QFont.Bold))
        header_layout.addWidget(identifier_label)
        
        header_layout.addStretch()
        
        change_label = QLabel(change_type)
        change_label.setFont(QFont("Arial", 10, QFont.Bold))
        change_label.setStyleSheet(f"color: {border_color};")
        header_layout.addWidget(change_label)
        
        layout.addLayout(header_layout)
        
        return frame
    
    def _create_diff_widget(self, old_text: str, new_text: str) -> QWidget:
        """
        Create a widget displaying text diff with highlighting.
        
        Implements Requirement 6.5: Detailed text diff with highlighting.
        
        Args:
            old_text: Original text
            new_text: New text
            
        Returns:
            Widget containing the diff display
        """
        diff_widget = QWidget()
        diff_layout = QVBoxLayout()
        diff_widget.setLayout(diff_layout)
        
        # Create side-by-side text displays
        splitter = QSplitter(Qt.Horizontal)
        
        # Old version
        old_group = QGroupBox("Old Version")
        old_layout = QVBoxLayout()
        old_group.setLayout(old_layout)
        
        old_text_edit = QTextEdit()
        old_text_edit.setReadOnly(True)
        old_text_edit.setMaximumHeight(200)
        old_text_edit.setStyleSheet(
            "QTextEdit {"
            "    background: #fff;"
            "    border: 1px solid #ddd;"
            "    border-radius: 3px;"
            "    padding: 5px;"
            "    font-size: 10px;"
            "    font-family: monospace;"
            "}"
        )
        
        # Highlight differences in old text
        self._highlight_diff(old_text_edit, old_text, new_text, is_old=True)
        old_layout.addWidget(old_text_edit)
        splitter.addWidget(old_group)
        
        # New version
        new_group = QGroupBox("New Version")
        new_layout = QVBoxLayout()
        new_group.setLayout(new_layout)
        
        new_text_edit = QTextEdit()
        new_text_edit.setReadOnly(True)
        new_text_edit.setMaximumHeight(200)
        new_text_edit.setStyleSheet(
            "QTextEdit {"
            "    background: #fff;"
            "    border: 1px solid #ddd;"
            "    border-radius: 3px;"
            "    padding: 5px;"
            "    font-size: 10px;"
            "    font-family: monospace;"
            "}"
        )
        
        # Highlight differences in new text
        self._highlight_diff(new_text_edit, old_text, new_text, is_old=False)
        new_layout.addWidget(new_text_edit)
        splitter.addWidget(new_group)
        
        diff_layout.addWidget(splitter)
        
        return diff_widget
    
    def _highlight_diff(
        self,
        text_edit: QTextEdit,
        old_text: str,
        new_text: str,
        is_old: bool
    ):
        """
        Highlight differences in text using difflib.
        
        Implements Requirement 6.5: Text diff highlighting with HTML/CSS.
        
        Args:
            text_edit: QTextEdit widget to populate
            old_text: Original text
            new_text: New text
            is_old: True if highlighting old text, False for new text
        """
        # Generate HTML diff using difflib
        html_diff = self._generate_html_diff(old_text, new_text, is_old)
        
        # Set HTML content
        text_edit.setHtml(html_diff)
    
    def _generate_html_diff(self, old_text: str, new_text: str, is_old: bool) -> str:
        """
        Generate HTML diff with CSS styling.
        
        Implements Requirement 6.5: Use difflib to generate detailed text diffs
        and render with HTML/CSS highlighting.
        
        Args:
            old_text: Original text
            new_text: New text
            is_old: True for old version, False for new version
            
        Returns:
            HTML string with styled diff
        """
        # Split into words for word-level diff
        old_words = old_text.split()
        new_words = new_text.split()
        
        # Generate diff using difflib
        diff = list(difflib.ndiff(old_words, new_words))
        
        # Build HTML with CSS styling
        html_parts = [
            '<html><head><style>',
            '.deleted { background-color: #ffcdd2; padding: 2px 4px; border-radius: 2px; }',
            '.added { background-color: #c8e6c9; padding: 2px 4px; border-radius: 2px; }',
            '.unchanged { color: #333; }',
            'body { font-family: monospace; font-size: 10pt; line-height: 1.6; }',
            '</style></head><body>'
        ]
        
        for token in diff:
            if token.startswith('- '):
                # Deleted word - show only in old version
                if is_old:
                    word = token[2:]
                    html_parts.append(f'<span class="deleted">{self._escape_html(word)}</span> ')
            elif token.startswith('+ '):
                # Added word - show only in new version
                if not is_old:
                    word = token[2:]
                    html_parts.append(f'<span class="added">{self._escape_html(word)}</span> ')
            elif token.startswith('  '):
                # Unchanged word - show in both versions
                word = token[2:]
                html_parts.append(f'<span class="unchanged">{self._escape_html(word)}</span> ')
        
        html_parts.append('</body></html>')
        
        return ''.join(html_parts)
    
    def _escape_html(self, text: str) -> str:
        """
        Escape HTML special characters.
        
        Args:
            text: Text to escape
            
        Returns:
            HTML-escaped text
        """
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))
    
    def _update_summary(self, modified: int, added: int, deleted: int):
        """
        Update the change summary display.
        
        Implements Requirement 6.6: Change summary with counts.
        """
        self.modified_label.setText(f"{modified} modified")
        self.added_label.setText(f"{added} added")
        self.deleted_label.setText(f"{deleted} deleted")
    
    def _clear_comparison(self):
        """Clear the comparison display."""
        # Remove all widgets from comparison layout
        while self.comparison_layout.count() > 0:
            item = self.comparison_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add empty message
        self.empty_label = QLabel(
            "Select two versions and click 'Compare Versions' to see differences."
        )
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(
            "padding: 50px; font-size: 13px; color: #999;"
        )
        self.comparison_layout.addWidget(self.empty_label)
    
    def _on_close(self):
        """Handle close button click."""
        self.comparison_closed.emit()
        self.close()
