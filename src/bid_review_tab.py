"""
Bid Review Tab Module

Provides the Bid Review tab UI for the Bid Specification Review Checklist.
Displays a structured checklist with 6 sections where each item shows
extracted values, confidence indicators, and per-item analyze buttons.
"""

import logging
from typing import Dict, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QPushButton, QProgressBar, QFrame, QLineEdit, QSizePolicy,
    QGridLayout, QGroupBox,
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QColor

from analyzer.bid_spec_patterns import BID_ITEM_MAP, BID_ITEM_DESCRIPTIONS
from src.bid_review_models import ChecklistItem, BidChecklistResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Section definitions for the UI layout
# ---------------------------------------------------------------------------

SECTION_DEFS = [
    ("Standard Contract Items", "standard_contract_items", [
        "pre_bid", "submission_format", "bid_bond", "payment_performance_bonds",
        "contract_time", "liquidated_damages", "warranty", "contractor_license",
        "insurance", "minority_dbe_goals", "working_hours", "subcontracting",
        "funding", "certified_payroll", "retainage", "safety", "qualifications",
    ]),
    ("Site Conditions", "site_conditions", [
        "site_access", "site_restoration", "bypass", "traffic_control",
        "disposal", "water_hydrant_meter",
    ]),
    ("Cleaning", "cleaning", [
        "cleaning_method", "cleaning_passes", "cleaning_notifications",
    ]),
    ("CCTV", "cctv", [
        "nassco", "cctv_submittal_format", "cctv_notifications",
    ]),
    ("CIPP", "cipp", [
        "cipp_curing_method", "cipp_cure_water", "cipp_warranty",
        "cipp_notifications", "cipp_contractor_qualifications",
        "cipp_wet_out_facility", "cipp_end_seals", "cipp_mudding_the_ends",
        "cipp_conditions_above", "cipp_pre_liner", "cipp_pipe_information",
        "cipp_resin_type", "cipp_testing", "cipp_engineered_design_stamp",
        "cipp_calculations", "cipp_air_testing",
    ]),
    ("CIPP Design & Performance", "cipp_design", [
        "cipp_design_life", "cipp_astm_standard", "cipp_gravity_pipe_conditions",
        "cipp_flexural_strength", "cipp_flexural_modulus", "cipp_tensile_strength",
        "cipp_design_safety_factor", "cipp_short_term_flexural_modulus",
        "cipp_long_term_flexural_modulus", "cipp_creep_retention_factor",
        "cipp_ovality", "cipp_soil_modulus", "cipp_soil_density",
        "cipp_groundwater_depth", "cipp_live_load", "cipp_poissons_ratio",
    ]),
    ("Manhole Rehab", "manhole_rehab", [
        "mh_information", "mh_product_type", "mh_products", "mh_testing",
        "mh_warranty", "mh_thickness", "mh_compressive_strength",
        "mh_bond_strength", "mh_shrinkage", "mh_grout",
        "mh_measurement_payment", "mh_external_coating", "mh_notifications",
        "mh_nace", "mh_bypass", "mh_substitution_requirements",
    ]),
    ("Spincast", "spincast", [
        "spincast_product_type", "spincast_testing", "spincast_warranty",
        "spincast_thickness", "spincast_corrugations",
    ]),
]


# ---------------------------------------------------------------------------
# Background threads
# ---------------------------------------------------------------------------

class BidReviewAllThread(QThread):
    """Background thread for analyzing all bid checklist items."""
    item_complete = pyqtSignal(str, str, object)   # item_key, display_name, ChecklistItem
    item_not_found = pyqtSignal(str, str)           # item_key, display_name
    item_error = pyqtSignal(str, str)               # item_key, error_msg
    all_finished = pyqtSignal(object)               # BidChecklistResult
    progress = pyqtSignal(str, int)                 # message, percent

    def __init__(self, engine, prepared):
        super().__init__()
        self.engine = engine
        self.prepared = prepared
        self.cancelled = False
        self._item_results: Dict[str, ChecklistItem] = {}

    def run(self):
        try:
            def on_item(item_key, display_name, item):
                self._item_results[item_key] = item
                if item.found:
                    self.item_complete.emit(item_key, display_name, item)
                else:
                    self.item_not_found.emit(item_key, display_name)

            self.engine.analyze_all_items(
                self.prepared,
                progress_callback=lambda msg, pct: self.progress.emit(msg, pct),
                item_callback=on_item,
                cancelled_check=lambda: self.cancelled,
            )

            result = self.engine.build_result(
                self.prepared, self._item_results
            )
            self.all_finished.emit(result)

        except Exception as e:
            logger.error("Bid review thread error: %s", e, exc_info=True)
            self.item_error.emit("_all", str(e))


class SingleBidItemThread(QThread):
    """Background thread for analyzing a single bid checklist item."""
    finished = pyqtSignal(str, str, object)   # item_key, display_name, ChecklistItem
    error = pyqtSignal(str, str)              # item_key, error_msg

    def __init__(self, engine, prepared, item_key):
        super().__init__()
        self.engine = engine
        self.prepared = prepared
        self.item_key = item_key

    def run(self):
        try:
            section_key, display_name, item = self.engine.analyze_single_item(
                self.prepared, self.item_key
            )
            self.finished.emit(self.item_key, display_name, item)
        except Exception as e:
            logger.error("Single bid item error for %s: %s", self.item_key, e, exc_info=True)
            self.error.emit(self.item_key, str(e))


# ---------------------------------------------------------------------------
# Confidence indicator colors
# ---------------------------------------------------------------------------

CONFIDENCE_COLORS = {
    "high": "#4CAF50",      # green
    "medium": "#FF9800",    # orange
    "low": "#F44336",       # red
    "not_found": "#9E9E9E", # gray
}

CONFIDENCE_LABELS = {
    "high": "Found",
    "medium": "Likely",
    "low": "Uncertain",
    "not_found": "Not found",
}


# ---------------------------------------------------------------------------
# Main tab widget
# ---------------------------------------------------------------------------

class BidReviewTab(QWidget):
    """
    Bid Review tab with checklist-style display.

    Signals:
        analysis_requested: Emitted when user clicks "Analyze Checklist"
        item_analyzed: Emitted when a single item is analyzed (for session save)
        review_finished: Emitted when full review completes (for session save)
    """

    analysis_requested = pyqtSignal()
    item_analyzed = pyqtSignal(str, str, object)   # item_key, display_name, ChecklistItem
    review_finished = pyqtSignal(object)            # BidChecklistResult

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bid_engine = None
        self.prepared = None
        self.item_results: Dict[str, ChecklistItem] = {}
        self._item_rows: Dict[str, dict] = {}  # item_key -> {value_edit, conf_label, btn, ...}
        self._current_thread = None
        self._current_result: Optional[BidChecklistResult] = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        self.setLayout(layout)

        # Title
        title = QLabel("Bid Specification Review Checklist")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("padding: 6px;")
        layout.addWidget(title)

        # Instructions (shown when no contract loaded)
        self.instructions_label = QLabel(
            "No contract loaded.\n\n"
            "Use the file bar above to browse and load a contract,\n"
            "then click 'Analyze Checklist' to extract bid specification details."
        )
        self.instructions_label.setWordWrap(True)
        self.instructions_label.setAlignment(Qt.AlignCenter)
        self.instructions_label.setStyleSheet(
            "padding: 30px; font-size: 13px; color: #888;"
        )
        layout.addWidget(self.instructions_label)

        # Top bar: Analyze All button + completion stats
        top_bar = QHBoxLayout()

        self.analyze_all_btn = QPushButton("Analyze Checklist")
        self.analyze_all_btn.setStyleSheet(
            "QPushButton {"
            "    padding: 8px 24px;"
            "    font-size: 13px; font-weight: bold;"
            "    background: #2196F3; color: white;"
            "    border: none; border-radius: 4px;"
            "}"
            "QPushButton:hover { background: #1976D2; }"
            "QPushButton:disabled { background: #BDBDBD; }"
        )
        self.analyze_all_btn.clicked.connect(self._on_analyze_all_clicked)
        self.analyze_all_btn.setVisible(False)
        top_bar.addWidget(self.analyze_all_btn)

        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("font-size: 12px; color: #555; padding-left: 12px;")
        top_bar.addWidget(self.stats_label)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(18)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #666; font-size: 11px;")
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)

        # Scrollable checklist area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        self.checklist_container = QWidget()
        self.checklist_layout = QVBoxLayout(self.checklist_container)
        self.checklist_layout.setContentsMargins(0, 0, 0, 0)
        self.checklist_layout.setSpacing(6)

        # Build all sections
        for section_title, section_key, item_keys in SECTION_DEFS:
            group = self._create_section(section_title, item_keys)
            self.checklist_layout.addWidget(group)

        self.checklist_layout.addStretch()
        scroll.setWidget(self.checklist_container)

        self.scroll_area = scroll
        self.scroll_area.setVisible(False)
        layout.addWidget(scroll)

    def _create_section(self, title: str, item_keys: list) -> QGroupBox:
        """Create a collapsible group box for a checklist section."""
        group = QGroupBox(title)
        group.setStyleSheet(
            "QGroupBox {"
            "    font-size: 13px; font-weight: bold;"
            "    border: 1px solid #ccc;"
            "    border-radius: 4px;"
            "    margin-top: 8px;"
            "    padding-top: 16px;"
            "}"
            "QGroupBox::title {"
            "    subcontrol-origin: margin;"
            "    left: 10px;"
            "    padding: 0 4px;"
            "    background: white;"
            "}"
        )

        grid = QGridLayout()
        grid.setColumnStretch(0, 2)  # Item name
        grid.setColumnStretch(1, 4)  # Value
        grid.setColumnStretch(2, 1)  # Confidence
        grid.setColumnStretch(3, 0)  # Button
        grid.setSpacing(4)

        # Header row
        for col, text in enumerate(["Item", "Bid Details", "Status", ""]):
            lbl = QLabel(text)
            lbl.setStyleSheet("font-size: 11px; color: #999; font-weight: normal; padding: 2px;")
            grid.addWidget(lbl, 0, col)

        for row_idx, item_key in enumerate(item_keys, start=1):
            _, display_name = BID_ITEM_MAP.get(item_key, ("", item_key))
            tooltip = BID_ITEM_DESCRIPTIONS.get(item_key, "")

            # Item name label
            name_lbl = QLabel(display_name)
            name_lbl.setStyleSheet("font-size: 12px; font-weight: normal; padding: 3px;")
            name_lbl.setWordWrap(True)
            if tooltip:
                name_lbl.setToolTip(tooltip)
            grid.addWidget(name_lbl, row_idx, 0)

            # Value (editable line edit)
            value_edit = QLineEdit()
            value_edit.setPlaceholderText("Not reviewed")
            value_edit.setStyleSheet(
                "QLineEdit {"
                "    font-size: 12px; padding: 3px 6px;"
                "    border: 1px solid #ddd; border-radius: 3px;"
                "    background: #fafafa;"
                "}"
                "QLineEdit:focus { border-color: #2196F3; background: white; }"
            )
            grid.addWidget(value_edit, row_idx, 1)

            # Confidence indicator
            conf_label = QLabel("--")
            conf_label.setAlignment(Qt.AlignCenter)
            conf_label.setFixedWidth(70)
            conf_label.setStyleSheet(
                "font-size: 10px; color: #999; padding: 2px 4px;"
                "border-radius: 3px;"
            )
            grid.addWidget(conf_label, row_idx, 2)

            # Analyze button
            btn = QPushButton("Analyze")
            btn.setFixedWidth(65)
            btn.setStyleSheet(
                "QPushButton {"
                "    font-size: 10px; padding: 3px 6px;"
                "    background: #e3f2fd; border: 1px solid #90CAF9;"
                "    border-radius: 3px; color: #1565C0;"
                "}"
                "QPushButton:hover { background: #BBDEFB; }"
                "QPushButton:disabled { background: #eee; color: #aaa; border-color: #ddd; }"
            )
            btn.setEnabled(False)
            btn.clicked.connect(lambda checked, k=item_key: self._on_single_analyze(k))
            grid.addWidget(btn, row_idx, 3)

            self._item_rows[item_key] = {
                "value_edit": value_edit,
                "conf_label": conf_label,
                "btn": btn,
                "name_lbl": name_lbl,
            }

        group.setLayout(grid)
        return group

    # ------------------------------------------------------------------
    # Public methods (called by main GUI)
    # ------------------------------------------------------------------

    def set_contract_loaded(self, loaded: bool):
        """Update UI state when a contract is loaded or unloaded."""
        if loaded:
            self.instructions_label.setText(
                "Contract loaded. Click 'Analyze Checklist' to extract\n"
                "bid specification details from the contract."
            )
            self.analyze_all_btn.setVisible(True)
            self.analyze_all_btn.setEnabled(True)
            self.scroll_area.setVisible(True)
            # Enable per-item buttons
            for row in self._item_rows.values():
                row["btn"].setEnabled(True)
        else:
            self.instructions_label.setText(
                "No contract loaded.\n\n"
                "Load a contract on the Contract tab first, then return here\n"
                "to extract bid specification details."
            )
            self.analyze_all_btn.setVisible(False)
            self.scroll_area.setVisible(False)

    def set_engine_and_prepared(self, engine, prepared):
        """Set the bid review engine and prepared data (called by main GUI)."""
        self.bid_engine = engine
        self.prepared = prepared

    def get_result(self) -> Optional[BidChecklistResult]:
        """Return the current result, or None."""
        return self._current_result

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_analyze_all_clicked(self):
        """User clicked 'Analyze Checklist'."""
        self.analysis_requested.emit()

    def _on_single_analyze(self, item_key: str):
        """User clicked per-item 'Analyze' button."""
        if not self.bid_engine or not self.prepared:
            logger.warning("Bid engine or prepared data not set for item %s", item_key)
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, "Not Ready",
                "Bid review engine not initialized.\n"
                "Please load a contract first."
            )
            return

        # Prevent concurrent model access (llama_cpp is not thread-safe)
        if self._current_thread and self._current_thread.isRunning():
            logger.info("Waiting for previous analysis to finish before starting %s", item_key)
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(
                self, "Please Wait",
                "Another analysis is in progress. Please wait for it to finish."
            )
            return

        row = self._item_rows.get(item_key)
        if row:
            row["btn"].setEnabled(False)
            row["btn"].setText("...")
            row["conf_label"].setText("Analyzing...")
            row["conf_label"].setStyleSheet(
                "font-size: 10px; color: #2196F3; padding: 2px 4px;"
            )

        # Show progress feedback
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        _, display_name = BID_ITEM_MAP.get(item_key, ("", item_key))
        self.progress_label.setVisible(True)
        self.progress_label.setText(f"Analyzing: {display_name}...")

        thread = SingleBidItemThread(self.bid_engine, self.prepared, item_key)
        thread.finished.connect(self._on_single_item_done)
        thread.error.connect(self._on_single_item_error)
        # Keep reference to prevent GC
        self._current_thread = thread
        thread.start()

    def _on_single_item_done(self, item_key, display_name, item):
        """Handle single item analysis completion (hides progress, delegates to _on_item_complete)."""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self._on_item_complete(item_key, display_name, item)

    def _on_single_item_error(self, item_key, error_msg):
        """Handle single item analysis error (hides progress, delegates to _on_item_error)."""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self._on_item_error(item_key, error_msg)

    # ------------------------------------------------------------------
    # Start full analysis (called by main GUI after signal)
    # ------------------------------------------------------------------

    def start_analysis(self, engine, prepared):
        """Start analyzing all checklist items in background."""
        # Cancel any running single-item thread first (llama_cpp not thread-safe)
        if self._current_thread and self._current_thread.isRunning():
            logger.info("Cancelling previous thread before starting full analysis")
            if hasattr(self._current_thread, 'cancelled'):
                self._current_thread.cancelled = True
            self._current_thread.quit()
            self._current_thread.wait(5000)

        self.bid_engine = engine
        self.prepared = prepared

        # Reset UI
        self.analyze_all_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText("Starting bid review...")
        for row in self._item_rows.values():
            row["btn"].setEnabled(False)

        thread = BidReviewAllThread(engine, prepared)
        thread.item_complete.connect(self._on_item_complete)
        thread.item_not_found.connect(self._on_item_not_found)
        thread.item_error.connect(self._on_item_error)
        thread.all_finished.connect(self._on_all_finished)
        thread.progress.connect(self._on_progress)
        self._current_thread = thread
        thread.start()

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------

    def _on_item_complete(self, item_key: str, display_name: str, item):
        """A single item was analyzed successfully."""
        if isinstance(item, ChecklistItem):
            self.item_results[item_key] = item
        else:
            # item might come through as generic object from signal
            self.item_results[item_key] = item

        row = self._item_rows.get(item_key)
        if not row:
            return

        conf = item.confidence if hasattr(item, "confidence") else "not_found"
        value = item.value if hasattr(item, "value") else str(item)
        notes = item.notes if hasattr(item, "notes") else ""

        row["value_edit"].setText(value)
        color = CONFIDENCE_COLORS.get(conf, "#9E9E9E")
        label_text = CONFIDENCE_LABELS.get(conf, conf)
        row["conf_label"].setText(label_text)
        row["conf_label"].setStyleSheet(
            f"font-size: 10px; color: white; background: {color};"
            f"padding: 2px 4px; border-radius: 3px;"
        )
        row["btn"].setEnabled(True)
        row["btn"].setText("Redo")

        if notes:
            row["value_edit"].setToolTip(notes)

        self._update_stats()

        # Relay to main GUI for session persistence
        self.item_analyzed.emit(item_key, display_name, item)

    def _on_item_not_found(self, item_key: str, display_name: str):
        """Item was analyzed but not found in document."""
        row = self._item_rows.get(item_key)
        if not row:
            return

        row["value_edit"].setText("")
        row["value_edit"].setPlaceholderText("Not found in document")
        row["conf_label"].setText("Not found")
        row["conf_label"].setStyleSheet(
            "font-size: 10px; color: white; background: #9E9E9E;"
            "padding: 2px 4px; border-radius: 3px;"
        )
        row["btn"].setEnabled(True)
        row["btn"].setText("Retry")
        self._update_stats()

    def _on_item_error(self, item_key: str, error_msg: str):
        """Item analysis failed."""
        row = self._item_rows.get(item_key)
        if not row:
            return

        row["conf_label"].setText("Error")
        row["conf_label"].setStyleSheet(
            "font-size: 10px; color: white; background: #F44336;"
            "padding: 2px 4px; border-radius: 3px;"
        )
        row["btn"].setEnabled(True)
        row["btn"].setText("Retry")
        row["value_edit"].setToolTip(f"Error: {error_msg}")

    def _on_all_finished(self, result):
        """All items analyzed."""
        self._current_result = result
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.analyze_all_btn.setEnabled(True)
        self.analyze_all_btn.setText("Re-analyze Checklist")

        # Re-enable all per-item buttons
        for row in self._item_rows.values():
            row["btn"].setEnabled(True)

        self._update_stats()
        logger.info("Bid review complete")

        # Relay to main GUI for session persistence
        self.review_finished.emit(result)

    def _on_progress(self, message: str, percent: int):
        """Update progress bar."""
        self.progress_bar.setValue(percent)
        self.progress_label.setText(message)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _update_stats(self):
        """Update the completion stats label."""
        total = len(self._item_rows)
        found = sum(
            1 for item_key, row in self._item_rows.items()
            if item_key in self.item_results
            and hasattr(self.item_results[item_key], "found")
            and self.item_results[item_key].found
        )
        pct = round(found / total * 100) if total else 0
        self.stats_label.setText(f"{found}/{total} items found ({pct}%)")
