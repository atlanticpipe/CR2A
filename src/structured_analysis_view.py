"""
Structured Analysis View - Schema-based collapsible display

This module provides a structured, collapsible view of contract analysis results
that matches the output_schemas_v1.json structure. It automatically hides empty
sections and provides expand/collapse functionality for all levels.
"""

import logging
from typing import Dict, Any, Optional, List
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QTextEdit
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class CollapsibleSection(QFrame):
    """A collapsible section widget with expand/collapse functionality."""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.is_collapsed = False
        self.content_widget = None
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header with toggle button
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QFrame:hover {
                background-color: #e8e8e8;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 8, 10, 8)
        
        # Toggle button
        self.toggle_btn = QPushButton("▼")
        self.toggle_btn.setFixedSize(20, 20)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle)
        header_layout.addWidget(self.toggle_btn)
        
        # Title label
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        # Make header clickable
        header.mousePressEvent = lambda e: self.toggle()
        
        layout.addWidget(header)
        
        # Content container
        self.content_container = QFrame()
        self.content_container.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-top: none;
                border-radius: 0 0 4px 4px;
            }
        """)
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(15, 10, 15, 10)
        
        layout.addWidget(self.content_container)
        
        self.setFrameStyle(QFrame.NoFrame)
    
    def set_content(self, widget: QWidget):
        """Set the content widget for this section."""
        # Clear existing content
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.content_widget = widget
        self.content_layout.addWidget(widget)
    
    def toggle(self):
        """Toggle the collapsed state."""
        self.is_collapsed = not self.is_collapsed
        self.content_container.setVisible(not self.is_collapsed)
        self.toggle_btn.setText("▶" if self.is_collapsed else "▼")
    
    def collapse(self):
        """Collapse the section."""
        if not self.is_collapsed:
            self.toggle()
    
    def expand(self):
        """Expand the section."""
        if self.is_collapsed:
            self.toggle()


class StructuredAnalysisView(QWidget):
    """
    Structured view of contract analysis results based on output_schemas_v1.json.
    
    Displays analysis results in a hierarchical, collapsible structure that matches
    the schema. Automatically hides empty sections and provides expand/collapse
    functionality at all levels.
    """
    
    # Section display names and icons
    SECTION_INFO = {
        "contract_overview": ("📄 Contract Overview", "#e3f2fd"),
        "administrative_and_commercial_terms": ("💼 Administrative & Commercial Terms", "#fff3e0"),
        "technical_and_performance_terms": ("⚙️ Technical & Performance Terms", "#f3e5f5"),
        "legal_risk_and_enforcement": ("⚖️ Legal, Risk & Enforcement", "#ffebee"),
        "regulatory_and_compliance_terms": ("📋 Regulatory & Compliance Terms", "#e8f5e9"),
        "data_technology_and_deliverables": ("💾 Data, Technology & Deliverables", "#e0f2f1"),
        "supplemental_operational_risks": ("⚠️ Supplemental Operational Risks", "#fff9c4"),
        "final_analysis": ("📊 Final Analysis", "#f5f5f5")
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.analysis_data = None
        self.sections = {}
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        # Content widget
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(10)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        
        scroll.setWidget(self.content_widget)
        main_layout.addWidget(scroll)
        
        # Control buttons
        controls = QHBoxLayout()
        
        expand_all_btn = QPushButton("Expand All")
        expand_all_btn.clicked.connect(self.expand_all)
        controls.addWidget(expand_all_btn)
        
        collapse_all_btn = QPushButton("Collapse All")
        collapse_all_btn.clicked.connect(self.collapse_all)
        controls.addWidget(collapse_all_btn)
        
        collapse_empty_btn = QPushButton("Collapse Empty")
        collapse_empty_btn.clicked.connect(self.collapse_empty_sections)
        controls.addWidget(collapse_empty_btn)
        
        controls.addStretch()
        
        main_layout.addLayout(controls)
    
    def display_analysis(self, analysis_result):
        """Display analysis results in structured format."""
        # Clear existing content
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.sections = {}
        
        # Convert analysis result to dict if needed
        if hasattr(analysis_result, 'to_dict'):
            self.analysis_data = analysis_result.to_dict()
        elif hasattr(analysis_result, '__dict__'):
            self.analysis_data = analysis_result.__dict__
        else:
            self.analysis_data = analysis_result
        
        # Display each section
        for section_key, (section_title, bg_color) in self.SECTION_INFO.items():
            if section_key in self.analysis_data:
                section_data = self.analysis_data[section_key]
                
                # Skip if section is empty
                if not section_data or (isinstance(section_data, dict) and not any(section_data.values())):
                    continue
                
                section_widget = self._create_section(section_key, section_title, section_data, bg_color)
                if section_widget:
                    self.sections[section_key] = section_widget
                    self.content_layout.addWidget(section_widget)
        
        self.content_layout.addStretch()
        
        # Auto-collapse empty sections
        self.collapse_empty_sections()
    
    def _create_section(self, section_key: str, title: str, data: Any, bg_color: str) -> Optional[CollapsibleSection]:
        """Create a collapsible section for the given data."""
        if not data:
            return None
        
        section = CollapsibleSection(title)
        
        # Create content based on section type
        if section_key == "contract_overview":
            content = self._create_overview_content(data)
        elif section_key == "final_analysis":
            content = self._create_final_analysis_content(data)
        elif isinstance(data, dict):
            content = self._create_clause_section_content(data)
        else:
            content = self._create_simple_content(data)
        
        if content:
            section.set_content(content)
            return section
        
        return None
    
    def _create_overview_content(self, data: Dict[str, Any]) -> QWidget:
        """Create content for contract overview section."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Display each field
        for key, value in data.items():
            if value:
                field_widget = QFrame()
                field_widget.setStyleSheet("""
                    QFrame {
                        background-color: #fafafa;
                        border: 1px solid #e0e0e0;
                        border-radius: 3px;
                        padding: 8px;
                    }
                """)
                field_layout = QVBoxLayout(field_widget)
                field_layout.setSpacing(4)
                field_layout.setContentsMargins(8, 8, 8, 8)
                
                # Field name
                name_label = QLabel(key)
                name_label.setStyleSheet("font-weight: bold; color: #555;")
                field_layout.addWidget(name_label)
                
                # Field value
                value_label = QLabel(str(value))
                value_label.setWordWrap(True)
                value_label.setStyleSheet("color: #333;")
                field_layout.addWidget(value_label)
                
                layout.addWidget(field_widget)
        
        return widget
    
    def _create_clause_section_content(self, data: Dict[str, Any]) -> QWidget:
        """Create content for clause sections (administrative, technical, etc.)."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create subsection for each clause type
        for clause_name, clause_data in data.items():
            if not clause_data or not isinstance(clause_data, dict):
                continue
            
            # Check if clause has any content
            has_content = any(clause_data.values())
            if not has_content:
                continue
            
            subsection = CollapsibleSection(clause_name)
            subsection_content = self._create_clause_block_content(clause_data)
            
            if subsection_content:
                subsection.set_content(subsection_content)
                layout.addWidget(subsection)
        
        return widget if layout.count() > 0 else None
    
    def _create_clause_block_content(self, data: Dict[str, Any]) -> Optional[QWidget]:
        """Create content for a single clause block."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)
        
        has_content = False
        
        # Display each field in the clause block
        for key, value in data.items():
            if not value:
                continue
            
            has_content = True
            
            field_frame = QFrame()
            field_frame.setStyleSheet("""
                QFrame {
                    background-color: #f9f9f9;
                    border-left: 3px solid #2196F3;
                    padding: 8px;
                }
            """)
            field_layout = QVBoxLayout(field_frame)
            field_layout.setSpacing(5)
            
            # Field name
            name_label = QLabel(key)
            name_label.setStyleSheet("font-weight: bold; color: #1976D2; font-size: 12px;")
            field_layout.addWidget(name_label)
            
            # Field value
            if isinstance(value, list):
                for item in value:
                    item_label = QLabel(f"• {str(item)}")
                    item_label.setWordWrap(True)
                    item_label.setStyleSheet("color: #333; margin-left: 10px;")
                    field_layout.addWidget(item_label)
            else:
                value_label = QLabel(str(value))
                value_label.setWordWrap(True)
                value_label.setStyleSheet("color: #333;")
                field_layout.addWidget(value_label)
            
            layout.addWidget(field_frame)
        
        return widget if has_content else None
    
    def _create_final_analysis_content(self, data: Any) -> QWidget:
        """Create content for final analysis section."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(str(data))
        text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #fafafa;
                border: 1px solid #e0e0e0;
                border-radius: 3px;
                padding: 10px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
            }
        """)
        text_edit.setMinimumHeight(100)
        
        layout.addWidget(text_edit)
        return widget
    
    def _create_simple_content(self, data: Any) -> QWidget:
        """Create simple content display for non-structured data."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel(str(data))
        label.setWordWrap(True)
        label.setStyleSheet("padding: 10px; background-color: #fafafa; border-radius: 3px;")
        
        layout.addWidget(label)
        return widget
    
    def expand_all(self):
        """Expand all sections."""
        for section in self.sections.values():
            section.expand()
            # Also expand subsections
            self._expand_subsections(section)
    
    def collapse_all(self):
        """Collapse all sections."""
        for section in self.sections.values():
            section.collapse()
    
    def collapse_empty_sections(self):
        """Collapse sections that have no meaningful content."""
        for section_key, section in self.sections.items():
            if self._is_section_empty(section_key):
                section.collapse()
    
    def _expand_subsections(self, parent_widget: QWidget):
        """Recursively expand all subsections within a widget."""
        for child in parent_widget.findChildren(CollapsibleSection):
            child.expand()
    
    def _is_section_empty(self, section_key: str) -> bool:
        """Check if a section has meaningful content."""
        if section_key not in self.analysis_data:
            return True
        
        data = self.analysis_data[section_key]
        
        if not data:
            return True
        
        if isinstance(data, dict):
            # Check if all values are empty
            return not any(data.values())
        
        return False
