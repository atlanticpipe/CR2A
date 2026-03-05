"""
Specs Tab Module

Provides the Specs tab UI for displaying technical specifications
extracted from a contract. Users can trigger spec analysis after loading
a contract on the Contract tab.
"""

import logging
from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea,
    QPushButton, QMessageBox, QProgressBar, QTextEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class SpecsAnalysisThread(QThread):
    """Background thread for extracting technical specifications from contract text."""
    finished = pyqtSignal(str)      # plain text result
    error = pyqtSignal(str)         # error message
    progress = pyqtSignal(str, int) # status message, percent

    def __init__(self, ai_client, contract_text: str):
        super().__init__()
        self.ai_client = ai_client
        self.contract_text = contract_text

    def run(self):
        try:
            self.progress.emit("Extracting technical specifications...", 10)

            # Send a generous portion of the contract
            text_for_ai = self.contract_text[:8000]
            if len(self.contract_text) > 10000:
                text_for_ai += "\n\n[...]\n\n" + self.contract_text[-2000:]

            system_msg = (
                "You are a construction contract specification expert. "
                "Extract ALL technical specifications from the contract text. "
                "Focus on measurable requirements: dimensions, thicknesses, strengths, "
                "pressures, temperatures, durations, quantities, and material grades."
            )

            user_msg = f"""List every technical specification found in this contract.

For each specification, state:
- What it is (e.g., Manhole Interior Coating Thickness)
- The required value (e.g., 12 mils minimum dry film thickness)
- Where it appears in the contract (section or article reference)

Look for specifications related to:
- Coating and lining thicknesses
- Concrete and mortar strengths (PSI)
- Pipe sizes and dimensions
- Material grades and standards (ASTM, AASHTO, etc.)
- Testing requirements (pressure tests, compaction percentages)
- Temperature and environmental limits
- Curing times and durations
- Excavation depths and trench dimensions
- Reinforcement sizes and spacing
- Flow rates and capacities
- Any other measurable technical requirement

Contract text:
{text_for_ai}
"""

            self.progress.emit("AI analyzing specifications...", 40)

            raw = self.ai_client.generate(system_msg, user_msg, max_tokens=4000)

            logger.info(f"Specs AI response length: {len(raw)} chars")

            self.progress.emit("Complete!", 100)
            self.finished.emit(raw.strip())

        except Exception as e:
            logger.error(f"Specs analysis failed: {e}", exc_info=True)
            self.error.emit(str(e))


class SpecsTab(QWidget):
    """
    Specs tab widget for displaying technical specifications extracted from a contract.

    Signals:
        analysis_requested: Emitted when user clicks "Analyze Specs" button
    """

    analysis_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.analysis_thread: Optional[SpecsAnalysisThread] = None
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Title
        title = QLabel("Technical Specifications")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("padding: 10px;")
        layout.addWidget(title)

        # Instructions / status message
        self.instructions_label = QLabel(
            "No contract loaded.\n\n"
            "Load a contract on the Contract tab first, then return here\n"
            "to extract technical specifications."
        )
        self.instructions_label.setWordWrap(True)
        self.instructions_label.setAlignment(Qt.AlignCenter)
        self.instructions_label.setStyleSheet(
            "padding: 30px; font-size: 13px; color: #888;"
        )
        layout.addWidget(self.instructions_label)

        # Analyze button (hidden until contract is loaded)
        self.analyze_btn = QPushButton("Analyze Specs")
        self.analyze_btn.setStyleSheet(
            "QPushButton {"
            "    padding: 10px 30px;"
            "    font-size: 14px;"
            "    background: #2196F3;"
            "    color: white;"
            "    border: none;"
            "    border-radius: 5px;"
            "}"
            "QPushButton:hover {"
            "    background: #1976D2;"
            "}"
            "QPushButton:disabled {"
            "    background: #BDBDBD;"
            "}"
        )
        self.analyze_btn.clicked.connect(self._on_analyze_clicked)
        self.analyze_btn.setVisible(False)
        layout.addWidget(self.analyze_btn, alignment=Qt.AlignCenter)

        # Progress bar (hidden until analysis starts)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { max-width: 400px; }")
        layout.addWidget(self.progress_bar, alignment=Qt.AlignCenter)

        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("color: #666; font-size: 11px;")
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)

        # Results text area (hidden until we have results)
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setVisible(False)
        self.results_text.setStyleSheet(
            "QTextEdit {"
            "    border: 1px solid #ddd;"
            "    padding: 10px;"
            "    font-size: 13px;"
            "    line-height: 1.5;"
            "}"
        )
        layout.addWidget(self.results_text)

        layout.addStretch()

    def set_contract_loaded(self, loaded: bool):
        """Update UI state when a contract is loaded or unloaded."""
        if loaded:
            self.instructions_label.setText(
                "Contract loaded. Click 'Analyze Specs' to extract\n"
                "technical specifications from the contract."
            )
            self.analyze_btn.setVisible(True)
            self.analyze_btn.setEnabled(True)
        else:
            self.instructions_label.setText(
                "No contract loaded.\n\n"
                "Load a contract on the Contract tab first, then return here\n"
                "to extract technical specifications."
            )
            self.analyze_btn.setVisible(False)
            self.results_text.setVisible(False)

    def _on_analyze_clicked(self):
        """Handle analyze button click."""
        self.analysis_requested.emit()

    def start_analysis(self, ai_client, contract_text: str):
        """Start spec analysis in a background thread."""
        if self.analysis_thread and self.analysis_thread.isRunning():
            return

        self.analyze_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText("Starting spec analysis...")
        self.results_text.setVisible(False)

        self.analysis_thread = SpecsAnalysisThread(ai_client, contract_text)
        self.analysis_thread.finished.connect(self._on_analysis_finished)
        self.analysis_thread.error.connect(self._on_analysis_error)
        self.analysis_thread.progress.connect(self._on_analysis_progress)
        self.analysis_thread.start()

    def _on_analysis_progress(self, message: str, percent: int):
        """Handle progress updates from the analysis thread."""
        self.progress_bar.setValue(percent)
        self.progress_label.setText(message)

    def _on_analysis_finished(self, text: str):
        """Handle successful analysis completion."""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.analyze_btn.setEnabled(True)

        if not text:
            self.instructions_label.setText(
                "No technical specifications found in this contract.\n"
                "Try re-analyzing or check that the contract contains spec data."
            )
            return

        self.instructions_label.setText("Specifications extracted from contract:")
        self.results_text.setPlainText(text)
        self.results_text.setVisible(True)

    def _on_analysis_error(self, error_msg: str):
        """Handle analysis error."""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.analyze_btn.setEnabled(True)

        QMessageBox.warning(
            self,
            "Spec Analysis Error",
            f"Failed to extract specifications:\n\n{error_msg}"
        )

    def clear(self):
        """Clear all results and reset to initial state."""
        self.results_text.clear()
        self.results_text.setVisible(False)
        self.set_contract_loaded(False)
