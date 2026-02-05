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
    
    Uses a template-based approach where all sections and categories are pre-created
    in __init__, then filled with data when display_analysis() is called. This ensures
    all sections and categories are always visible, with empty ones auto-minimized.
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
        self.category_boxes = {}  # Maps "section_key.category_name" to CollapsibleSection widget
        
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
        
        # Build the complete UI template with all sections and categories
        self._build_template()
    
    def _build_template(self):
        """
        Build the complete UI template with all sections and categories.
        
        This creates all 6 main sections and pre-creates category boxes for all
        possible categories. The boxes are stored in self.category_boxes for
        later data filling.
        """
        from src.schema_completer import SchemaCompleter
        
        logger.info("Building template with all sections and categories")
        
        # Create sections in order (excluding contract_overview, supplemental_operational_risks, and final_analysis for now)
        clause_sections = [
            "administrative_and_commercial_terms",
            "technical_and_performance_terms",
            "legal_risk_and_enforcement",
            "regulatory_and_compliance_terms",
            "data_technology_and_deliverables"
        ]
        
        # Create contract overview section (special handling - no categories)
        section_key = "contract_overview"
        if section_key in self.SECTION_INFO:
            title, bg_color = self.SECTION_INFO[section_key]
            section = CollapsibleSection(title)
            
            # Create empty content widget for overview
            content = QWidget()
            content_layout = QVBoxLayout(content)
            content_layout.setSpacing(8)
            content_layout.setContentsMargins(0, 0, 0, 0)
            
            # Store reference for later filling
            section.content_widget_layout = content_layout
            section.set_content(content)
            
            self.sections[section_key] = section
            self.content_layout.addWidget(section)
            logger.debug(f"Created section: {section_key}")
        
        # Create clause sections with all categories
        for section_key in clause_sections:
            if section_key not in self.SECTION_INFO:
                continue
                
            title, bg_color = self.SECTION_INFO[section_key]
            section = CollapsibleSection(title)
            
            # Create container for category boxes
            section_content = QWidget()
            section_content_layout = QVBoxLayout(section_content)
            section_content_layout.setSpacing(5)
            section_content_layout.setContentsMargins(0, 0, 0, 0)
            
            # Get categories for this section
            categories = self._get_categories_for_section(section_key)
            logger.debug(f"Section {section_key} has {len(categories)} categories")
            
            # Create a category box for each category
            for category_name in categories:
                category_box = self._create_category_box(category_name)
                box_key = f"{section_key}.{category_name}"
                self.category_boxes[box_key] = category_box
                section_content_layout.addWidget(category_box)
            
            section.set_content(section_content)
            self.sections[section_key] = section
            self.content_layout.addWidget(section)
            logger.debug(f"Created section: {section_key} with {len(categories)} category boxes")
        
        # Create supplemental operational risks section (special handling - list of risks)
        section_key = "supplemental_operational_risks"
        if section_key in self.SECTION_INFO:
            title, bg_color = self.SECTION_INFO[section_key]
            section = CollapsibleSection(title)
            
            # Create empty content widget for risks
            content = QWidget()
            content_layout = QVBoxLayout(content)
            content_layout.setSpacing(5)
            content_layout.setContentsMargins(0, 0, 0, 0)
            
            # Store reference for later filling
            section.content_widget_layout = content_layout
            section.set_content(content)
            
            self.sections[section_key] = section
            self.content_layout.addWidget(section)
            logger.debug(f"Created section: {section_key}")
        
        # Create final analysis section (special handling - text content)
        section_key = "final_analysis"
        if section_key in self.SECTION_INFO:
            title, bg_color = self.SECTION_INFO[section_key]
            section = CollapsibleSection(title)
            
            # Create empty content widget for final analysis
            content = QWidget()
            content_layout = QVBoxLayout(content)
            content_layout.setContentsMargins(0, 0, 0, 0)
            
            # Store reference for later filling
            section.content_widget_layout = content_layout
            section.set_content(content)
            
            self.sections[section_key] = section
            self.content_layout.addWidget(section)
            logger.debug(f"Created section: {section_key}")
        
        # Add stretch at the end
        self.content_layout.addStretch()
        
        logger.info(f"Template built: {len(self.sections)} sections, {len(self.category_boxes)} category boxes")
    
    def _get_categories_for_section(self, section_key: str) -> List[str]:
        """
        Get list of all categories for a section from SchemaCompleter.
        
        Args:
            section_key: The section key (e.g., "administrative_and_commercial_terms")
            
        Returns:
            List of category names for this section
        """
        from src.schema_completer import SchemaCompleter
        
        if section_key == "administrative_and_commercial_terms":
            return SchemaCompleter.ADMINISTRATIVE_CATEGORIES
        elif section_key == "technical_and_performance_terms":
            return SchemaCompleter.TECHNICAL_CATEGORIES
        elif section_key == "legal_risk_and_enforcement":
            return SchemaCompleter.LEGAL_CATEGORIES
        elif section_key == "regulatory_and_compliance_terms":
            return SchemaCompleter.REGULATORY_CATEGORIES
        elif section_key == "data_technology_and_deliverables":
            return SchemaCompleter.DATA_TECH_CATEGORIES
        else:
            return []
    
    def _create_category_box(self, category_name: str) -> CollapsibleSection:
        """
        Create an empty category box that will be filled with data later.
        
        Args:
            category_name: The name of the category
            
        Returns:
            CollapsibleSection widget with empty content
        """
        box = CollapsibleSection(category_name)
        
        # Pre-create empty content widget with placeholders
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(10)
        content_layout.setContentsMargins(5, 5, 5, 5)
        
        # Store reference to layout for later filling
        box.content_widget_layout = content_layout
        box.is_empty = True  # Flag to track if box has content
        
        box.set_content(content)
        return box
    
    def display_analysis(self, analysis_result):
        """
        Display analysis results using the pre-built template.
        
        This method fills the pre-created category boxes with data from the
        analysis result, then auto-minimizes empty boxes.
        
        Args:
            analysis_result: Can be ComprehensiveAnalysisResult, VerifiedAnalysisResult, or dict
        """
        logger.info("Displaying analysis using template-based approach")
        
        # Clear all boxes first
        self._clear_all_boxes()
        
        # Extract result dict from analysis_result
        result_dict = self._extract_result_dict(analysis_result)
        
        if not result_dict:
            logger.warning("No analysis data to display")
            return
        
        logger.info(f"Extracted result dict with {len(result_dict)} sections: {list(result_dict.keys())}")
        
        # Fill category boxes with data
        for section_key in ["administrative_and_commercial_terms", "technical_and_performance_terms",
                           "legal_risk_and_enforcement", "regulatory_and_compliance_terms",
                           "data_technology_and_deliverables"]:
            if section_key in result_dict:
                section_data = result_dict[section_key]
                if isinstance(section_data, dict):
                    for category_name, clause_data in section_data.items():
                        box_key = f"{section_key}.{category_name}"
                        if box_key in self.category_boxes:
                            self._fill_category_box(self.category_boxes[box_key], clause_data)
                            logger.debug(f"Filled box: {box_key}")
        
        # Handle special sections (contract_overview, supplemental_operational_risks, final_analysis)
        self._fill_contract_overview(result_dict.get('contract_overview'))
        self._fill_supplemental_risks(result_dict.get('supplemental_operational_risks'))
        self._fill_final_analysis(result_dict.get('final_analysis'))
        
        # Auto-minimize empty boxes
        self._auto_minimize_empty_boxes()
        
        logger.info("Display complete")
    
    def _fill_contract_overview(self, overview_data: Any):
        """
        Fill the contract overview section with data.
        
        Args:
            overview_data: Contract overview data (dict or ContractOverview object)
        """
        if not overview_data:
            logger.debug("No contract overview data to display")
            return
        
        section = self.sections.get('contract_overview')
        if not section or not hasattr(section, 'content_widget_layout'):
            logger.warning("Contract overview section not found or not properly initialized")
            return
        
        # Convert to dict if needed
        if hasattr(overview_data, 'to_dict'):
            overview_data = overview_data.to_dict()
        
        if not isinstance(overview_data, dict):
            logger.warning(f"Contract overview data is not a dict: {type(overview_data)}")
            return
        
        logger.info(f"Filling contract overview with {len(overview_data)} fields")
        
        # Display each field
        for key, value in overview_data.items():
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
                
                # Field name (convert snake_case to Title Case)
                display_name = key.replace('_', ' ').title()
                name_label = QLabel(display_name)
                name_label.setStyleSheet("font-weight: bold; color: #555;")
                field_layout.addWidget(name_label)
                
                # Field value
                value_label = QLabel(str(value))
                value_label.setWordWrap(True)
                value_label.setStyleSheet("color: #333;")
                field_layout.addWidget(value_label)
                
                section.content_widget_layout.addWidget(field_widget)
        
        # Expand the section since it has content
        section.expand()
        logger.debug("Contract overview section filled and expanded")
    
    def _fill_supplemental_risks(self, risks_data: Any):
        """
        Fill the supplemental operational risks section with data.
        
        Args:
            risks_data: List of supplemental risks
        """
        if not risks_data:
            logger.debug("No supplemental risks data to display")
            return
        
        section = self.sections.get('supplemental_operational_risks')
        if not section or not hasattr(section, 'content_widget_layout'):
            logger.warning("Supplemental risks section not found or not properly initialized")
            return
        
        # Convert to list if needed
        if not isinstance(risks_data, list):
            logger.warning(f"Supplemental risks data is not a list: {type(risks_data)}")
            return
        
        logger.info(f"Filling supplemental risks with {len(risks_data)} items")
        
        # Display each risk
        for i, risk in enumerate(risks_data, 1):
            # Convert to dict if needed
            if hasattr(risk, 'to_dict'):
                risk = risk.to_dict()
            
            risk_widget = QFrame()
            risk_widget.setStyleSheet("""
                QFrame {
                    background-color: #fff9e6;
                    border-left: 3px solid #ff9800;
                    padding: 10px;
                    margin-bottom: 5px;
                }
            """)
            risk_layout = QVBoxLayout(risk_widget)
            risk_layout.setSpacing(5)
            
            # Risk number
            number_label = QLabel(f"Risk #{i}")
            number_label.setStyleSheet("font-weight: bold; color: #f57c00;")
            risk_layout.addWidget(number_label)
            
            # Risk details
            if isinstance(risk, dict):
                for key, value in risk.items():
                    if value:
                        detail_label = QLabel(f"{key.replace('_', ' ').title()}: {value}")
                        detail_label.setWordWrap(True)
                        detail_label.setStyleSheet("color: #333;")
                        risk_layout.addWidget(detail_label)
            else:
                risk_label = QLabel(str(risk))
                risk_label.setWordWrap(True)
                risk_label.setStyleSheet("color: #333;")
                risk_layout.addWidget(risk_label)
            
            section.content_widget_layout.addWidget(risk_widget)
        
        # Expand the section since it has content
        section.expand()
        logger.debug("Supplemental risks section filled and expanded")
    
    def _fill_final_analysis(self, analysis_data: Any):
        """
        Fill the final analysis section with data.
        
        Args:
            analysis_data: Final analysis text or data
        """
        if not analysis_data:
            logger.debug("No final analysis data to display")
            return
        
        section = self.sections.get('final_analysis')
        if not section or not hasattr(section, 'content_widget_layout'):
            logger.warning("Final analysis section not found or not properly initialized")
            return
        
        logger.info("Filling final analysis section")
        
        # Create text edit for final analysis
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(str(analysis_data))
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
        text_edit.setMinimumHeight(150)
        
        section.content_widget_layout.addWidget(text_edit)
        
        # Expand the section since it has content
        section.expand()
        logger.debug("Final analysis section filled and expanded")
    
    def _extract_result_dict(self, analysis_result) -> Dict[str, Any]:
        """
        Extract a dictionary from various analysis result formats.
        
        Handles:
        - ComprehensiveAnalysisResult
        - VerifiedAnalysisResult (extracts base_result)
        - AnalysisResult (legacy format)
        - Dict (pass through)
        
        Args:
            analysis_result: The analysis result in any supported format
            
        Returns:
            Dictionary with section keys and clause data
        """
        result_dict = {}
        
        # Check if this is a VerifiedAnalysisResult with base_result
        if hasattr(analysis_result, 'base_result') and hasattr(analysis_result, 'get_base_result'):
            logger.debug("Processing VerifiedAnalysisResult - extracting base_result")
            try:
                # Get the ComprehensiveAnalysisResult from the VerifiedAnalysisResult
                base = analysis_result.get_base_result()
                logger.debug("Successfully extracted ComprehensiveAnalysisResult from VerifiedAnalysisResult")
                
                # Now process it as a ComprehensiveAnalysisResult
                return self._extract_from_comprehensive_result(base)
                    
            except Exception as e:
                logger.error(f"Error extracting base_result from VerifiedAnalysisResult: {e}", exc_info=True)
                # Fall back to trying to use the dict directly
                base = analysis_result.base_result
                if isinstance(base, dict):
                    return base
        
        # Check if it's a ComprehensiveAnalysisResult
        elif hasattr(analysis_result, 'contract_overview'):
            logger.debug("Processing ComprehensiveAnalysisResult")
            return self._extract_from_comprehensive_result(analysis_result)
        
        # Fallback: try to_dict if available
        elif hasattr(analysis_result, 'to_dict'):
            try:
                result_dict = analysis_result.to_dict()
                logger.debug(f"Converted analysis result to dict with keys: {list(result_dict.keys())}")
                return result_dict
            except Exception as e:
                logger.error(f"Error calling to_dict(): {e}")
                # Try __dict__ as fallback
                if hasattr(analysis_result, '__dict__'):
                    return analysis_result.__dict__
        elif hasattr(analysis_result, '__dict__'):
            logger.debug("Using __dict__")
            return analysis_result.__dict__
        elif isinstance(analysis_result, dict):
            logger.debug("Using dict directly")
            return analysis_result
        
        logger.warning("Could not extract result dict from analysis_result")
        return {}
    
    def _extract_from_comprehensive_result(self, result) -> Dict[str, Any]:
        """
        Extract dictionary from ComprehensiveAnalysisResult.
        
        Args:
            result: ComprehensiveAnalysisResult object
            
        Returns:
            Dictionary with all sections converted to dict format
        """
        result_dict = {}
        
        # Add each section if it exists and is not None
        if hasattr(result, 'contract_overview') and result.contract_overview:
            result_dict['contract_overview'] = result.contract_overview.to_dict() if hasattr(result.contract_overview, 'to_dict') else result.contract_overview
        
        if hasattr(result, 'administrative_and_commercial_terms') and result.administrative_and_commercial_terms:
            result_dict['administrative_and_commercial_terms'] = result.administrative_and_commercial_terms.to_dict() if hasattr(result.administrative_and_commercial_terms, 'to_dict') else result.administrative_and_commercial_terms
        
        if hasattr(result, 'technical_and_performance_terms') and result.technical_and_performance_terms:
            result_dict['technical_and_performance_terms'] = result.technical_and_performance_terms.to_dict() if hasattr(result.technical_and_performance_terms, 'to_dict') else result.technical_and_performance_terms
        
        if hasattr(result, 'legal_risk_and_enforcement') and result.legal_risk_and_enforcement:
            result_dict['legal_risk_and_enforcement'] = result.legal_risk_and_enforcement.to_dict() if hasattr(result.legal_risk_and_enforcement, 'to_dict') else result.legal_risk_and_enforcement
        
        if hasattr(result, 'regulatory_and_compliance_terms') and result.regulatory_and_compliance_terms:
            result_dict['regulatory_and_compliance_terms'] = result.regulatory_and_compliance_terms.to_dict() if hasattr(result.regulatory_and_compliance_terms, 'to_dict') else result.regulatory_and_compliance_terms
        
        if hasattr(result, 'data_technology_and_deliverables') and result.data_technology_and_deliverables:
            result_dict['data_technology_and_deliverables'] = result.data_technology_and_deliverables.to_dict() if hasattr(result.data_technology_and_deliverables, 'to_dict') else result.data_technology_and_deliverables
        
        if hasattr(result, 'supplemental_operational_risks') and result.supplemental_operational_risks:
            result_dict['supplemental_operational_risks'] = [r.to_dict() if hasattr(r, 'to_dict') else r for r in result.supplemental_operational_risks]
        
        if hasattr(result, 'final_analysis') and result.final_analysis:
            result_dict['final_analysis'] = result.final_analysis
        
        return result_dict
    
    def _clear_all_boxes(self):
        """
        Clear all category boxes to prepare for new data.
        
        Iterates through all pre-created category boxes and clears their content,
        resetting them to empty state.
        """
        logger.debug(f"Clearing {len(self.category_boxes)} category boxes")
        
        for box_key, box in self.category_boxes.items():
            # Clear the content layout
            if hasattr(box, 'content_widget_layout'):
                while box.content_widget_layout.count():
                    child = box.content_widget_layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
            
            # Reset is_empty flag
            box.is_empty = True
    
    def _fill_category_box(self, box: CollapsibleSection, clause_data: Any):
        """
        Fill a category box with clause data.
        
        Handles three cases:
        1. None/empty data - leave box empty
        2. "Not found" clause - show warning message
        3. Found clause - show full details
        
        Args:
            box: The CollapsibleSection widget to fill
            clause_data: The clause data (dict, ClauseBlock, or None)
        """
        # Check if clause_data is None/empty
        if not clause_data:
            box.is_empty = True
            return
        
        # Convert to dict if needed
        if hasattr(clause_data, 'to_dict'):
            clause_data = clause_data.to_dict()
        
        if not isinstance(clause_data, dict):
            box.is_empty = True
            return
        
        # Check if this is a "Not found" clause
        if self._is_not_found_clause(clause_data):
            # Display "Not found" message
            not_found_frame = QFrame()
            not_found_frame.setStyleSheet("""
                QFrame {
                    background-color: #f5f5f5;
                    border-left: 3px solid #999;
                    padding: 8px;
                }
            """)
            not_found_layout = QVBoxLayout(not_found_frame)
            
            not_found_label = QLabel("⚠️ Not found in contract")
            not_found_label.setStyleSheet("font-style: italic; color: #666; font-size: 11px;")
            not_found_layout.addWidget(not_found_label)
            
            box.content_widget_layout.addWidget(not_found_frame)
            box.is_empty = True  # Treat "not found" as empty for minimization
        else:
            # Display full clause details
            content = self._create_clause_block_content(clause_data)
            if content:
                box.content_widget_layout.addWidget(content)
                box.is_empty = False
            else:
                box.is_empty = True
    
    def _is_not_found_clause(self, clause_data: Dict[str, Any]) -> bool:
        """
        Check if a clause is marked as "Not found".
        
        Args:
            clause_data: Dictionary containing clause data
            
        Returns:
            True if clause is "Not found", False otherwise
        """
        clause_language = clause_data.get('Clause Language') or clause_data.get('clause_language', '')
        clause_summary = clause_data.get('Clause Summary') or clause_data.get('clause_summary', '')
        
        return (str(clause_language).strip().lower() == 'not found' or 
                str(clause_summary).strip().lower() == 'not found')
    
    def _auto_minimize_empty_boxes(self):
        """
        Auto-minimize all empty category boxes.
        
        Collapses boxes where is_empty is True, leaving found boxes expanded.
        """
        empty_count = 0
        found_count = 0
        
        for box_key, box in self.category_boxes.items():
            if box.is_empty:
                box.collapse()
                empty_count += 1
            else:
                box.expand()
                found_count += 1
        
        logger.info(f"Auto-minimized {empty_count} empty boxes, {found_count} boxes have content")
    
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
            
            # Check if clause has any content OR if it's a "not found" clause
            clause_language = clause_data.get('Clause Language') or clause_data.get('clause_language', '')
            clause_summary = clause_data.get('Clause Summary') or clause_data.get('clause_summary', '')
            is_not_found = (str(clause_language).strip().lower() == 'not found' or 
                           str(clause_summary).strip().lower() == 'not found')
            has_content = any(clause_data.values()) or is_not_found
            
            if not has_content:
                continue
            
            subsection = CollapsibleSection(clause_name)
            subsection_content = self._create_clause_block_content(clause_data)
            
            if subsection_content:
                subsection.set_content(subsection_content)
                layout.addWidget(subsection)
        
        return widget if layout.count() > 0 else None
    
    def _create_clause_block_content(self, data: Dict[str, Any]) -> Optional[QWidget]:
        """Create content for a single clause block with all 6 required fields."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Check if this is a "Not found" clause
        clause_language = data.get('Clause Language') or data.get('clause_language', '')
        clause_summary = data.get('Clause Summary') or data.get('clause_summary', '')
        is_not_found = (str(clause_language).strip().lower() == 'not found' or 
                       str(clause_summary).strip().lower() == 'not found')
        
        # If not found, show a simple message
        if is_not_found:
            not_found_frame = QFrame()
            not_found_frame.setStyleSheet("""
                QFrame {
                    background-color: #f5f5f5;
                    border-left: 3px solid #999;
                    padding: 8px;
                }
            """)
            not_found_layout = QVBoxLayout(not_found_frame)
            
            not_found_label = QLabel("⚠️ Not found in contract")
            not_found_label.setStyleSheet("font-style: italic; color: #666; font-size: 11px;")
            not_found_layout.addWidget(not_found_label)
            
            layout.addWidget(not_found_frame)
            return widget
        
        # Define all 6 required fields in order with their display names
        required_fields = [
            ('Clause Language', 'clause_language', 'Clause Language'),
            ('Clause Summary', 'clause_summary', 'Clause Summary (BLUF)'),
            ('Risk Triggers Identified', 'risk_triggers_identified', 'Risk Triggers Identified'),
            ('Flow-Down Obligations', 'flow_down_obligations', 'Flow-Down Obligations'),
            ('Redline Recommendations', 'redline_recommendations', 'Redline Recommendations'),
            ('Harmful Language / Policy Conflicts', 'harmful_language_policy_conflicts', 'Harmful Language / Policy Conflicts')
        ]
        
        # Display all 6 fields in order
        for title_case_key, snake_case_key, display_name in required_fields:
            # Try both naming conventions
            value = data.get(title_case_key) or data.get(snake_case_key)
            
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
            name_label = QLabel(display_name)
            name_label.setStyleSheet("font-weight: bold; color: #1976D2; font-size: 12px;")
            field_layout.addWidget(name_label)
            
            # Field value - always show something, even if empty
            if not value:
                # Show empty state
                empty_label = QLabel("(None)")
                empty_label.setStyleSheet("color: #999; font-style: italic;")
                field_layout.addWidget(empty_label)
            elif isinstance(value, list):
                if len(value) == 0:
                    # Empty list
                    empty_label = QLabel("(No items)")
                    empty_label.setStyleSheet("color: #999; font-style: italic;")
                    field_layout.addWidget(empty_label)
                else:
                    # Display list items
                    for item in value:
                        # Handle dict items (like redline recommendations)
                        if isinstance(item, dict):
                            item_text = ""
                            for k, v in item.items():
                                item_text += f"{k}: {v}\n"
                            item_label = QLabel(f"• {item_text.strip()}")
                        else:
                            item_label = QLabel(f"• {str(item)}")
                        item_label.setWordWrap(True)
                        item_label.setStyleSheet("color: #333; margin-left: 10px;")
                        field_layout.addWidget(item_label)
            elif isinstance(value, dict):
                # Handle nested dict
                if len(value) == 0:
                    empty_label = QLabel("(No items)")
                    empty_label.setStyleSheet("color: #999; font-style: italic;")
                    field_layout.addWidget(empty_label)
                else:
                    for k, v in value.items():
                        item_label = QLabel(f"{k}: {str(v)}")
                        item_label.setWordWrap(True)
                        item_label.setStyleSheet("color: #333; margin-left: 10px;")
                        field_layout.addWidget(item_label)
            elif isinstance(value, str):
                if value.strip() == "":
                    empty_label = QLabel("(None)")
                    empty_label.setStyleSheet("color: #999; font-style: italic;")
                    field_layout.addWidget(empty_label)
                else:
                    value_label = QLabel(str(value))
                    value_label.setWordWrap(True)
                    value_label.setStyleSheet("color: #333;")
                    field_layout.addWidget(value_label)
            else:
                # Other types
                value_label = QLabel(str(value))
                value_label.setWordWrap(True)
                value_label.setStyleSheet("color: #333;")
                field_layout.addWidget(value_label)
            
            layout.addWidget(field_frame)
        
        return widget
    
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
        # For special sections (contract_overview, supplemental_operational_risks, final_analysis)
        # check if they have any widgets in their content layout
        special_sections = ['contract_overview', 'supplemental_operational_risks', 'final_analysis']
        
        for section_key, section in self.sections.items():
            if section_key in special_sections:
                # Check if the section has any content widgets
                if hasattr(section, 'content_widget_layout'):
                    if section.content_widget_layout.count() == 0:
                        section.collapse()
                    # If it has content, leave it as is (don't force expand or collapse)
            else:
                # For clause sections, check if all category boxes are empty
                section_empty = True
                for box_key, box in self.category_boxes.items():
                    if box_key.startswith(f"{section_key}."):
                        if not box.is_empty:
                            section_empty = False
                            break
                
                if section_empty:
                    section.collapse()
    
    def _expand_subsections(self, parent_widget: QWidget):
        """Recursively expand all subsections within a widget."""
        for child in parent_widget.findChildren(CollapsibleSection):
            child.expand()
    
    def _is_section_empty(self, section_key: str) -> bool:
        """
        Check if a section has meaningful content.
        
        This method is deprecated in favor of the template-based approach
        but kept for backward compatibility.
        """
        # For special sections, check if they have content widgets
        special_sections = ['contract_overview', 'supplemental_operational_risks', 'final_analysis']
        
        if section_key in special_sections:
            section = self.sections.get(section_key)
            if section and hasattr(section, 'content_widget_layout'):
                return section.content_widget_layout.count() == 0
            return True
        
        # For clause sections, check if all category boxes are empty
        for box_key, box in self.category_boxes.items():
            if box_key.startswith(f"{section_key}."):
                if not box.is_empty:
                    return False
        
        return True
