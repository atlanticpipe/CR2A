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

# Add project root to path so "from src.X" works when running directly.
# parent = src/, parent.parent = project root (where src/ is a package).
sys.path.insert(0, str(Path(__file__).parent.parent))

# Use software rendering for Qt so the GPU is fully available for LLM inference.
# Intel iGPU Vulkan compute (llama.cpp) conflicts with Qt's GPU rendering.
os.environ.setdefault("QT_OPENGL", "software")

# IMPORTANT: Initialize llama.cpp's Vulkan backend BEFORE PyQt5 is imported.
# Qt5 loads GPU libraries that corrupt the Vulkan compute state if initialized
# after Qt. Calling llama_backend_init() first claims the Vulkan device cleanly.
try:
    import llama_cpp as _llama_cpp
    _llama_cpp.llama_backend_init()
except Exception:
    pass

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QFileDialog, QMessageBox,
    QProgressBar, QTabWidget, QScrollArea, QGroupBox, QLineEdit,
    QMenuBar, QMenu, QAction, QDialog, QFormLayout, QDialogButtonBox,
    QCheckBox, QSpinBox, QRadioButton, QComboBox, QButtonGroup,
    QSplitter, QSlider, QFrame, QStackedWidget, QTreeView,
    QHeaderView, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDir, QUrl, QSortFilterProxyModel, QModelIndex
from PyQt5.QtGui import QFont, QColor, QDesktopServices, QIcon
from PyQt5.QtWidgets import QFileSystemModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

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

import html as html_module
import re as _re


# ═══════════════════════════════════════════════════════════════════════════════
# Chat message widget — individual message frames with optional feedback buttons
# ═══════════════════════════════════════════════════════════════════════════════

class ChatMessageWidget(QFrame):
    """A single chat message displayed in the scrollable chat panel.

    For 'summary' messages (analysis results), includes Accept/Correct buttons.
    For 'not_found' messages, includes an 'I Found This' button.
    """

    feedback_accepted = pyqtSignal(str, dict)        # cat_key, clause_block
    feedback_corrected = pyqtSignal(str, dict, str)   # cat_key, original_data, corrected_text
    feedback_found = pyqtSignal(str)                  # cat_key (user says they found a missed clause)

    def __init__(self, msg_type, content, title=None, theme=None, parent=None,
                 cat_key=None, clause_block=None):
        super().__init__(parent)
        self.cat_key = cat_key
        self.clause_block = clause_block or {}
        self.msg_type = msg_type

        if theme is None:
            theme = THEMES.get('light', {})
        t = theme

        styles = {
            'system':      f'color: {t.get("text_muted","#888")}; font-style: italic; padding: 4px 8px;',
            'log':         f'color: {t.get("text_dim","#666")}; font-size: 11px; padding: 2px 8px;',
            'info':        f'color: {t.get("text_dim","#666")}; font-size: 11px; padding: 2px 8px;',
            'prompt':      f'background: {t.get("prompt_bg","#f0f0f0")}; border-left: 3px solid {t.get("prompt_border","#ccc")}; padding: 6px 10px; margin: 4px 0; font-family: monospace; font-size: 11px; white-space: pre-wrap;',
            'response':    f'background: {t.get("observation_bg","#f0f0f0")}; border-left: 3px solid {t.get("observation_border","#ccc")}; padding: 6px 10px; margin: 4px 0; font-family: monospace; font-size: 11px; white-space: pre-wrap;',
            'summary':     f'padding: 6px 8px; background: {t.get("summary_bg","#f5f5f5")}; border-left: 3px solid {t.get("summary_border","#888")}; margin: 2px 0;',
            'not_found':   f'padding: 6px 8px; background: {t.get("summary_bg","#f5f5f5")}; border-left: 3px solid {t.get("warning","#cca700")}; margin: 2px 0;',
            'user':        f'padding: 6px 8px; background: {t.get("user_msg_bg","#e3f2fd")}; border-radius: 4px; margin: 4px 0;',
            'answer':      f'padding: 8px; background: {t.get("answer_bg","#fff")}; border-left: 3px solid {t.get("answer_border","#569cd6")}; margin: 4px 0;',
            'error':       f'color: {t.get("error","#f44747")}; padding: 4px 8px;',
            'thought':     f'color: {t.get("text_dim","#666")}; font-style: italic; font-size: 11px; padding: 2px 8px;',
            'tool_call':   f'background: {t.get("tool_bg","#fffde7")}; border-left: 3px solid {t.get("tool_border","#cca700")}; padding: 4px 10px; margin: 2px 0; font-family: monospace; font-size: 11px;',
            'observation': f'background: {t.get("observation_bg","#f0f0f0")}; border-left: 3px solid {t.get("observation_border","#ccc")}; padding: 4px 10px; margin: 2px 0; font-size: 11px;',
        }

        style = styles.get(msg_type, 'padding: 4px 8px;')

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.setLayout(layout)

        # Render message body as HTML label
        if msg_type in ('answer', 'response'):
            body = _md_to_html(content)
        else:
            body = html_module.escape(content).replace('\n', '<br>')

        if title:
            safe_title = html_module.escape(title)
            html_text = f'<div style="{style}"><b>{safe_title}</b><br>{body}</div>'
        else:
            html_text = f'<div style="{style}">{body}</div>'

        self.message_label = QLabel(html_text)
        self.message_label.setWordWrap(True)
        self.message_label.setTextFormat(Qt.RichText)
        self.message_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.message_label)

        # Feedback buttons for analysis results
        if msg_type == 'summary' and cat_key:
            self._add_feedback_buttons(layout, t)
        elif msg_type == 'not_found' and cat_key:
            self._add_found_button(layout, t)

    def _add_feedback_buttons(self, layout, t):
        """Add Accept / Correct buttons for analysis result messages."""
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(8, 2, 8, 4)
        btn_layout.setSpacing(6)

        accept_btn = QPushButton("Accept")
        accept_btn.setToolTip("Mark this analysis as correct — saves as a learning example")
        accept_btn.setStyleSheet(
            f"padding: 3px 10px; font-size: 10px; background: {t.get('success','#4ec9b0')}; "
            f"color: white; border: none; border-radius: 3px;"
        )
        accept_btn.setCursor(Qt.PointingHandCursor)
        accept_btn.clicked.connect(self._on_accept)
        btn_layout.addWidget(accept_btn)

        correct_btn = QPushButton("Correct")
        correct_btn.setToolTip("Provide the correct analysis — saves as a correction for learning")
        correct_btn.setStyleSheet(
            f"padding: 3px 10px; font-size: 10px; background: {t.get('warning','#cca700')}; "
            f"color: white; border: none; border-radius: 3px;"
        )
        correct_btn.setCursor(Qt.PointingHandCursor)
        correct_btn.clicked.connect(self._on_correct)
        btn_layout.addWidget(correct_btn)

        btn_layout.addStretch()

        self.feedback_status = QLabel("")
        self.feedback_status.setStyleSheet("font-size: 10px; font-style: italic;")
        btn_layout.addWidget(self.feedback_status)

        layout.addLayout(btn_layout)

    def _add_found_button(self, layout, t):
        """Add 'I Found This' button for not-found results."""
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(8, 2, 8, 4)
        btn_layout.setSpacing(6)

        found_btn = QPushButton("I Found This")
        found_btn.setToolTip("The AI missed this clause — provide the correct text so it learns")
        found_btn.setStyleSheet(
            f"padding: 3px 10px; font-size: 10px; background: {t.get('accent','#569cd6')}; "
            f"color: white; border: none; border-radius: 3px;"
        )
        found_btn.setCursor(Qt.PointingHandCursor)
        found_btn.clicked.connect(self._on_found)
        btn_layout.addWidget(found_btn)

        btn_layout.addStretch()

        self.feedback_status = QLabel("")
        self.feedback_status.setStyleSheet("font-size: 10px; font-style: italic;")
        btn_layout.addWidget(self.feedback_status)

        layout.addLayout(btn_layout)

    def _on_accept(self):
        if self.cat_key:
            self.feedback_accepted.emit(self.cat_key, self.clause_block)
            self.feedback_status.setText("Saved as learning example")

    def _on_correct(self):
        if self.cat_key:
            # Open correction dialog
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Correct: {self.cat_key.replace('_', ' ').title()}")
            dialog.setMinimumWidth(500)
            dialog.setMinimumHeight(350)

            dlg_layout = QVBoxLayout()
            dialog.setLayout(dlg_layout)

            original = self.clause_block.get('Clause Summary', '')
            dlg_layout.addWidget(QLabel("Original AI analysis:"))
            orig_display = QTextEdit()
            orig_display.setPlainText(original)
            orig_display.setReadOnly(True)
            orig_display.setMaximumHeight(100)
            dlg_layout.addWidget(orig_display)

            dlg_layout.addWidget(QLabel("Your correction:"))
            correction_edit = QTextEdit()
            correction_edit.setPlaceholderText("Enter the correct analysis...")
            dlg_layout.addWidget(correction_edit)

            dlg_layout.addWidget(QLabel("Lesson (optional — why was the AI wrong?):"))
            lesson_edit = QLineEdit()
            lesson_edit.setPlaceholderText("e.g., 'This clause was in the addendum, not the main spec'")
            dlg_layout.addWidget(lesson_edit)

            btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            btn_box.accepted.connect(dialog.accept)
            btn_box.rejected.connect(dialog.reject)
            dlg_layout.addWidget(btn_box)

            if dialog.exec_() == QDialog.Accepted:
                corrected = correction_edit.toPlainText().strip()
                lesson = lesson_edit.text().strip()
                if corrected:
                    if lesson:
                        corrected += f"\n[LESSON: {lesson}]"
                    self.feedback_corrected.emit(self.cat_key, self.clause_block, corrected)
                    self.feedback_status.setText("Correction saved for learning")

    def _on_found(self):
        """User says they found a clause the AI missed."""
        if not self.cat_key:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Found: {self.cat_key.replace('_', ' ').title()}")
        dialog.setMinimumWidth(500)
        dialog.setMinimumHeight(300)

        dlg_layout = QVBoxLayout()
        dialog.setLayout(dlg_layout)

        dlg_layout.addWidget(QLabel("The AI reported this clause as NOT FOUND."))
        dlg_layout.addWidget(QLabel("Paste or type the correct clause summary:"))

        correction_edit = QTextEdit()
        correction_edit.setPlaceholderText("Enter what the clause actually says...")
        dlg_layout.addWidget(correction_edit)

        dlg_layout.addWidget(QLabel("Where did you find it? (optional):"))
        location_edit = QLineEdit()
        location_edit.setPlaceholderText("e.g., 'Addendum 2, Section 7.3'")
        dlg_layout.addWidget(location_edit)

        dlg_layout.addWidget(QLabel("Lesson (optional — why did the AI miss it?):"))
        lesson_edit = QLineEdit()
        lesson_edit.setPlaceholderText("e.g., 'It was under a non-standard heading'")
        dlg_layout.addWidget(lesson_edit)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        dlg_layout.addWidget(btn_box)

        if dialog.exec_() == QDialog.Accepted:
            corrected = correction_edit.toPlainText().strip()
            location = location_edit.text().strip()
            lesson = lesson_edit.text().strip()
            if corrected:
                # Build a clause block for the missed clause
                found_block = {
                    'Clause Summary': '',  # original was empty (not found)
                    'Clause Location': location or 'User-provided',
                    '_was_missed': True,
                }
                if lesson:
                    corrected += f"\n[LESSON: AI missed this clause — {lesson}]"
                else:
                    corrected += "\n[LESSON: AI missed this clause entirely]"
                self.feedback_corrected.emit(self.cat_key, found_block, corrected)
                self.feedback_status.setText("Correction saved — AI will look for this next time")


# ═══════════════════════════════════════════════════════════════════════════════
# Theme definitions
# ═══════════════════════════════════════════════════════════════════════════════

THEMES = {
    "dark": {
        # Window / global
        "window_bg": "#1e1e1e",
        "panel_bg": "#252526",
        "input_bg": "#3c3c3c",
        "border": "#3c3c3c",
        "text": "#cccccc",
        "text_muted": "#888888",
        "text_dim": "#666666",
        "accent": "#569cd6",
        "accent_hover": "#4a8abf",
        "accent_text": "#ffffff",
        "error": "#f44747",
        "warning": "#cca700",
        "success": "#4ec9b0",
        "header_bg": "#2d2d2d",
        "header_border": "#3c3c3c",
        "hover_bg": "#2a2d2e",
        "selection_bg": "#264f78",
        "chat_bg": "#1e1e1e",
        "user_msg_bg": "#264f78",
        "answer_bg": "#252526",
        "answer_border": "#569cd6",
        "summary_bg": "#2d2d2d",
        "summary_border": "#888888",
        "tool_bg": "#332b00",
        "tool_border": "#cca700",
        "observation_bg": "#1a2e1a",
        "observation_border": "#4ec9b0",
        "prompt_bg": "#1a2740",
        "prompt_border": "#569cd6",
        "scrollbar_bg": "#1e1e1e",
        "scrollbar_handle": "#424242",
        "quick_btn_bg": "#2d2d2d",
        "quick_btn_border": "#3c3c3c",
    },
    "light": {
        "window_bg": "#ffffff",
        "panel_bg": "#f5f5f5",
        "input_bg": "#ffffff",
        "border": "#e0e0e0",
        "text": "#1e1e1e",
        "text_muted": "#666666",
        "text_dim": "#999999",
        "accent": "#1976D2",
        "accent_hover": "#1565C0",
        "accent_text": "#ffffff",
        "error": "#c62828",
        "warning": "#FF9800",
        "success": "#4CAF50",
        "header_bg": "#e8e8e8",
        "header_border": "#cccccc",
        "hover_bg": "#e3f2fd",
        "selection_bg": "#bbdefb",
        "chat_bg": "#fafafa",
        "user_msg_bg": "#e3f2fd",
        "answer_bg": "#f9f9f9",
        "answer_border": "#1976D2",
        "summary_bg": "#f5f5f5",
        "summary_border": "#999999",
        "tool_bg": "#fff3e0",
        "tool_border": "#FF9800",
        "observation_bg": "#e8f5e9",
        "observation_border": "#4CAF50",
        "prompt_bg": "#e3f2fd",
        "prompt_border": "#1976D2",
        "scrollbar_bg": "#f5f5f5",
        "scrollbar_handle": "#cccccc",
        "quick_btn_bg": "#e3f2fd",
        "quick_btn_border": "#90CAF9",
    },
}


def build_app_stylesheet(t):
    """Build a full QSS stylesheet from a theme dict."""
    return f"""
        QMainWindow, QDialog, QWidget {{
            background-color: {t['window_bg']};
            color: {t['text']};
        }}
        QLabel {{
            color: {t['text']};
        }}
        QLineEdit, QSpinBox, QComboBox {{
            background: {t['input_bg']};
            color: {t['text']};
            border: 1px solid {t['border']};
            border-radius: 4px;
            padding: 4px;
        }}
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
            border-color: {t['accent']};
        }}
        QPushButton {{
            background: {t['panel_bg']};
            color: {t['text']};
            border: 1px solid {t['border']};
            border-radius: 4px;
            padding: 6px 12px;
        }}
        QPushButton:hover {{
            background: {t['hover_bg']};
        }}
        QPushButton:pressed {{
            background: {t['selection_bg']};
        }}
        QTextEdit, QListWidget {{
            background: {t['chat_bg']};
            color: {t['text']};
            border: 1px solid {t['border']};
            border-radius: 4px;
        }}
        QTreeView {{
            background: {t['panel_bg']};
            color: {t['text']};
            border: none;
        }}
        QTreeView::item:hover {{
            background: {t['hover_bg']};
        }}
        QTreeView::item:selected {{
            background: {t['selection_bg']};
        }}
        QHeaderView::section {{
            background: {t['header_bg']};
            color: {t['text']};
            border: 1px solid {t['border']};
        }}
        QGroupBox {{
            color: {t['text']};
            border: 1px solid {t['border']};
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 14px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            color: {t['text']};
        }}
        QMenuBar {{
            background: {t['header_bg']};
            color: {t['text']};
        }}
        QMenuBar::item:selected {{
            background: {t['selection_bg']};
        }}
        QMenu {{
            background: {t['panel_bg']};
            color: {t['text']};
            border: 1px solid {t['border']};
        }}
        QMenu::item:selected {{
            background: {t['selection_bg']};
        }}
        QStatusBar {{
            background: {t['header_bg']};
            color: {t['text_muted']};
        }}
        QScrollBar:vertical {{
            background: {t['scrollbar_bg']};
            width: 10px;
        }}
        QScrollBar::handle:vertical {{
            background: {t['scrollbar_handle']};
            min-height: 20px;
            border-radius: 5px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar:horizontal {{
            background: {t['scrollbar_bg']};
            height: 10px;
        }}
        QScrollBar::handle:horizontal {{
            background: {t['scrollbar_handle']};
            min-width: 20px;
            border-radius: 5px;
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
        }}
        QProgressBar {{
            background: {t['panel_bg']};
            border: 1px solid {t['border']};
            border-radius: 3px;
            text-align: center;
            color: {t['text']};
        }}
        QProgressBar::chunk {{
            background: {t['accent']};
            border-radius: 3px;
        }}
        QSlider::groove:horizontal {{
            background: {t['border']};
            height: 6px;
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {t['accent']};
            width: 14px;
            margin: -4px 0;
            border-radius: 7px;
        }}
        QSplitter::handle {{
            background: {t['border']};
        }}
        QTabWidget::pane {{
            border: 1px solid {t['border']};
            background: {t['panel_bg']};
        }}
        QTabBar::tab {{
            background: {t['panel_bg']};
            color: {t['text']};
            border: 1px solid {t['border']};
            padding: 6px 12px;
        }}
        QTabBar::tab:selected {{
            background: {t['window_bg']};
            border-bottom: 2px solid {t['accent']};
        }}
        QCheckBox, QRadioButton {{
            color: {t['text']};
        }}
        QDialogButtonBox QPushButton {{
            min-width: 80px;
        }}
        /* Named element overrides */
        #landing_title {{
            color: {t['accent']};
        }}
        #landing_subtitle {{
            color: {t['text_muted']};
        }}
        #muted_label {{
            color: {t['text_muted']};
        }}
        #accent_btn {{
            background: {t['accent']};
            color: {t['accent_text']};
            border: none;
            border-radius: 6px;
        }}
        #accent_btn:hover {{
            background: {t['accent_hover']};
        }}
        #section_header {{
            text-align: left;
            padding: 6px 10px;
            font-weight: bold;
            font-size: 11px;
            background: {t['header_bg']};
            border: none;
            border-bottom: 1px solid {t['header_border']};
        }}
        #section_header:hover {{
            background: {t['hover_bg']};
        }}
        #chat_status {{
            color: {t['text_muted']};
        }}
    """


# ═══════════════════════════════════════════════════════════════════════════════
# Lightweight Markdown → HTML converter
# ═══════════════════════════════════════════════════════════════════════════════

def _md_to_html(text):
    """Convert basic Markdown to HTML for chat display.

    Handles: headers, bold, italic, code blocks, inline code, bullet lists,
    numbered lists, and line breaks.
    """
    lines = text.split('\n')
    html_parts = []
    in_code_block = False
    in_list = False
    list_type = None  # 'ul' or 'ol'

    for line in lines:
        # Fenced code blocks
        if line.strip().startswith('```'):
            if in_code_block:
                html_parts.append('</pre>')
                in_code_block = False
            else:
                if in_list:
                    html_parts.append(f'</{list_type}>')
                    in_list = False
                html_parts.append(
                    '<pre style="background: rgba(128,128,128,0.15); '
                    'padding: 8px; border-radius: 4px; font-family: monospace; '
                    'font-size: 12px; white-space: pre-wrap; margin: 4px 0;">'
                )
                in_code_block = True
            continue

        if in_code_block:
            html_parts.append(html_module.escape(line))
            html_parts.append('\n')
            continue

        stripped = line.strip()

        # Close list if line is not a list item
        if in_list and not _re.match(r'^[-*]\s', stripped) and not _re.match(r'^\d+\.\s', stripped) and stripped:
            html_parts.append(f'</{list_type}>')
            in_list = False

        # Empty line
        if not stripped:
            if in_list:
                html_parts.append(f'</{list_type}>')
                in_list = False
            html_parts.append('<br>')
            continue

        # Headers
        m = _re.match(r'^(#{1,3})\s+(.*)', stripped)
        if m:
            level = len(m.group(1))
            sizes = {1: '16px', 2: '14px', 3: '13px'}
            html_parts.append(
                f'<div style="font-weight: bold; font-size: {sizes[level]}; '
                f'margin: 6px 0 2px 0;">{_inline_md(m.group(2))}</div>'
            )
            continue

        # Bullet list
        m = _re.match(r'^[-*]\s+(.*)', stripped)
        if m:
            if not in_list or list_type != 'ul':
                if in_list:
                    html_parts.append(f'</{list_type}>')
                html_parts.append('<ul style="margin: 2px 0 2px 16px; padding: 0;">')
                in_list = True
                list_type = 'ul'
            html_parts.append(f'<li>{_inline_md(m.group(1))}</li>')
            continue

        # Numbered list
        m = _re.match(r'^(\d+)\.\s+(.*)', stripped)
        if m:
            if not in_list or list_type != 'ol':
                if in_list:
                    html_parts.append(f'</{list_type}>')
                html_parts.append('<ol style="margin: 2px 0 2px 16px; padding: 0;">')
                in_list = True
                list_type = 'ol'
            html_parts.append(f'<li>{_inline_md(m.group(2))}</li>')
            continue

        # Regular paragraph
        html_parts.append(f'<div>{_inline_md(stripped)}</div>')

    if in_code_block:
        html_parts.append('</pre>')
    if in_list:
        html_parts.append(f'</{list_type}>')

    return ''.join(html_parts)


def _inline_md(text):
    """Convert inline markdown: bold, italic, inline code."""
    text = html_module.escape(text)
    # Inline code
    text = _re.sub(r'`([^`]+)`', r'<code style="background: rgba(128,128,128,0.2); padding: 1px 4px; border-radius: 3px; font-family: monospace; font-size: 12px;">\1</code>', text)
    # Bold
    text = _re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    # Italic
    text = _re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    return text


class CR2AFolderFilterProxy(QSortFilterProxyModel):
    """Filter proxy that only shows 'prompts' and 'templates' folders (and their contents) in the CR2A tree."""

    ALLOWED_FOLDERS = {"prompts", "templates"}

    def __init__(self, root_path, parent=None):
        super().__init__(parent)
        self._root_path = root_path

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        index = model.index(source_row, 0, source_parent)
        file_path = model.filePath(index)
        file_name = model.fileName(index)

        # Get the path relative to the CR2A root
        try:
            rel = os.path.relpath(file_path, self._root_path).replace("\\", "/")
        except ValueError:
            # Cross-drive paths (e.g. F: vs E:) cannot be made relative
            return False
        parts = rel.split("/")

        if len(parts) == 0:
            return False

        # Top-level items: only show allowed folders
        if len(parts) == 1:
            return file_name in self.ALLOWED_FOLDERS and model.isDir(index)

        # Deeper items: show if their top-level ancestor is an allowed folder
        return parts[0] in self.ALLOWED_FOLDERS


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
            skipped_files = []
            for idx, file_path in enumerate(self.files):
                filename = file_path.name
                file_base_pct = int((idx / total) * 60)  # 0-60% for extraction
                file_range = int(60 / total)  # % range per file
                self.progress.emit(f"Extracting text from {filename}...", file_base_pct)

                # Sub-range callback: map page progress into this file's slice
                def make_file_progress(base, rng, fname):
                    def cb(status, pct):
                        mapped = base + int(pct * rng / 100)
                        self.progress.emit(f"{fname}: {status}", mapped)
                    return cb

                try:
                    text = self.engine.uploader.extract_text(
                        str(file_path),
                        progress_callback=make_file_progress(file_base_pct, file_range, filename)
                    )
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
                    else:
                        skipped_files.append(filename)
                        logger.warning(f"No text extracted from {filename} (empty)")
                except Exception as e:
                    skipped_files.append(filename)
                    logger.warning(f"Failed to extract text from {filename}: {e}")

            if skipped_files:
                logger.info(f"Skipped {len(skipped_files)} files (scanned/image PDFs): {skipped_files}")
                skip_msg = f"Skipped {len(skipped_files)} image-based file(s): {', '.join(skipped_files[:3])}"
                if len(skipped_files) > 3:
                    skip_msg += f" (+{len(skipped_files)-3} more)"
                self.progress.emit(skip_msg, 60)

            if not combined_text_parts:
                self.error.emit("No text could be extracted from any file in the folder.\n"
                               "The files may be scanned/image PDFs (plans, drawings).\n"
                               "Try loading text-based documents (ITB, specs, addenda).")
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


class ChatOrchestrationThread(QThread):
    """Background thread for ReAct-style tool-calling chat loop."""
    message = pyqtSignal(str, str)       # role, content — for incremental chat updates
    token_stream = pyqtSignal(str)       # individual token for streaming display
    tool_started = pyqtSignal(str, str)  # tool_name, args_str
    tool_finished = pyqtSignal(str, str) # tool_name, result_preview
    finished = pyqtSignal(list)          # full message list
    error = pyqtSignal(str)
    progress = pyqtSignal(str, int)

    def __init__(self, ai_client, tool_registry, user_message, conversation_history=None):
        super().__init__()
        self.ai_client = ai_client
        self.tool_registry = tool_registry
        self.user_message = user_message
        self.conversation_history = conversation_history or []

    def run(self):
        try:
            def progress_callback(status, percent):
                self.progress.emit(status, percent)

            def token_callback(token_text):
                self.token_stream.emit(token_text)

            result_messages = self.ai_client.process_with_tools(
                self.user_message,
                self.tool_registry,
                conversation_history=self.conversation_history,
                progress_callback=progress_callback,
                token_callback=token_callback,
            )

            # Emit individual messages for real-time display
            for msg in result_messages:
                role = msg.get("role", "assistant")
                content = msg.get("content", "")
                if role == "tool_call":
                    self.tool_started.emit(content, "")
                elif role == "observation":
                    self.tool_finished.emit("", content[:200])
                else:
                    self.message.emit(role, content)

            self.finished.emit(result_messages)

        except Exception as e:
            self.error.emit(str(e))


class QuickToolThread(QThread):
    """Background thread for direct tool execution (no ReAct loop)."""
    finished_signal = pyqtSignal(str, str)  # tool_name, result
    error_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str, int)  # message, percentage
    item_complete_signal = pyqtSignal(str, str, str, dict)  # type, key, display_name, data

    def __init__(self, tool_registry, tool_name):
        super().__init__()
        self.tool_registry = tool_registry
        self.tool_name = tool_name

    def run(self):
        try:
            # Wire up progress and per-item callbacks
            self.tool_registry.progress_callback = self._on_progress
            self.tool_registry.item_callback = self._on_item
            result = self.tool_registry.execute(self.tool_name, {})
            self.finished_signal.emit(self.tool_name, result)
        except Exception as e:
            self.error_signal.emit(str(e))
        finally:
            self.tool_registry.progress_callback = None
            self.tool_registry.item_callback = None

    def _on_progress(self, message, pct):
        self.progress_signal.emit(message, pct)

    def _on_item(self, item_type, key, display_name, data):
        self.item_complete_signal.emit(item_type, key, display_name, data)


class CR2A_GUI(QMainWindow):
    """Main application window — Chat-first interface."""

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
        self.excel_builder = None  # ExcelTemplateBuilder for auto-populating workbook
        self.tool_registry = None  # ToolRegistry for chat-based tool calling
        self.chat_thread = None  # ChatOrchestrationThread
        self.conversation_messages = []  # Chat conversation history for ReAct context
        self._streaming_tokens = []  # Token buffer for streaming display
        self._streaming_active = False  # Whether streaming is in progress
        self.prepared_bid_review = None  # PreparedBidReview for bid review engine
        self.bid_review_engine = None  # BidReviewEngine instance

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
        self.apply_theme()  # Apply theme after config is loaded
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
    
    def apply_theme(self, theme_name=None):
        """Apply a theme to the entire application."""
        if theme_name is None:
            theme_name = self.config_manager.get_theme() if self.config_manager else "light"
        t = THEMES.get(theme_name, THEMES["light"])
        self._current_theme = t
        self._current_theme_name = theme_name

        # Apply global stylesheet
        app = QApplication.instance()
        if app:
            app.setStyleSheet(build_app_stylesheet(t))

        # Save if changed
        if self.config_manager and self.config_manager.get_theme() != theme_name:
            self.config_manager.set_theme(theme_name)
            self.config_manager.save_config()

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
                if self.tabs:
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
            self._log_to_chat('system',
                f"Historical Analysis Loaded: {analysis_result.metadata.filename}\n"
                f"You can now ask questions about this analysis."
            )
            
            # Switch to Contract tab (merged upload + analysis at index 0)
            if self.tabs:
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
            self._log_to_chat('system',
                "The currently loaded analysis has been deleted from history.\n"
                "Please analyze a new contract or select another analysis from history."
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
        if self.structured_view:
            self.structured_view._clear_all_boxes()
            self.structured_view.enable_analyze_buttons(False)
    
    def init_ui(self):
        """Initialize the chat-first user interface (Phase 2)."""
        self.setWindowTitle("CR2A - Contract Review & Analysis")
        self.setGeometry(100, 100, 1400, 900)

        # Create menu bar
        self.create_menu_bar()

        # Central widget with stacked pages
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        central_widget.setLayout(main_layout)

        self.stacked = QStackedWidget()
        main_layout.addWidget(self.stacked)

        # ── Page 0: Folder Selection ──
        self.stacked.addWidget(self._create_folder_selection_page())

        # ── Page 1: Workspace (file browser + chat) ──
        self.stacked.addWidget(self._create_workspace_page())

        # Start on folder selection
        self.stacked.setCurrentIndex(0)

        # Compatibility stubs for old tab-based code paths
        self.tabs = None
        self.bid_review_tab = None
        self.specs_tab = None
        self.history_tab = None
        self.structured_view = None
        self.file_label = self.folder_name_label  # alias for backward compat
        self.upload_mode_label = QLabel("")  # hidden
        self.upload_status = self.workspace_status_label
        self.load_btn = QPushButton()  # hidden dummy
        self.load_all_btn = QPushButton()  # hidden dummy
        self.analyze_all_btn = QPushButton()  # hidden dummy

        # Status bar
        self.statusBar().showMessage("Ready — Open a folder to begin")

    def _create_folder_selection_page(self):
        """Create the folder selection landing page."""
        page = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        page.setLayout(layout)

        layout.addStretch(2)

        # Logo / Title
        title = QLabel("CR2A")
        title.setFont(QFont("Arial", 48, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("landing_title")
        layout.addWidget(title)

        subtitle = QLabel("Contract Review & Analysis")
        subtitle.setFont(QFont("Arial", 16))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setObjectName("landing_subtitle")
        layout.addWidget(subtitle)

        # Open Folder button
        open_btn = QPushButton("Open Folder")
        open_btn.setFont(QFont("Arial", 14, QFont.Bold))
        open_btn.setFixedSize(220, 50)
        open_btn.setObjectName("accent_btn")
        open_btn.clicked.connect(self.browse_folder)
        btn_container = QHBoxLayout()
        btn_container.setAlignment(Qt.AlignCenter)
        btn_container.addWidget(open_btn)
        layout.addLayout(btn_container)

        # Direct path entry for network/mapped drives the dialog can't see
        path_row = QHBoxLayout()
        path_row.setAlignment(Qt.AlignCenter)
        self.path_entry = QLineEdit()
        self.path_entry.setPlaceholderText("Or type/paste a folder path (e.g. F:\\APS Drive\\Job Files\\...)")
        self.path_entry.setFixedWidth(400)
        self.path_entry.returnPressed.connect(self._open_typed_path)
        path_go_btn = QPushButton("Go")
        path_go_btn.setFixedWidth(50)
        path_go_btn.clicked.connect(self._open_typed_path)
        path_row.addWidget(self.path_entry)
        path_row.addWidget(path_go_btn)
        layout.addLayout(path_row)

        layout.addSpacing(20)

        # Recent projects list
        recent_label = QLabel("Recent Projects")
        recent_label.setFont(QFont("Arial", 11))
        recent_label.setObjectName("muted_label")
        recent_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(recent_label)

        self.recent_list = QListWidget()
        self.recent_list.setMaximumWidth(500)
        self.recent_list.setMaximumHeight(150)
        self.recent_list.setStyleSheet("font-size: 12px;")
        self.recent_list.itemDoubleClicked.connect(self._on_recent_project_clicked)
        recent_container = QHBoxLayout()
        recent_container.setAlignment(Qt.AlignCenter)
        recent_container.addWidget(self.recent_list)
        layout.addLayout(recent_container)

        # Settings button
        settings_btn = QPushButton("Settings")
        settings_btn.setStyleSheet("padding: 6px 16px; font-size: 12px;")
        settings_btn.clicked.connect(self.open_settings)
        settings_container = QHBoxLayout()
        settings_container.setAlignment(Qt.AlignCenter)
        settings_container.addWidget(settings_btn)
        layout.addLayout(settings_container)

        layout.addStretch(3)
        return page

    def _create_workspace_page(self):
        """Create the workspace page: file browser (left) + chat (right)."""
        page = QWidget()
        page_layout = QVBoxLayout()
        page_layout.setContentsMargins(4, 4, 4, 4)
        page_layout.setSpacing(4)
        page.setLayout(page_layout)

        # Top toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        back_btn = QPushButton("< Back")
        back_btn.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        back_btn.clicked.connect(lambda: self.stacked.setCurrentIndex(0))
        toolbar.addWidget(back_btn)

        self.folder_name_label = QLabel("No folder loaded")
        self.folder_name_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.folder_name_label.setStyleSheet("padding: 2px 8px;")
        toolbar.addWidget(self.folder_name_label, stretch=1)

        self.workspace_status_label = QLabel("")
        self.workspace_status_label.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        toolbar.addWidget(self.workspace_status_label)

        settings_btn = QPushButton("Settings")
        settings_btn.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        settings_btn.clicked.connect(self.open_settings)
        toolbar.addWidget(settings_btn)

        page_layout.addLayout(toolbar)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(14)
        page_layout.addWidget(self.progress_bar)

        # Main splitter: file browser (left) + chat (right)
        self.main_splitter = QSplitter(Qt.Horizontal)

        # LEFT: Two-section file browser
        self.main_splitter.addWidget(self._create_file_browser_panel())

        # RIGHT: Chat panel
        self.main_splitter.addWidget(self._create_chat_panel())

        self.main_splitter.setSizes([300, 900])
        self.main_splitter.setStretchFactor(0, 0)  # File browser fixed width
        self.main_splitter.setStretchFactor(1, 1)  # Chat stretches

        page_layout.addWidget(self.main_splitter, stretch=1)
        return page

    def _create_file_browser_panel(self):
        """Create the two-section file browser (VS Code workspace explorer style)."""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        panel.setLayout(layout)

        # Section 1: CR2A app folder (auto-collapsed)
        cr2a_header = QPushButton("CR2A")
        cr2a_header.setObjectName("section_header")
        cr2a_header.setCheckable(True)
        cr2a_header.setChecked(False)  # Auto-collapsed
        layout.addWidget(cr2a_header)

        # CR2A folder tree (templates, prompts)
        self.cr2a_tree = QTreeView()
        self.cr2a_tree.setMaximumHeight(0)  # Collapsed
        self.cr2a_tree.setHeaderHidden(True)
        self.cr2a_tree.setStyleSheet("font-size: 11px;")
        self.cr2a_tree.doubleClicked.connect(self._on_file_double_clicked)

        # Set up CR2A file model — only show prompts/ and templates/ folders
        self.cr2a_model = QFileSystemModel()
        app_dir = str(Path(__file__).resolve().parent.parent)
        self.cr2a_model.setRootPath(app_dir)
        self.cr2a_proxy = CR2AFolderFilterProxy(app_dir, self)
        self.cr2a_proxy.setSourceModel(self.cr2a_model)
        self.cr2a_tree.setModel(self.cr2a_proxy)
        self.cr2a_tree.setRootIndex(self.cr2a_proxy.mapFromSource(self.cr2a_model.index(app_dir)))
        # Hide size, type, date columns
        for col in range(1, 4):
            self.cr2a_tree.hideColumn(col)

        layout.addWidget(self.cr2a_tree)

        # Toggle CR2A section
        def toggle_cr2a(checked):
            self.cr2a_tree.setMaximumHeight(200 if checked else 0)
        cr2a_header.toggled.connect(toggle_cr2a)

        # Section 2: User's bid folder (expanded)
        self.bid_folder_header = QPushButton("Bid Folder")
        self.bid_folder_header.setObjectName("section_header")
        layout.addWidget(self.bid_folder_header)

        self.bid_tree = QTreeView()
        self.bid_tree.setHeaderHidden(True)
        self.bid_tree.setStyleSheet("font-size: 11px;")
        self.bid_tree.doubleClicked.connect(self._on_file_double_clicked)

        self.bid_model = QFileSystemModel()
        self.bid_model.setNameFilters(["*.pdf", "*.docx", "*.txt", "*.xlsx", "*.xls"])
        self.bid_model.setNameFilterDisables(False)
        self.bid_tree.setModel(self.bid_model)
        for col in range(1, 4):
            self.bid_tree.hideColumn(col)

        layout.addWidget(self.bid_tree, stretch=1)

        return panel

    def _on_file_double_clicked(self, index):
        """Handle double-click on a file in the browser — open with OS default."""
        model = index.model()
        # Unwrap proxy model to get to QFileSystemModel
        if isinstance(model, QSortFilterProxyModel):
            source_index = model.mapToSource(index)
            source_model = model.sourceModel()
        else:
            source_index = index
            source_model = model
        if source_model and not source_model.isDir(source_index):
            file_path = source_model.filePath(source_index)
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))

    def _on_recent_project_clicked(self, item):
        """Handle double-click on a recent project."""
        folder_path = item.data(Qt.UserRole)
        if folder_path and os.path.isdir(folder_path):
            self._open_folder(folder_path)
    
    def _create_chat_panel(self):
        """Create the main chat panel with message display and input."""
        chat_panel = QWidget()
        chat_layout = QVBoxLayout()
        chat_layout.setContentsMargins(4, 0, 4, 4)
        chat_layout.setSpacing(4)
        chat_panel.setLayout(chat_layout)

        # Chat message display — scrollable list of ChatMessageWidget frames
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setStyleSheet("padding: 4px; font-size: 13px; border: none;")
        self._chat_container = QWidget()
        self._chat_layout = QVBoxLayout()
        self._chat_layout.setContentsMargins(8, 8, 8, 8)
        self._chat_layout.setSpacing(4)
        self._chat_layout.addStretch()  # push messages to top initially
        self._chat_container.setLayout(self._chat_layout)
        self.chat_scroll.setWidget(self._chat_container)
        chat_layout.addWidget(self.chat_scroll)

        # Backward-compat alias so old code referencing self.chat_history doesn't crash
        self.chat_history = self.chat_scroll

        # Inline status indicator (replaces progress bar for chat operations)
        self.chat_status_label = QLabel("")
        self.chat_status_label.setObjectName("chat_status")
        self.chat_status_label.setStyleSheet(
            "font-size: 11px; padding: 4px 8px; font-style: italic;"
        )
        self.chat_status_label.setVisible(False)
        chat_layout.addWidget(self.chat_status_label)

        # Quick action buttons
        action_bar = QHBoxLayout()
        action_bar.setSpacing(4)

        for label, cmd in [
            ("Run Bid Review", "Run a full bid review"),
            ("Analyze Contract", "Run a full contract analysis"),
            ("Extract Specs", "Run specs extraction"),
        ]:
            btn = QPushButton(label)
            btn.setObjectName("quick_action_btn")
            btn.setStyleSheet("padding: 4px 10px; font-size: 11px;")
            btn.clicked.connect(lambda checked, c=cmd: self._send_quick_command(c))
            action_bar.addWidget(btn)

        action_bar.addStretch()
        chat_layout.addLayout(action_bar)

        # Chat input
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        self.question_input = QLineEdit()
        self.question_input.setPlaceholderText("Ask about the contract, or request an analysis...")
        self.question_input.setStyleSheet("padding: 10px; font-size: 13px;")
        self.question_input.returnPressed.connect(self.send_question)
        input_layout.addWidget(self.question_input)
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_question)
        self.send_btn.setObjectName("accent_btn")
        self.send_btn.setStyleSheet("padding: 10px 20px; font-size: 13px; font-weight: bold;")
        input_layout.addWidget(self.send_btn)
        chat_layout.addLayout(input_layout)

        return chat_panel

    # Map quick command text to tool names for direct execution
    _QUICK_COMMAND_TOOLS = {
        "Run a full bid review": "run_full_bid_review",
        "Run a full contract analysis": "run_full_contract_analysis",
        "Run specs extraction": "run_specs_extraction",
    }

    def _send_quick_command(self, command):
        """Execute a quick action — bypass ReAct loop and call the tool directly."""
        tool_name = self._QUICK_COMMAND_TOOLS.get(command)

        if not tool_name or not self.tool_registry:
            # Fallback to chat if tool not found
            self.question_input.setText(command)
            self.send_question()
            return

        if not self.contract_text:
            QMessageBox.warning(self, "No Contract", "Please open a folder and load documents first.")
            return

        # Display user message
        self._log_to_chat('user', command, 'You:')
        self.send_btn.setEnabled(False)
        self.statusBar().showMessage("Processing...")
        self.chat_status_label.setText(f"Running {tool_name}...")
        self.chat_status_label.setVisible(True)

        # Execute tool directly in a background thread (no ReAct loop)
        self._quick_tool_thread = QuickToolThread(self.tool_registry, tool_name)
        self._quick_tool_thread.finished_signal.connect(self._on_quick_tool_finished)
        self._quick_tool_thread.error_signal.connect(self._on_quick_tool_error)
        self._quick_tool_thread.progress_signal.connect(self._on_quick_tool_progress)
        self._quick_tool_thread.item_complete_signal.connect(self._on_quick_tool_item)
        self._quick_tool_thread.start()

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
        self.structured_view.feedback_accepted.connect(self.on_feedback_accepted)
        self.structured_view.feedback_corrected.connect(self.on_feedback_corrected)
        self.structured_view.clause_added.connect(self.on_clause_added)
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
        """Create the simplified menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        open_folder_action = QAction("Open Folder...", self)
        open_folder_action.triggered.connect(self.browse_folder)
        file_menu.addAction(open_folder_action)

        open_workbook_action = QAction("Open Analysis Workbook", self)
        open_workbook_action.triggered.connect(self.open_analysis_workbook)
        file_menu.addAction(open_workbook_action)

        file_menu.addSeparator()

        settings_action = QAction("Settings...", self)
        settings_action.triggered.connect(self.open_settings)
        file_menu.addAction(settings_action)

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
            # Apply theme immediately
            self.apply_theme()
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

    def open_analysis_workbook(self):
        """Open the CR2A analysis Excel workbook with the default application."""
        if not self.excel_builder:
            QMessageBox.information(
                self, "No Workbook",
                "No analysis workbook available.\n\n"
                "Load a contract or folder first to create the workbook."
            )
            return
        path = self.excel_builder.excel_path
        if not path.exists():
            QMessageBox.information(
                self, "No Workbook",
                f"Workbook not found at:\n{path}\n\n"
                "Load a contract or folder first."
            )
            return
        from PyQt5.QtCore import QUrl
        from PyQt5.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

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
        chat_text = self._get_chat_plain_text()
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
            chat_text = self._get_chat_plain_text()
            
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

        # Contract analysis (Sections II-V)
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
        }

        sections = [
            ('administrative_and_commercial_terms', result.administrative_and_commercial_terms),
            ('technical_and_performance_terms', result.technical_and_performance_terms),
            ('legal_risk_and_enforcement', result.legal_risk_and_enforcement),
            ('regulatory_and_compliance_terms', result.regulatory_and_compliance_terms),
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
        """Initialize analysis and query engines with configured AI backend."""
        backend = self.config_manager.get_ai_backend() if self.config_manager else "local"

        # Clear previous engine so a failed init doesn't leave a stale backend
        self.analysis_engine = None
        self.query_engine = None

        if backend == "claude":
            self._init_engines_claude()
        else:
            self._init_engines_local()

        # Update tool registry if it already exists (e.g. after settings change)
        if self.tool_registry and self.analysis_engine:
            self.tool_registry.analysis_engine = self.analysis_engine
            ai_client = self.analysis_engine.ai_client
            self.tool_registry.query_engine = self.query_engine
            if hasattr(self, 'bid_review_engine') and self.bid_review_engine:
                self.bid_review_engine.ai_client = ai_client

    def _init_engines_claude(self):
        """Initialize engines with Claude API backend."""
        try:
            import anthropic  # noqa: F401 — verify package is installed
        except ImportError:
            self.statusBar().showMessage("anthropic package not installed")
            QMessageBox.critical(
                self, "Missing Package",
                "The 'anthropic' Python package is not installed.\n\n"
                "Install it with:  pip install anthropic"
            )
            return

        try:
            claude_model = self.config_manager.get_claude_model() if self.config_manager else "claude-sonnet"
            logger.info(f"Initializing Claude API engine: {claude_model}")
            self.statusBar().showMessage(f"Connecting to Claude API ({claude_model})...")

            from src.api_key_manager import ApiKeyManager
            mgr = ApiKeyManager(self.config_manager)
            api_key = mgr.get_key()

            if not api_key:
                self.statusBar().showMessage("Claude API key required. Go to Settings to configure.")
                QMessageBox.warning(
                    self, "API Key Required",
                    "No Anthropic API key found.\n\n"
                    "Set the ANTHROPIC_API_KEY environment variable\n"
                    "or enter your key in Settings → AI Backend."
                )
                return

            self.analysis_engine = AnalysisEngine(
                ai_backend="claude",
                api_key=api_key,
                claude_model=claude_model,
            )

            from src.document_retriever import DocumentRetriever
            self.retriever = DocumentRetriever()

        except Exception as e:
            logger.error(f"Failed to create Claude analysis engine: {e}", exc_info=True)
            self.analysis_engine = None
            QMessageBox.critical(self, "Engine Error", f"Failed to initialize Claude API:\n\n{e}")
            return

        try:
            self.statusBar().showMessage(f"Validating Claude API key...")
            self.analysis_engine.ai_client.ensure_loaded()
            self.query_engine = QueryEngine(
                self.analysis_engine.ai_client,
                retriever=self.retriever
            )
            model_id = self.analysis_engine.ai_client.model
            self.statusBar().showMessage(f"Ready (Claude API: {model_id})")
            logger.info("Claude API engine initialized successfully")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to validate Claude API: {error_msg}", exc_info=True)
            # Engine exists but API key is bad — keep engine for document loading
            # but create query engine without AI so chat still works for non-AI features
            self.statusBar().showMessage("Claude API unavailable — check key and connection")
            QMessageBox.warning(
                self,
                "Claude API Error",
                f"Failed to connect to Claude API:\n\n{error_msg}\n\n"
                "Document loading still works, but AI analysis requires a valid key.\n\n"
                "Options:\n"
                "1. Check your API key in Settings\n"
                "2. Verify internet connection\n"
                "3. Switch to Local AI in Settings"
            )

    def _init_engines_local(self):
        """Initialize engines with local Llama model backend."""
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

            gpu_mode = self.config_manager.get_gpu_mode() if self.config_manager else "auto"
            gpu_backend = self.config_manager.get_gpu_backend() if self.config_manager else "auto"
            ram_reserved_os_mb = self.config_manager.get_ram_reserved_os_mb() if self.config_manager else None
            gpu_offload_layers = self.config_manager.get_gpu_offload_layers() if self.config_manager else None
            self.analysis_engine = AnalysisEngine(
                local_model_name=model_name,
                gpu_mode=gpu_mode,
                gpu_backend=gpu_backend,
                ram_reserved_os_mb=ram_reserved_os_mb,
                gpu_offload_layers=gpu_offload_layers,
            )

            from src.document_retriever import DocumentRetriever
            self.retriever = DocumentRetriever()

        except Exception as e:
            logger.error(f"Failed to create analysis engine: {e}", exc_info=True)
            QMessageBox.critical(self, "Engine Error", f"Failed to initialize analysis engine:\n\n{e}")
            return

        # Load the AI model separately so a model failure doesn't block contract loading.
        # llama_cpp's Llama() constructor is not thread-safe on Windows, so load on main thread.
        try:
            model_name = self.config_manager.get_local_model_name() if self.config_manager else "llama-3.2-3b-q4"
            self.statusBar().showMessage(f"Loading AI model into memory ({model_name})...")
            self.analysis_engine.ai_client.ensure_loaded()
            self.query_engine = QueryEngine(
                self.analysis_engine.ai_client,
                retriever=self.retriever
            )
            self.statusBar().showMessage(f"Ready (Local AI: {model_name})")
            logger.info("Local AI engine initialized successfully")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to load AI model: {error_msg}", exc_info=True)
            # Null out the broken AI client so AI-dependent tools fail early
            # with a clear message instead of retrying the broken model load.
            self.analysis_engine.ai_client = None
            self.statusBar().showMessage("AI model unavailable — load contract and document features still work")
            QMessageBox.critical(
                self,
                "AI Initialization Error",
                f"Failed to initialize local AI model:\n\n{error_msg}\n\n"
                "Contract loading and document features still work.\n\n"
                "Options:\n"
                "1. Try a different model in Settings\n"
                "2. Check available memory (need 8GB+ RAM)\n"
                "3. Ensure model is downloaded (Settings → Manage Models)\n"
                "4. Switch to Claude API in Settings → AI Backend"
            )
    
    def browse_file(self):
        """Open file browser."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Contract File",
            "",
            "All Supported (*.pdf *.docx *.txt *.xlsx);;PDF Files (*.pdf);;Word Files (*.docx);;Text Files (*.txt);;Excel Files (*.xlsx)"
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
        """Open folder browser — the only entry point for loading documents."""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Contract Folder",
            "",
            QFileDialog.ShowDirsOnly
        )
        if folder_path:
            self._open_folder(folder_path)

    def _open_typed_path(self):
        """Open a folder from the manually typed path entry."""
        path = self.path_entry.text().strip()
        if not path:
            return
        if os.path.isdir(path):
            self._open_folder(path)
        else:
            QMessageBox.warning(self, "Invalid Path", f"Folder not found:\n\n{path}")

    def _open_folder(self, folder_path):
        """Open a bid folder: validate, switch to workspace page, and start loading."""
        from pathlib import Path

        folder = Path(folder_path)

        # Find all supported files in folder (recursive — includes subfolders)
        supported_exts = {'.pdf', '.docx', '.txt', '.xlsx'}
        # Exclude CR2A output files and temp files
        exclude_names = {"cr2a_analysis.xlsx", "template.xlsx"}
        cr2a_storage = folder / ".cr2a"
        files = []
        for f in folder.rglob("*"):
            if not f.is_file():
                continue
            if f.suffix.lower() not in supported_exts:
                continue
            # Skip .cr2a storage directory
            try:
                f.relative_to(cr2a_storage)
                continue
            except ValueError:
                pass
            # Skip CR2A output files and Excel temp files
            if f.name.lower() in exclude_names:
                continue
            if f.name.startswith("~$"):
                continue
            files.append(f)

        if not files:
            QMessageBox.warning(
                self,
                "No Files Found",
                f"No supported contract files found in:\n{folder_path}\n\n"
                f"Supported formats: PDF, DOCX, TXT, XLSX"
            )
            return

        files = sorted(files, key=lambda f: f.name.lower())

        # Update state
        self.upload_mode = "folder"
        self.current_folder = folder_path
        self.folder_files = files
        self.current_file = str(files[0])  # Primary file for session matching

        # Switch to workspace page
        self.stacked.setCurrentIndex(1)

        # Update file browser to show this folder
        self.bid_folder_header.setText(f"{folder.name} ({len(files)} files)")
        self.folder_name_label.setText(folder.name)
        self.bid_model.setRootPath(folder_path)
        self.bid_tree.setRootIndex(self.bid_model.index(folder_path))

        # Welcome chat message
        self._log_to_chat('system', f'Opened folder: {folder.name} ({len(files)} files)')
        # Show relative paths so user can see subfolder structure
        def _rel_name(f):
            try:
                rel = f.relative_to(folder)
                return str(rel) if str(rel) != f.name else f.name
            except ValueError:
                return f.name
        file_list = ", ".join(_rel_name(f) for f in files[:8])
        if len(files) > 8:
            file_list += f", +{len(files) - 8} more"
        self._log_to_chat('log', f'Files: {file_list}')
        self._log_to_chat('log', 'Loading documents...')

        # Save to recent projects
        self._add_recent_project(folder_path, folder.name)

        # Start folder load automatically
        self._load_folder()

    def _load_folder(self):
        """Load all folder files as combined context (no AI)."""
        if not self.analysis_engine:
            QMessageBox.warning(self, "Error", "Analysis engine not initialized.")
            return

        if not self.folder_files:
            QMessageBox.warning(self, "Error", "No folder selected.")
            return

        # Reset previous state
        self.prepared_contract = None
        self.prepared_bid_review = None
        self.category_results = {}
        self.current_analysis = None

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
                self._init_excel_builder()
                if self.session_manager:
                    self.session_manager.set_contract_info(
                        contract_file=f"{len(self.folder_files)} files",
                        contract_file_path=self.current_folder,
                        upload_mode=self.upload_mode,
                    )
            else:
                logger.warning(f"Project folder not writable: {error}")
                self._log_to_chat('error',
                    f"Cannot save results to this folder: {error}\n"
                    "Analysis will run but results won't be saved to Excel or session.")
        except Exception as e:
            logger.warning(f"Project storage init failed: {e}")
            self._log_to_chat('error',
                f"Project storage initialization failed: {e}\n"
                "Analysis will run but results won't be saved.")

        # Update UI
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.workspace_status_label.setText("Loading files...")
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
            self._init_excel_builder()

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

            # History tab removed in Phase 2 (chat-first UI)
            # self.init_history_tab()

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
        if self.tabs:
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

        # Extract clauses from each section
        sections = [
            'administrative_and_commercial_terms',
            'technical_and_performance_terms',
            'legal_risk_and_enforcement',
            'regulatory_and_compliance_terms',
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
            # Engine wasn't created at all (rare — e.g. config failure). Try to init now.
            self.init_engines()
            if not self.analysis_engine:
                QMessageBox.warning(self, "Error", "Analysis engine not available.")
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
                self._init_excel_builder()
                # Record contract info in session
                if self.session_manager:
                    self.session_manager.set_contract_info(
                        contract_file=os.path.basename(self.current_file),
                        contract_file_path=self.current_file,
                        upload_mode=self.upload_mode,
                    )
            else:
                logger.warning(f"Project folder not writable: {error}")
                self._log_to_chat('error',
                    f"Cannot save results to this folder: {error}\n"
                    "Analysis will run but results won't be saved to Excel or session.")
        except Exception as e:
            logger.warning(f"Project storage init failed: {e}")
            self._log_to_chat('error',
                f"Project storage initialization failed: {e}\n"
                "Analysis will run but results won't be saved.")

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
        self.contract_text = prepared.contract_text

        # Detect contract type from content for knowledge retrieval
        if self.analysis_engine and hasattr(self.analysis_engine, 'knowledge_store'):
            from src.knowledge_store import KnowledgeStore
            prepared.contract_type = KnowledgeStore._detect_contract_type(
                prepared.contract_text or ""
            )

        self.progress_bar.setVisible(False)

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
        self._log_to_chat('log', f'Pattern matching found {regex_count} clause matches across {cat_count} categories')
        self._log_to_chat('log', 'Ready! Ask questions or use the quick action buttons below.')

        self.workspace_status_label.setText(
            f"Loaded: {text_len:,} chars, {regex_count} pattern matches"
        )
        self.statusBar().showMessage(f"Contract loaded: {filename}")

        # Prepare bid review engine (for tool registry)
        from src.bid_review_engine import BidReviewEngine
        ai_client = self.analysis_engine.ai_client if self.analysis_engine else None
        self.bid_review_engine = BidReviewEngine(ai_client)
        self.prepared_bid_review = self.bid_review_engine.prepare_bid_review(
            contract_text=self.contract_text,
            file_path=self.current_file or "",
            page_count=getattr(self, '_page_count', 0),
            file_size_bytes=getattr(self, '_file_size_bytes', 0),
        )

        # Initialize tool registry for chat-based tool calling
        self._init_tool_registry()

        # Attempt to restore previous session for this contract
        self._try_restore_session()

        # Refresh file browser to show any new files (e.g., CR2A_Analysis.xlsx)
        if self.current_folder:
            self.bid_model.setRootPath(self.current_folder)

    def on_prepare_error(self, error):
        """Handle contract preparation error."""
        self.progress_bar.setVisible(False)
        self.workspace_status_label.setText(f"Load failed: {error}")
        self.statusBar().showMessage("Load failed")
        self._log_to_chat('error', str(error), 'Load Error')
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
        if self.structured_view:
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
        """Handle single category analysis completion.

        clause_block may be a single dict or a list of dicts when the AI
        found multiple distinct clause instances for the same category.
        """
        # Normalise to a list
        if isinstance(clause_block, dict):
            clause_blocks = [clause_block]
        elif isinstance(clause_block, list):
            clause_blocks = clause_block
        else:
            return

        # Store result — keep first block as the canonical result for
        # session persistence and tool-registry (backward compat)
        primary = clause_blocks[0]
        self.category_results[cat_key] = primary

        # Auto-save to session
        if self.session_manager:
            self.session_manager.update_category_result(cat_key, primary)
            self.session_manager.save()

        # Auto-save to Excel workbook — write all instances
        if self.excel_builder:
            contract_file = os.path.basename(self.current_file) if self.current_file else ""
            self.excel_builder.update_contract_category_multi(
                cat_key, clause_blocks, contract_file
            )

        # Sync to tool registry
        if self.tool_registry:
            self.tool_registry.category_results[cat_key] = primary

        # Log to chat panel — with feedback buttons
        instance_count = len(clause_blocks)
        for i, block in enumerate(clause_blocks):
            if isinstance(block, dict):
                summary = block.get('Clause Summary', '')
                location = block.get('Clause Location', '')
                logger.info(f"Chat log block {i} for {cat_key}: "
                           f"summary={repr(summary[:80] if summary else '')}, "
                           f"location={repr(location)}, keys={list(block.keys())}")
            else:
                summary = ''
                location = ''
                logger.warning(f"Chat log block {i} for {cat_key}: not a dict, type={type(block)}")
            label = f'Analyzed: {display_name}'
            if instance_count > 1:
                label += f' ({i + 1}/{instance_count})'
            # Build visible content lines
            lines = []
            if summary:
                lines.append(summary)
            if location:
                lines.append(f'Location: {location}')
            content = '\n'.join(lines) if lines else '(no details returned)'
            self._log_to_chat('summary', content, label,
                              cat_key=cat_key, clause_block=block)

        # Update structured view with results
        if self.structured_view and self.analysis_engine:
            self.structured_view.fill_single_category(
                cat_key, clause_blocks, self.analysis_engine.CATEGORY_MAP
            )
            self.structured_view.update_category_status(
                cat_key, "analyzed", self.analysis_engine.CATEGORY_MAP
            )

        # Build current analysis for chat/export
        self._rebuild_current_analysis()

        self.statusBar().showMessage(f"Analyzed: {display_name}")
        self.workspace_status_label.setText(
            f"Analyzed: {display_name} ({len(self.category_results)} categories done)"
        )

    def on_feedback_accepted(self, cat_key: str, clause_block: dict):
        """Save accepted result as pattern knowledge."""
        if not self.analysis_engine or not self.analysis_engine.knowledge_store:
            return
        summary = clause_block.get('Clause Summary') or clause_block.get('clause_summary', '')
        if not summary:
            return
        source = os.path.basename(self.current_file) if self.current_file else "unknown"
        contract_type = getattr(self.prepared_contract, 'contract_type', '') if self.prepared_contract else ''
        try:
            store = self.analysis_engine.knowledge_store
            store.save_pattern(cat_key, contract_type, summary, source)
            display = cat_key.replace('_', ' ').title()
            stats = store.get_stats(contract_type)
            self._log_to_chat('info',
                f'Saved as good example for future analyses. '
                f'Knowledge base: {stats}',
                f'Knowledge: {display}')
            self.statusBar().showMessage(f"Pattern saved for {display}")

            # Auto-update profile for this contract type
            if contract_type:
                try:
                    store.update_profile(contract_type)
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Failed to save pattern for {cat_key}: {e}")

    def on_feedback_corrected(self, cat_key: str, original_data: dict, corrected_text: str):
        """Save correction as knowledge."""
        if not self.analysis_engine or not self.analysis_engine.knowledge_store:
            return
        original = original_data.get('Clause Summary') or original_data.get('clause_summary', '')
        source = os.path.basename(self.current_file) if self.current_file else "unknown"
        contract_type = getattr(self.prepared_contract, 'contract_type', '') if self.prepared_contract else ''
        was_missed = original_data.get('_was_missed', False)

        # Extract lesson if embedded in corrected text
        lesson = ""
        corrected_summary = corrected_text
        if "\n[LESSON: " in corrected_text:
            parts = corrected_text.rsplit("\n[LESSON: ", 1)
            corrected_summary = parts[0]
            lesson = parts[1].rstrip("]") if len(parts) > 1 else ""

        try:
            self.analysis_engine.knowledge_store.save_correction(
                cat_key, contract_type, original, corrected_summary, lesson, source,
                was_missed=was_missed
            )
            display = cat_key.replace('_', ' ').title()
            kind = "missed clause" if was_missed else "correction"
            # Show knowledge stats
            store = self.analysis_engine.knowledge_store
            stats = store.get_stats(contract_type)
            self._log_to_chat('info',
                f'Saved {kind} for future analyses. '
                f'Knowledge base: {stats}',
                f'Knowledge: {display}')
            self.statusBar().showMessage(f"Correction saved for {display}")

            # Auto-update profile for this contract type
            if contract_type:
                try:
                    store.update_profile(contract_type)
                except Exception:
                    pass

            # Update the displayed result with the corrected text
            corrected_block = dict(original_data)
            corrected_block['Clause Summary'] = corrected_summary
            if not corrected_block.get('Clause Location'):
                corrected_block['Clause Location'] = 'User-provided'
            corrected_block.pop('_was_missed', None)
            self.on_category_complete(cat_key,
                self.analysis_engine.CATEGORY_MAP.get(cat_key, ('', cat_key))[1],
                corrected_block)
        except Exception as e:
            logger.warning(f"Failed to save correction for {cat_key}: {e}")

    def on_clause_added(self, cat_key: str, clause_block: dict):
        """Handle user manually adding an additional clause instance."""
        display_name = cat_key.replace('_', ' ').title()
        if self.analysis_engine:
            mapping = self.analysis_engine.CATEGORY_MAP.get(cat_key)
            if mapping:
                display_name = mapping[1]

        # Log to chat
        summary = clause_block.get('Clause Summary', '')
        location = clause_block.get('Clause Location', '')
        self._log_to_chat('summary', f'{summary}\nLocation: {location}',
                          f'Added by user: {display_name}',
                          cat_key=cat_key, clause_block=clause_block)

        # Save to Excel if available
        if self.excel_builder and self.current_file:
            contract_file = os.path.basename(self.current_file)
            self.excel_builder.update_contract_category_multi(
                cat_key, [clause_block], contract_file
            )

        self.statusBar().showMessage(f"Added clause: {display_name}")

    def _extract_overview_async(self):
        """Contract overview extraction removed — section no longer displayed."""
        pass

    def _init_tool_registry(self):
        """Initialize the tool registry for chat-based tool calling."""
        try:
            from src.tool_registry import ToolRegistry
            self.tool_registry = ToolRegistry(
                analysis_engine=self.analysis_engine,
                bid_review_engine=self.bid_review_engine,
                query_engine=self.query_engine,
                prepared_contract=self.prepared_contract,
                prepared_bid_review=self.prepared_bid_review,
                excel_builder=self.excel_builder,
            )
            logger.info("Tool registry initialized with %d tools", len(self.tool_registry.get_tool_names()))
        except Exception as e:
            logger.warning("Failed to initialize tool registry: %s", e)
            self.tool_registry = None

    def _add_recent_project(self, folder_path, folder_name):
        """Add a folder to the recent projects list."""
        # Check for duplicates
        for i in range(self.recent_list.count()):
            item = self.recent_list.item(i)
            if item.data(Qt.UserRole) == folder_path:
                # Move to top
                self.recent_list.takeItem(i)
                break

        item = QListWidgetItem(f"{folder_name}  —  {folder_path}")
        item.setData(Qt.UserRole, folder_path)
        self.recent_list.insertItem(0, item)

        # Keep max 10
        while self.recent_list.count() > 10:
            self.recent_list.takeItem(self.recent_list.count() - 1)

    def _init_excel_builder(self):
        """Initialize the Excel template builder for the current project."""
        if not self.project_storage:
            return
        try:
            from src.excel_template_builder import ExcelTemplateBuilder
            # Gather contract file names
            contract_files = []
            if self.upload_mode == "folder" and self.folder_files:
                contract_files = [os.path.basename(f) for f in self.folder_files]
            elif self.current_file:
                contract_files = [os.path.basename(self.current_file)]
            self.excel_builder = ExcelTemplateBuilder(
                self.project_storage.project_root, contract_files
            )
            path = self.excel_builder.initialize_workbook()
            logger.info("Excel workbook ready: %s", path)
        except Exception as e:
            logger.warning("Failed to initialize Excel builder: %s", e)
            self.excel_builder = None

    def on_category_not_found(self, cat_key, prompt='', response=''):
        """Handle category not found by AI."""
        if self.session_manager:
            self.session_manager.mark_category_not_found(cat_key)
            self.session_manager.save()
        mapping = self.analysis_engine.CATEGORY_MAP.get(cat_key)
        name = mapping[1] if mapping else cat_key
        self._log_to_chat('not_found', f'Not found in contract: {name}',
                          cat_key=cat_key)
        # Update structured view with not-found status and content
        if self.structured_view and self.analysis_engine:
            not_found_data = {'Clause Location': 'Not found', 'Clause Summary': ''}
            self.structured_view.fill_single_category(
                cat_key, not_found_data, self.analysis_engine.CATEGORY_MAP
            )
            self.structured_view.update_category_status(
                cat_key, "not_found", self.analysis_engine.CATEGORY_MAP
            )
        self.statusBar().showMessage(f"Not found: {name}")

    def on_category_error(self, cat_key, error_msg):
        """Handle single category analysis error."""
        mapping = self.analysis_engine.CATEGORY_MAP.get(cat_key) if self.analysis_engine else None
        name = mapping[1] if mapping else cat_key
        self._log_to_chat('error', f'{name}: {error_msg}', 'Analysis Error')
        if self.structured_view and self.analysis_engine:
            self.structured_view.update_category_status(
                cat_key, "error", self.analysis_engine.CATEGORY_MAP
            )
        self.statusBar().showMessage(f"Error analyzing {name}: {error_msg}")
        logger.error(f"Category analysis error for {cat_key}: {error_msg}")

    def analyze_all(self):
        """Analyze all categories sequentially."""
        if not self.prepared_contract:
            QMessageBox.warning(self, "Error", "No contract loaded.")
            return
        if not self.analysis_engine:
            QMessageBox.warning(self, "Error", "Analysis engine not initialized.")
            return

        # Prevent concurrent model access
        if self.chat_thread and self.chat_thread.isRunning():
            self._log_to_chat('log', 'Please wait for the current task to finish.')
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.send_btn.setEnabled(False)
        self._log_to_chat('system', 'Starting full contract analysis...')

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
        self.send_btn.setEnabled(True)

        count = len(self.category_results)
        self.workspace_status_label.setText(f"Analysis complete: {count} categories")
        self.statusBar().showMessage("Analysis complete")
        self._log_to_chat('system', f'Contract analysis complete: {count} categories analyzed. Results saved to Excel.')

        self._rebuild_current_analysis(include_overview=True)

        if self.current_analysis:
            self._auto_save_analysis(self.current_analysis)

        # Refresh file browser
        if self.current_folder:
            self.bid_model.setRootPath(self.current_folder)

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

        if self.specs_tab:
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

        # Auto-save to Excel workbook
        if self.excel_builder:
            self.excel_builder.update_specs(text)

    def on_bid_review_analysis_requested(self):
        """Handle bid review analysis request from Bid Review tab."""
        logger.info("Bid review analysis requested")
        if not self.contract_text:
            QMessageBox.warning(
                self, "No Contract",
                "No contract text available. Load a contract first."
            )
            return

        # Allow bid review even without AI — regex-only mode
        ai_client = None
        if self.analysis_engine and self.analysis_engine.ai_client:
            ai_client = self.analysis_engine.ai_client
        else:
            logger.warning("AI client not available — bid review will use regex-only mode")

        # Prevent concurrent model access (llama_cpp not thread-safe)
        if ai_client and self.active_category_thread and self.active_category_thread.isRunning():
            QMessageBox.warning(
                self, "Please Wait",
                "A contract analysis is in progress on the Contract tab.\n"
                "Please wait for it to finish before running bid review."
            )
            return

        if not self.bid_review_tab:
            return

        # Reuse engine/prepared if already set during contract load, else create
        bid_engine = self.bid_review_tab.bid_engine
        prepared = self.bid_review_tab.prepared
        if not bid_engine or not prepared:
            from src.bid_review_engine import BidReviewEngine
            bid_engine = BidReviewEngine(ai_client)
            prepared = bid_engine.prepare_bid_review(
                contract_text=self.contract_text,
                file_path=self.file_label.text() if hasattr(self, 'file_label') else "",
                page_count=getattr(self, '_page_count', 0),
                file_size_bytes=getattr(self, '_file_size_bytes', 0),
            )

        # Start analysis on the tab
        logger.info("Starting bid review analysis (AI available: %s)", ai_client is not None)
        self.bid_review_tab.start_analysis(bid_engine, prepared)

    def _on_bid_item_session_save(self, item_key, display_name, item):
        """Auto-save a single bid review item and log to chat."""
        if self.session_manager and hasattr(item, 'to_dict'):
            self.session_manager.update_bid_review_item(item_key, item.to_dict())
            self.session_manager.save()

        # Auto-save to Excel workbook
        if self.excel_builder:
            self.excel_builder.update_bid_review_item(item_key, item)

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

        # Auto-save full bid review to Excel workbook
        if self.excel_builder and result:
            count = self.excel_builder.update_bid_review_full(result)
            logger.info("Excel: wrote %d bid review items", count)

        self._log_to_chat('system', 'Bid Review complete. Results saved to Excel workbook.')

    def _try_restore_session(self):
        """Attempt to restore a previous session for the loaded contract."""
        if not self.session_manager:
            return

        if not self.session_manager.load():
            return

        if not self.session_manager.has_session_for(self.current_file):
            logger.info("Session file is for a different contract, skipping restore")
            self.session_manager.clear()
            return

        # --- Restore category_results ---
        saved_categories = self.session_manager.category_results
        if saved_categories:
            self.category_results = dict(saved_categories)
            logger.info("Restored %d category results from session", len(self.category_results))

        # --- Rebuild current_analysis for chat/export ---
        if self.category_results:
            self._rebuild_current_analysis()

        # --- Sync tool registry with restored results ---
        if self.tool_registry:
            self.tool_registry.category_results = dict(self.category_results)

        # --- Restore bid review items (to tool registry) ---
        bid_items = self.session_manager.bid_review_item_results
        if bid_items and self.tool_registry:
            from src.bid_review_models import ChecklistItem
            for item_key, item_dict in bid_items.items():
                try:
                    item = ChecklistItem.from_dict(item_dict)
                    self.tool_registry.bid_item_results[item_key] = item
                except Exception:
                    pass

        # --- Load chat history into panel ---
        self._load_chat_history_for_contract()

        # --- Rebuild Excel workbook from restored session ---
        if self.excel_builder:
            contract_file = os.path.basename(self.current_file) if self.current_file else ""
            for cat_key, clause_block in self.category_results.items():
                self.excel_builder.update_contract_category(cat_key, clause_block, contract_file)
            if bid_items:
                from src.bid_review_models import ChecklistItem
                for item_key, item_dict in bid_items.items():
                    try:
                        item = ChecklistItem.from_dict(item_dict)
                        self.excel_builder.update_bid_review_item(item_key, item)
                    except Exception:
                        pass

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
            self.workspace_status_label.setText(f"Restored: {summary}")
            self.statusBar().showMessage("Previous session restored")
            self._log_to_chat('system', f"Previous session restored ({summary}). You can ask questions or continue analyzing.")

    def _restore_bid_review(self, result_dict, item_results_dict):
        """Restore bid review tab from saved session data."""
        if not self.bid_review_tab:
            return

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
            self.current_analysis = self.analysis_engine.build_comprehensive_result(
                self.prepared_contract,
                self.category_results,
                overview=None
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
        
        # Pass the contract file path so location fields can be rendered as hyperlinks
        if self.structured_view:
            self.structured_view.set_contract_file_path(self.current_file)

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

    def _log_to_chat(self, msg_type: str, content: str, title: str = None,
                     cat_key: str = None, clause_block: dict = None):
        """
        Append a styled message widget to the chat panel.

        Args:
            msg_type: 'system', 'log', 'prompt', 'response', 'summary',
                      'not_found', 'user', 'answer', 'error', 'info'
            content: Message text (supports markdown for 'answer' type)
            title: Optional bold title line
            cat_key: Category key for feedback buttons (summary/not_found messages)
            clause_block: Clause data dict for feedback (summary messages)
        """
        t = getattr(self, '_current_theme', THEMES['light'])

        widget = ChatMessageWidget(
            msg_type=msg_type,
            content=content,
            title=title,
            theme=t,
            parent=self._chat_container,
            cat_key=cat_key,
            clause_block=clause_block,
        )

        # Wire feedback signals to main window handlers
        if cat_key:
            widget.feedback_accepted.connect(self.on_feedback_accepted)
            widget.feedback_corrected.connect(self.on_feedback_corrected)
            widget.feedback_found.connect(self._on_chat_feedback_found)

        # Insert before the stretch at the bottom
        count = self._chat_layout.count()
        self._chat_layout.insertWidget(count - 1, widget)

        # Limit visible messages to prevent performance issues
        max_messages = 300
        while self._chat_layout.count() > max_messages + 1:  # +1 for stretch
            item = self._chat_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        # Auto-scroll to bottom
        QApplication.processEvents()
        scrollbar = self.chat_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_chat_feedback_found(self, cat_key: str):
        """Handle 'I Found This' from a not_found chat message — opens correction dialog."""
        # This is handled by the ChatMessageWidget's _on_found which emits feedback_corrected
        pass

    def _clear_chat_display(self):
        """Remove all message widgets from the chat scroll area."""
        while self._chat_layout.count() > 1:  # keep the stretch
            item = self._chat_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

    def _get_chat_plain_text(self):
        """Extract plain text from all chat message widgets."""
        lines = []
        for i in range(self._chat_layout.count()):
            item = self._chat_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), (ChatMessageWidget, QLabel)):
                w = item.widget()
                label = getattr(w, 'message_label', w)
                lines.append(label.text())
        # Strip HTML tags for plain text
        import re
        plain = "\n".join(lines)
        plain = re.sub(r'<[^>]+>', '', plain)
        return plain

    def send_question(self):
        """Send a question — uses ReAct tool calling if available, else direct query."""
        question = self.question_input.text().strip()
        if not question:
            return

        if not self.contract_text:
            QMessageBox.warning(self, "No Contract", "Please open a folder and load documents first.")
            return

        # Display user message
        self._log_to_chat('user', question, 'You:')
        self.question_input.clear()
        self.send_btn.setEnabled(False)
        self.statusBar().showMessage("Processing...")

        # Store in conversation history
        self.conversation_messages.append({"role": "user", "content": question})

        # Route: ReAct tool calling (preferred) or direct query (fallback)
        ai_client = self.analysis_engine.ai_client if self.analysis_engine else None

        if ai_client and self.tool_registry:
            # ReAct-style tool calling via ChatOrchestrationThread
            self.chat_thread = ChatOrchestrationThread(
                ai_client, self.tool_registry, question,
                conversation_history=self.conversation_messages[-6:]
            )
            # Initialize streaming state
            self._streaming_tokens = []
            self._streaming_active = False

            self.chat_thread.token_stream.connect(self._on_token_stream)
            self.chat_thread.message.connect(self._on_chat_message)
            self.chat_thread.tool_started.connect(self._on_tool_started)
            self.chat_thread.tool_finished.connect(self._on_tool_finished)
            self.chat_thread.finished.connect(self._on_chat_finished)
            self.chat_thread.error.connect(self.on_query_error)
            self.chat_thread.progress.connect(self._on_chat_progress)
            self.chat_thread.start()

            # Show inline status
            self.chat_status_label.setText("Thinking...")
            self.chat_status_label.setVisible(True)
        elif self.query_engine:
            # Fallback: direct query without tools
            analysis = self.get_or_build_current_analysis()
            analysis_dict = analysis.to_dict() if analysis else {
                'metadata': {'filename': os.path.basename(self.current_file or ''), 'schema_version': 'minimal'}
            }
            self.query_thread = QueryThread(self.query_engine, question, analysis_dict)
            self.query_thread.finished.connect(self.on_query_complete)
            self.query_thread.error.connect(self.on_query_error)
            self.query_thread.start()
        else:
            self._log_to_chat('error', 'AI engine not available. Check Settings.', 'Error')
            self.send_btn.setEnabled(True)

    def _on_token_stream(self, token_text):
        """Handle a single streamed token — append to chat in real-time."""
        if not self._streaming_active:
            # First token: start a new streaming message widget
            self._streaming_active = True
            self._streaming_tokens = [token_text]
            t = getattr(self, '_current_theme', THEMES['light'])
            # Create a streaming label widget
            self._streaming_label = QLabel()
            self._streaming_label.setWordWrap(True)
            self._streaming_label.setTextFormat(Qt.RichText)
            self._streaming_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self._streaming_label.setStyleSheet(
                f"padding: 8px; background: {t['answer_bg']}; "
                f"border-left: 3px solid {t['answer_border']}; margin: 4px 0;"
            )
            self._streaming_label.setText(
                f"<b>CR2A:</b><br>{html_module.escape(token_text)}"
            )
            count = self._chat_layout.count()
            self._chat_layout.insertWidget(count - 1, self._streaming_label)
        else:
            self._streaming_tokens.append(token_text)
            # Update the streaming label with all tokens so far
            full_text = "".join(self._streaming_tokens)
            self._streaming_label.setText(
                f"<b>CR2A:</b><br>{html_module.escape(full_text)}"
            )

        # Auto-scroll
        scrollbar = self.chat_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_chat_progress(self, status, percent):
        """Update inline status indicator for chat operations."""
        self.chat_status_label.setText(f"{status}")
        self.chat_status_label.setVisible(True)

    def _on_chat_message(self, role, content):
        """Handle incremental chat message from ReAct loop."""
        # If we were streaming, the final answer was already shown token-by-token
        if role == "assistant" and self._streaming_active:
            self._streaming_active = False
            self._streaming_tokens = []
            return  # Already displayed via streaming

        if role == "thought":
            self._log_to_chat('log', content, 'Thinking:')
        elif role == "assistant":
            self._log_to_chat('answer', content, 'CR2A:')
        elif role == "error":
            self._log_to_chat('error', content, 'Error:')

    def _on_tool_started(self, tool_call, args_str):
        """Handle tool execution start."""
        # End any active streaming before showing tool activity
        if self._streaming_active:
            self._streaming_active = False
            self._streaming_tokens = []
        self._log_to_chat('log', f'Running: {tool_call}')

    def _on_tool_finished(self, tool_name, result_preview):
        """Handle tool execution completion."""
        if result_preview:
            self._log_to_chat('summary', result_preview)

    def _on_chat_finished(self, messages):
        """Handle ReAct chat loop completion."""
        self._streaming_active = False
        self._streaming_tokens = []
        self.send_btn.setEnabled(True)
        self.statusBar().showMessage("Ready")
        self.chat_status_label.setVisible(False)
        self.progress_bar.setVisible(False)

        # Store assistant response in conversation history
        for msg in messages:
            if msg.get("role") == "assistant":
                self.conversation_messages.append(msg)
                break

        # Update Excel and session after tool calls
        self._sync_tool_results_to_session()

        # Refresh file browser to show updated Excel
        if self.current_folder:
            self.bid_model.setRootPath(self.current_folder)
    
    def _on_quick_tool_finished(self, tool_name, result):
        """Handle direct tool execution completion."""
        self._log_to_chat('summary', result[:500] if len(result) > 500 else result, f'{tool_name}')
        self._log_to_chat('system', 'Complete.')
        self.send_btn.setEnabled(True)
        self.statusBar().showMessage("Ready")
        self.chat_status_label.setVisible(False)

        # Sync tool registry results to session manager
        self._sync_tool_results_to_session(tool_name)

        # Refresh file browser to show updated Excel
        if self.current_folder:
            self.bid_model.setRootPath(self.current_folder)

    def _on_quick_tool_item(self, item_type, key, display_name, data):
        """Handle per-item results from running tools — display each in chat."""
        if item_type == 'bid_review':
            value = data.get('value', '')
            location = data.get('location', '')
            page = data.get('page', '')
            confidence = data.get('confidence', '')
            notes = data.get('notes', '')

            if confidence == 'not_found':
                self._log_to_chat('not_found', f'Not found: {display_name}',
                                  cat_key=key)
            else:
                parts = [f'Value: {value}']
                if location:
                    parts.append(f'Location: {location}')
                if page:
                    parts.append(f'Page: {page}')
                parts.append(f'Confidence: {confidence}')
                if notes:
                    parts.append(f'Notes: {notes}')
                self._log_to_chat('summary', '\n'.join(parts), f'Bid Review: {display_name}',
                                  cat_key=key, clause_block=data)

        elif item_type == 'contract':
            summary = data.get('Clause Summary', '')
            location = data.get('Clause Location', '')
            self._log_to_chat('summary', f'{summary}\nLocation: {location}',
                              f'Analyzed: {display_name}',
                              cat_key=key, clause_block=data)
            # Also store in category_results for session persistence
            self.category_results[key] = data

        elif item_type == 'contract_not_found':
            self._log_to_chat('not_found', f'Not found in contract: {display_name}',
                              cat_key=key)

    def _on_quick_tool_progress(self, message, pct):
        """Handle per-item progress from a running tool."""
        self.chat_status_label.setText(message)
        self.statusBar().showMessage(f"Processing... {pct}%")

    def _on_quick_tool_error(self, error_msg):
        """Handle direct tool execution error."""
        self._log_to_chat('error', error_msg, 'Error:')
        self.send_btn.setEnabled(True)
        self.statusBar().showMessage("Ready")
        self.chat_status_label.setVisible(False)

    def _sync_tool_results_to_session(self, tool_name=None):
        """Sync tool registry results (categories, bid items, specs) to session storage."""
        if not self.tool_registry:
            return

        if not self.session_manager:
            logger.warning("Session manager not available — results will not be persisted to disk")

        dirty = False

        # Sync category results
        for cat_key, clause_block in self.tool_registry.category_results.items():
            if cat_key not in self.category_results:
                self.category_results[cat_key] = clause_block
            if self.session_manager:
                self.session_manager.update_category_result(cat_key, clause_block)
                dirty = True

        # Sync bid review item results
        for item_key, item in self.tool_registry.bid_item_results.items():
            if self.session_manager:
                item_dict = item.to_dict() if hasattr(item, 'to_dict') else item
                self.session_manager.update_bid_review_item(item_key, item_dict)
                dirty = True

        # Sync specs text (store in session as a pseudo-category)
        if self.tool_registry.specs_text and self.session_manager:
            self.session_manager.update_category_result(
                '_specs', {'Clause Summary': self.tool_registry.specs_text}
            )
            dirty = True

        if dirty and self.session_manager:
            self.session_manager.save()
            logger.info("Session saved after tool completion (tool=%s)", tool_name)

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
            self._clear_chat_display()

            # Display welcome message
            self._log_to_chat('system', f'Welcome to CR2A Chat!\nLoaded {len(chats)} previous conversation(s) for {filename}')

            # Display all previous chats with user attribution
            for chat in chats:
                username = chat.get('username', 'unknown')
                computer_name = chat.get('computer_name', 'unknown')
                question = chat.get('question', '')
                answer = chat.get('answer', '')

                # Display question
                self._log_to_chat('user', question, f'User ({username}@{computer_name})')

                # Display answer
                self._log_to_chat('answer', answer, 'Answer')

            logger.info(f"Loaded {len(chats)} chat entries for {filename}")

        except Exception as e:
            logger.error(f"Failed to load chat history: {e}", exc_info=True)


class SettingsDialog(QDialog):
    """Settings dialog with hardware detection, RAM partition slider, and GPU offload slider."""

    def __init__(self, parent, config_manager):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(580)

        # Detect hardware once on open
        from src.hardware_info import detect_hardware, estimate_os_ram_mb, RUNTIME_OVERHEAD_MB
        self._RUNTIME_OVERHEAD_MB = RUNTIME_OVERHEAD_MB
        self.hw_info = detect_hardware()
        self._os_ram_snapshot = estimate_os_ram_mb()

        # Import model registry for slider calculations
        from src.model_manager import ModelManager
        self._model_registry = ModelManager.MODEL_REGISTRY

        # Block signals during init to prevent premature updates
        self._initializing = True
        self.init_ui()
        self.load_settings()
        self._initializing = False

        # Initial update of derived displays
        self._on_model_changed()

    def init_ui(self):
        """Initialize the dialog UI."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # =====================================================================
        # 0. Appearance
        # =====================================================================
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QHBoxLayout()
        appearance_group.setLayout(appearance_layout)

        appearance_layout.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Light", "light")
        self.theme_combo.addItem("Dark", "dark")
        appearance_layout.addWidget(self.theme_combo)
        appearance_layout.addStretch()

        layout.addWidget(appearance_group)

        # =====================================================================
        # 0b. AI Backend Selection
        # =====================================================================
        backend_group = QGroupBox("AI Backend")
        backend_layout = QVBoxLayout()
        backend_group.setLayout(backend_layout)

        backend_row = QHBoxLayout()
        backend_row.addWidget(QLabel("Backend:"))
        self.backend_combo = QComboBox()
        self.backend_combo.addItem("Local AI (Offline)", "local")
        self.backend_combo.addItem("Claude API (Cloud)", "claude")
        self.backend_combo.currentIndexChanged.connect(self._on_backend_changed)
        backend_row.addWidget(self.backend_combo)
        backend_row.addStretch()
        backend_layout.addLayout(backend_row)

        # Claude-specific controls (hidden by default)
        self.claude_widget = QWidget()
        claude_form = QFormLayout()
        claude_form.setContentsMargins(0, 6, 0, 0)
        self.claude_widget.setLayout(claude_form)

        self.claude_model_combo = QComboBox()
        self.claude_model_combo.addItem("Claude Sonnet (Faster / Lower Cost)", "claude-sonnet")
        self.claude_model_combo.addItem("Claude Opus (Highest Quality)", "claude-opus")
        claude_form.addRow("Model:", self.claude_model_combo)

        api_key_row = QHBoxLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("sk-ant-...")
        api_key_row.addWidget(self.api_key_input)

        self.show_key_btn = QPushButton("Show")
        self.show_key_btn.setCheckable(True)
        self.show_key_btn.setFixedWidth(50)
        self.show_key_btn.toggled.connect(
            lambda checked: self.api_key_input.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        api_key_row.addWidget(self.show_key_btn)

        self.test_key_btn = QPushButton("Test")
        self.test_key_btn.setFixedWidth(50)
        self.test_key_btn.clicked.connect(self._test_api_key)
        api_key_row.addWidget(self.test_key_btn)
        claude_form.addRow("API Key:", api_key_row)

        self.api_key_status = QLabel("")
        self.api_key_status.setStyleSheet("color: #666; font-size: 11px;")
        claude_form.addRow("", self.api_key_status)

        self.claude_widget.hide()
        backend_layout.addWidget(self.claude_widget)

        layout.addWidget(backend_group)

        # =====================================================================
        # A. System Hardware Info (read-only)
        # =====================================================================
        hw_group = QGroupBox("System Hardware")
        hw_form = QFormLayout()
        hw_group.setLayout(hw_form)

        cpu_text = f"{self.hw_info.cpu_name} ({self.hw_info.cpu_cores}C/{self.hw_info.cpu_threads}T)"
        hw_form.addRow("CPU:", QLabel(cpu_text))

        ram_total_gb = self.hw_info.total_ram_mb / 1024
        ram_avail_gb = self.hw_info.available_ram_mb / 1024
        hw_form.addRow("RAM:", QLabel(f"{ram_total_gb:.1f} GB total, {ram_avail_gb:.1f} GB available"))

        if self.hw_info.gpu_name:
            gpu_text = f"{self.hw_info.gpu_name} ({self.hw_info.gpu_type})"
            if self.hw_info.gpu_vram_mb:
                gpu_text += f" — {self.hw_info.gpu_vram_mb / 1024:.1f} GB VRAM"
        else:
            gpu_text = "No dedicated GPU detected"
        hw_form.addRow("GPU:", QLabel(gpu_text))

        layout.addWidget(hw_group)

        # =====================================================================
        # B. Quick Setup (preset buttons)
        # =====================================================================
        preset_group = QGroupBox("Quick Setup")
        preset_layout = QHBoxLayout()
        preset_group.setLayout(preset_layout)

        self.fast_btn = QPushButton("Fast")
        self.fast_btn.setToolTip("3B model, minimal GPU offload, modest RAM usage")
        self.fast_btn.clicked.connect(lambda: self._apply_preset("fast"))
        preset_layout.addWidget(self.fast_btn)

        self.balanced_btn = QPushButton("Balanced")
        self.balanced_btn.setToolTip("Best model that fits comfortably in your RAM")
        self.balanced_btn.clicked.connect(lambda: self._apply_preset("balanced"))
        preset_layout.addWidget(self.balanced_btn)

        self.quality_btn = QPushButton("High Quality")
        self.quality_btn.setToolTip("8B Q4 model for highest quality analysis")
        self.quality_btn.clicked.connect(lambda: self._apply_preset("quality"))
        preset_layout.addWidget(self.quality_btn)

        # Disable presets that won't fit
        total = self.hw_info.total_ram_mb
        self.fast_btn.setEnabled(total >= 4096)       # 3B needs ~3GB + OS
        self.balanced_btn.setEnabled(total >= 4096)
        self.quality_btn.setEnabled(total >= 8192)     # 8B Q4 needs ~6GB + OS

        layout.addWidget(preset_group)

        # =====================================================================
        # C. Model Selection & Threads
        # =====================================================================
        model_group = QGroupBox("AI Model (Local)")
        model_layout = QVBoxLayout()
        model_group.setLayout(model_layout)

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
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        model_form.addRow("Model:", self.model_combo)

        self.threads_spinner = QSpinBox()
        self.threads_spinner.setRange(1, 32)
        self.threads_spinner.setValue(0)
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
        # D. RAM Partition Slider
        # =====================================================================
        ram_group = QGroupBox("RAM Allocation")
        ram_layout = QVBoxLayout()
        ram_group.setLayout(ram_layout)

        ram_layout.addWidget(QLabel("Drag to allocate RAM between OS and model:"))

        self.ram_slider = QSlider(Qt.Horizontal)
        self.ram_slider.setTickPosition(QSlider.TicksBelow)
        self.ram_slider.setTickInterval(512)
        # Range set in _on_model_changed(); value = ram_reserved_os_mb
        self.ram_slider.valueChanged.connect(self._update_ram_display)
        ram_layout.addWidget(self.ram_slider)

        # Labels below slider: OS side (left) and Model side (right)
        ram_labels = QHBoxLayout()
        self.ram_os_label = QLabel("OS & Apps: -- GB")
        self.ram_model_label = QLabel("Model: -- GB")
        self.ram_model_label.setAlignment(Qt.AlignRight)
        ram_labels.addWidget(self.ram_os_label)
        ram_labels.addStretch()
        ram_labels.addWidget(self.ram_model_label)
        ram_layout.addLayout(ram_labels)

        # Breakdown label
        self.ram_breakdown_label = QLabel("")
        self.ram_breakdown_label.setStyleSheet("color: #666;")
        ram_layout.addWidget(self.ram_breakdown_label)

        # Warning label (hidden by default)
        self.ram_warning_label = QLabel("")
        self.ram_warning_label.setStyleSheet("color: red; font-weight: bold;")
        self.ram_warning_label.hide()
        ram_layout.addWidget(self.ram_warning_label)

        layout.addWidget(ram_group)

        # =====================================================================
        # E. GPU Backend & Offload
        # =====================================================================
        self.gpu_group = QGroupBox("GPU Acceleration")
        gpu_layout = QVBoxLayout()
        self.gpu_group.setLayout(gpu_layout)

        # Backend selection dropdown
        backend_row = QHBoxLayout()
        backend_row.addWidget(QLabel("Compute Backend:"))
        self.gpu_backend_combo = QComboBox()
        self._populate_backend_combo()
        backend_row.addWidget(self.gpu_backend_combo, 1)
        gpu_layout.addLayout(backend_row)

        # Backend status label
        self.backend_status_label = QLabel("")
        self.backend_status_label.setStyleSheet("color: #666; font-size: 11px;")
        gpu_layout.addWidget(self.backend_status_label)
        self._update_backend_status()

        # GPU offload slider
        gpu_layout.addWidget(QLabel("GPU Layer Offload:"))
        self.gpu_slider = QSlider(Qt.Horizontal)
        self.gpu_slider.setTickPosition(QSlider.TicksBelow)
        self.gpu_slider.setTickInterval(1)
        self.gpu_slider.setMinimum(0)
        self.gpu_slider.setMaximum(32)  # updated in _on_model_changed
        self.gpu_slider.valueChanged.connect(self._update_gpu_label)
        gpu_layout.addWidget(self.gpu_slider)

        self.gpu_offload_label = QLabel("0 of 0 layers  --  0 GB")
        gpu_layout.addWidget(self.gpu_offload_label)

        if self.hw_info.gpu_type == "integrated":
            gpu_layout.addWidget(QLabel("(Shared RAM — GPU offload uses system memory)"))

        # GPU warning label
        self.gpu_warning_label = QLabel("")
        self.gpu_warning_label.setStyleSheet("color: red; font-weight: bold;")
        self.gpu_warning_label.hide()
        gpu_layout.addWidget(self.gpu_warning_label)

        # Only show GPU group if a GPU is detected
        self.gpu_group.setVisible(self.hw_info.gpu_type != "none")
        layout.addWidget(self.gpu_group)

        # Track local-only groups for visibility toggling
        self._local_only_groups = [hw_group, preset_group, model_group, ram_group, self.gpu_group]

        # =====================================================================
        # F. Dialog Buttons
        # =====================================================================
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_backend_changed(self):
        """Toggle visibility of local vs Claude controls."""
        is_claude = self.backend_combo.currentData() == "claude"
        self.claude_widget.setVisible(is_claude)
        for group in self._local_only_groups:
            group.setVisible(not is_claude)

    def _test_api_key(self):
        """Test the entered Anthropic API key."""
        key = self.api_key_input.text().strip()
        if not key:
            self.api_key_status.setText("Enter an API key first.")
            self.api_key_status.setStyleSheet("color: orange; font-size: 11px;")
            return

        self.api_key_status.setText("Testing...")
        self.api_key_status.setStyleSheet("color: #666; font-size: 11px;")
        QApplication.processEvents()

        try:
            from src.api_key_manager import ApiKeyManager
            mgr = ApiKeyManager(self.config_manager)
            if mgr.validate_key(key):
                self.api_key_status.setText("Valid — connected to Claude API.")
                self.api_key_status.setStyleSheet("color: green; font-size: 11px;")
            else:
                self.api_key_status.setText("Invalid key or connection failed.")
                self.api_key_status.setStyleSheet("color: red; font-size: 11px;")
        except Exception as e:
            self.api_key_status.setText(f"Error: {e}")
            self.api_key_status.setStyleSheet("color: red; font-size: 11px;")

    def _get_selected_model_info(self):
        """Return MODEL_REGISTRY entry for currently selected model."""
        model_key = self.model_combo.currentData()
        return model_key, self._model_registry.get(model_key, {})

    def _on_model_changed(self):
        """Update slider ranges when the model selection changes."""
        model_key, info = self._get_selected_model_info()
        if not info:
            return

        total = self.hw_info.total_ram_mb
        size_mb = info.get("size_mb", 2020)
        num_layers = info.get("num_layers", 28)

        # RAM slider: min = OS floor, max = total - model weights minimum
        os_floor = max(2048, self._os_ram_snapshot)
        model_floor = size_mb + self._RUNTIME_OVERHEAD_MB
        ram_max = max(os_floor, total - model_floor)

        self.ram_slider.setMinimum(os_floor)
        self.ram_slider.setMaximum(ram_max)

        # If current value is out of range, clamp it
        if self.ram_slider.value() < os_floor:
            self.ram_slider.setValue(os_floor)
        elif self.ram_slider.value() > ram_max:
            self.ram_slider.setValue(ram_max)

        # GPU slider: 0 to num_layers
        self.gpu_slider.setMaximum(num_layers)
        if self.gpu_slider.value() > num_layers:
            self.gpu_slider.setValue(num_layers)

        self._update_ram_display()
        self._update_gpu_label()

    def _update_ram_display(self):
        """Update RAM partition labels and breakdown."""
        if self._initializing:
            return

        total = self.hw_info.total_ram_mb
        os_reserved = self.ram_slider.value()
        model_ram = total - os_reserved

        self.ram_os_label.setText(f"OS & Apps: {os_reserved / 1024:.1f} GB")
        self.ram_model_label.setText(f"Model: {model_ram / 1024:.1f} GB")

        # Compute breakdown
        model_key, info = self._get_selected_model_info()
        if info:
            from src.hardware_info import get_ram_breakdown
            gpu_layers = self.gpu_slider.value() if self.gpu_group.isVisible() else 0
            breakdown = get_ram_breakdown(
                total_model_ram_mb=model_ram,
                model_key=model_key,
                gpu_offload_layers=gpu_layers,
                gpu_type=self.hw_info.gpu_type,
            )
            tokens = breakdown["estimated_tokens"]
            token_str = f"{tokens:,}" if tokens > 0 else "0"
            parts = [f"Weights: {breakdown['weights_mb'] / 1024:.1f} GB"]
            if breakdown["gpu_offload_mb"] > 0:
                parts.append(f"GPU offload: {breakdown['gpu_offload_mb'] / 1024:.1f} GB")
            parts.append(f"Context cache: {breakdown['context_cache_mb'] / 1024:.1f} GB")
            parts.append(f"~{token_str} tokens")
            self.ram_breakdown_label.setText("  |  ".join(parts))

            # Warning check
            self._check_allocation_warnings(model_ram, breakdown)

    def _populate_backend_combo(self):
        """Populate the GPU backend dropdown with detected backends."""
        from src.backend_registry import detect_available_backends, get_display_name
        self.gpu_backend_combo.clear()
        self.gpu_backend_combo.addItem("Auto (best available)", "auto")
        backends = detect_available_backends()
        for b in backends:
            display = get_display_name(b.name)
            if not b.available:
                display += f"  [{b.reason}]"
            self.gpu_backend_combo.addItem(display, b.name)
            idx = self.gpu_backend_combo.count() - 1
            if not b.available:
                # Gray out unavailable backends
                model = self.gpu_backend_combo.model()
                item = model.item(idx)
                item.setEnabled(False)
                if b.install_hint:
                    self.gpu_backend_combo.setItemData(idx, b.install_hint, Qt.ToolTipRole)
        # Set current selection from config
        current = self.config_manager.get_gpu_backend()
        for i in range(self.gpu_backend_combo.count()):
            if self.gpu_backend_combo.itemData(i) == current:
                self.gpu_backend_combo.setCurrentIndex(i)
                break
        self.gpu_backend_combo.currentIndexChanged.connect(self._update_backend_status)

    def _update_backend_status(self):
        """Update the backend status label."""
        from src.backend_registry import get_best_backend, get_display_name
        idx = self.gpu_backend_combo.currentIndex()
        pref = self.gpu_backend_combo.itemData(idx) if idx >= 0 else "auto"
        best = get_best_backend(pref or "auto")
        if best.available:
            name = get_display_name(best.name)
            self.backend_status_label.setText(f"Active: {name} — {best.reason}")
            self.backend_status_label.setStyleSheet("color: #080; font-size: 11px;")
        else:
            self.backend_status_label.setText(f"No GPU backend available — CPU only")
            self.backend_status_label.setStyleSheet("color: #c60; font-size: 11px;")

    def _update_gpu_label(self):
        """Update GPU slider label showing layers and GB."""
        if self._initializing:
            return

        model_key, info = self._get_selected_model_info()
        layers = self.gpu_slider.value()
        num_layers = info.get("num_layers", 28) if info else 28
        mb_per_layer = info.get("mb_per_layer", 100) if info else 100

        gb = (layers * mb_per_layer) / 1024
        self.gpu_offload_label.setText(
            f"{layers} of {num_layers} layers  --  ~{gb:.2f} GB"
        )

        # For integrated GPUs, GPU changes affect RAM breakdown
        if self.hw_info.gpu_type == "integrated":
            self._update_ram_display()

    def _check_allocation_warnings(self, model_ram_mb, breakdown):
        """Show/hide warnings if allocations exceed available memory."""
        total_needed = (
            breakdown["weights_mb"]
            + breakdown["gpu_offload_mb"]
            + self._RUNTIME_OVERHEAD_MB
        )

        if total_needed > model_ram_mb:
            self.ram_warning_label.setText(
                "Warning: Model weights + GPU offload exceed available model RAM"
            )
            self.ram_warning_label.show()
        elif breakdown["estimated_tokens"] < 512:
            self.ram_warning_label.setText(
                "Warning: Very low context window — increase model RAM or reduce GPU offload"
            )
            self.ram_warning_label.show()
        else:
            self.ram_warning_label.hide()

    def _apply_preset(self, preset: str):
        """Apply a Quick Setup preset."""
        total = self.hw_info.total_ram_mb
        has_gpu = self.hw_info.gpu_type != "none"

        if preset == "fast":
            self.model_combo.setCurrentIndex(
                self.model_combo.findData("llama-3.2-3b-q4"))
            os_reserved = max(2048, self._os_ram_snapshot)
            self.ram_slider.setValue(min(os_reserved + 1024, self.ram_slider.maximum()))
            if has_gpu:
                self.gpu_slider.setValue(0)

        elif preset == "balanced":
            if total >= 12288:
                # 12+ GB: use 8B Q3 (lighter 8B)
                self.model_combo.setCurrentIndex(
                    self.model_combo.findData("llama-3.1-8b-q3"))
            else:
                # Under 12 GB: use 3B
                self.model_combo.setCurrentIndex(
                    self.model_combo.findData("llama-3.2-3b-q4"))
            os_reserved = max(2048, self._os_ram_snapshot)
            self.ram_slider.setValue(min(os_reserved + 512, self.ram_slider.maximum()))
            if has_gpu:
                num_layers = self._model_registry.get(
                    self.model_combo.currentData(), {}).get("num_layers", 28)
                self.gpu_slider.setValue(num_layers // 2)

        elif preset == "quality":
            self.model_combo.setCurrentIndex(
                self.model_combo.findData("llama-3.1-8b-q4"))
            # Give model as much RAM as reasonable
            os_floor = max(2048, self._os_ram_snapshot)
            self.ram_slider.setValue(os_floor)
            if has_gpu:
                num_layers = self._model_registry.get(
                    "llama-3.1-8b-q4", {}).get("num_layers", 32)
                self.gpu_slider.setValue(num_layers)

    def load_settings(self):
        """Load current settings from config manager."""
        if not self.config_manager:
            return

        # Theme
        theme = self.config_manager.get_theme()
        idx = self.theme_combo.findData(theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)

        # AI Backend
        backend = self.config_manager.get_ai_backend()
        idx = self.backend_combo.findData(backend)
        if idx >= 0:
            self.backend_combo.setCurrentIndex(idx)
        self._on_backend_changed()

        # Claude model
        claude_model = self.config_manager.get_claude_model()
        idx = self.claude_model_combo.findData(claude_model)
        if idx >= 0:
            self.claude_model_combo.setCurrentIndex(idx)

        # Load API key from encrypted storage (if available)
        try:
            from src.api_key_manager import ApiKeyManager
            mgr = ApiKeyManager(self.config_manager)
            key = mgr.get_key()
            if key:
                self.api_key_input.setText(key)
                self.api_key_status.setText("Key loaded from storage.")
                self.api_key_status.setStyleSheet("color: #666; font-size: 11px;")
        except Exception:
            pass

        model_name = self.config_manager.get_local_model_name()
        index = self.model_combo.findData(model_name)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)

        threads = self.config_manager.get_local_model_threads()
        if threads is not None:
            self.threads_spinner.setValue(threads)
        else:
            self.threads_spinner.setValue(0)

        # RAM slider
        ram_reserved = self.config_manager.get_ram_reserved_os_mb()
        if ram_reserved is not None:
            self.ram_slider.setValue(ram_reserved)
        else:
            # Default: reserve current OS usage + 1 GB headroom
            default_reserved = min(
                self._os_ram_snapshot + 1024,
                self.hw_info.total_ram_mb - 2048
            )
            self.ram_slider.setValue(max(2048, default_reserved))

        # GPU slider
        gpu_layers = self.config_manager.get_gpu_offload_layers()
        if gpu_layers is not None:
            self.gpu_slider.setValue(gpu_layers)
        else:
            # Default: 0 for CPU-only, all layers if GPU available
            gpu_mode = self.config_manager.get_gpu_mode()
            if gpu_mode == "cpu" or self.hw_info.gpu_type == "none":
                self.gpu_slider.setValue(0)
            else:
                model_key = self.model_combo.currentData()
                num_layers = self._model_registry.get(model_key, {}).get("num_layers", 0)
                self.gpu_slider.setValue(num_layers)

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
            # Save theme
            theme = self.theme_combo.currentData()
            self.config_manager.set_theme(theme)

            # Save AI backend settings
            backend = self.backend_combo.currentData()
            self.config_manager.set_ai_backend(backend)
            self.config_manager.set_claude_model(self.claude_model_combo.currentData())

            # Save API key (encrypted) if entered
            api_key = self.api_key_input.text().strip()
            if api_key:
                try:
                    from src.api_key_manager import ApiKeyManager
                    mgr = ApiKeyManager(self.config_manager)
                    mgr.set_key(api_key)
                except Exception as e:
                    logger.warning("Failed to encrypt API key: %s", e)

            model_name = self.model_combo.currentData()
            self.config_manager.set_local_model_name(model_name)

            threads = self.threads_spinner.value()
            if threads == 0:
                threads = None
            self.config_manager.set_local_model_threads(threads)

            # Save RAM and GPU settings
            self.config_manager.set_ram_reserved_os_mb(self.ram_slider.value())
            gpu_layers = self.gpu_slider.value() if self.gpu_group.isVisible() else None
            self.config_manager.set_gpu_offload_layers(gpu_layers)

            # Save GPU backend preference
            gpu_backend = self.gpu_backend_combo.currentData()
            if gpu_backend:
                self.config_manager.set_gpu_backend(gpu_backend)

            # Derive gpu_mode for backward compat
            if gpu_layers is None or gpu_layers == 0:
                self.config_manager.set_gpu_mode("cpu")
            else:
                self.config_manager.set_gpu_mode("gpu")

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

    # Ensure Qt can find its platform plugins when running from a venv
    import os
    if not os.environ.get('QT_QPA_PLATFORM_PLUGIN_PATH'):
        try:
            import PyQt5
            plugins_path = os.path.join(os.path.dirname(PyQt5.__file__), 'Qt5', 'plugins', 'platforms')
            if os.path.isdir(plugins_path):
                os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugins_path
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look

    window = CR2A_GUI()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

