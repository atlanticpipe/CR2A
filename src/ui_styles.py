"""
UI Styles Module

Defines consistent color schemes, fonts, and button styles for the Unified CR2A Application.
This module provides a centralized style configuration to ensure UI consistency across all screens.
"""

from typing import Dict, Any


class UIStyles:
    """
    Centralized UI style configuration for the CR2A Application.
    
    This class defines:
    - Color scheme (primary, secondary, accent, status colors)
    - Font configurations (sizes, families, weights)
    - Button styles
    - Widget padding and spacing
    - Window dimensions
    """
    
    # ========== Color Scheme ==========
    
    # Primary colors
    PRIMARY_COLOR = "#0066cc"  # Blue - for primary actions and user messages
    PRIMARY_DARK = "#004d99"   # Darker blue - for hover states
    PRIMARY_LIGHT = "#3385d6"  # Lighter blue - for highlights
    
    # Secondary colors
    SECONDARY_COLOR = "#006600"  # Green - for assistant messages and success
    SECONDARY_DARK = "#004d00"   # Darker green
    SECONDARY_LIGHT = "#339933"  # Lighter green
    
    # Neutral colors
    BACKGROUND_COLOR = "#ffffff"      # White - main background
    SURFACE_COLOR = "#f5f5f5"         # Light gray - surface elements
    BORDER_COLOR = "#cccccc"          # Gray - borders
    TEXT_PRIMARY = "#000000"          # Black - primary text
    TEXT_SECONDARY = "#666666"        # Dark gray - secondary text
    TEXT_DISABLED = "#999999"         # Light gray - disabled text
    
    # Status colors
    SUCCESS_COLOR = "#28a745"   # Green - success messages
    ERROR_COLOR = "#dc3545"     # Red - error messages
    WARNING_COLOR = "#ffc107"   # Yellow - warning messages
    INFO_COLOR = "#17a2b8"      # Cyan - info messages
    
    # ========== Font Configuration ==========
    
    # Font family
    FONT_FAMILY = "Segoe UI"  # Primary font for Windows
    FONT_FAMILY_FALLBACK = "Arial"  # Fallback font
    
    # Font sizes
    FONT_SIZE_TITLE = 24        # Main screen titles
    FONT_SIZE_SUBTITLE = 16     # Subtitles and section headers
    FONT_SIZE_LARGE = 12        # Large body text
    FONT_SIZE_NORMAL = 10       # Normal body text
    FONT_SIZE_SMALL = 9         # Small text (status, timestamps)
    FONT_SIZE_TINY = 8          # Tiny text (metadata)
    
    # Font weights
    FONT_WEIGHT_BOLD = "bold"
    FONT_WEIGHT_NORMAL = "normal"
    FONT_WEIGHT_ITALIC = "italic"
    
    # ========== Spacing and Padding ==========
    
    PADDING_SMALL = 5
    PADDING_MEDIUM = 10
    PADDING_LARGE = 20
    PADDING_XLARGE = 40
    
    SPACING_SMALL = 5
    SPACING_MEDIUM = 10
    SPACING_LARGE = 20
    SPACING_XLARGE = 30
    
    # ========== Window Configuration ==========
    
    WINDOW_MIN_WIDTH = 1024
    WINDOW_MIN_HEIGHT = 768
    WINDOW_DEFAULT_WIDTH = 1024
    WINDOW_DEFAULT_HEIGHT = 768
    
    # ========== Widget Dimensions ==========
    
    BUTTON_WIDTH_SMALL = 15
    BUTTON_WIDTH_MEDIUM = 20
    BUTTON_WIDTH_LARGE = 30
    
    PROGRESS_BAR_LENGTH = 500
    
    TEXT_WRAP_LENGTH = 600
    
    # ========== Style Dictionaries ==========
    
    @staticmethod
    def get_title_font() -> tuple:
        """
        Get font configuration for main titles.
        
        Returns:
            Tuple of (family, size, weight)
        """
        return (UIStyles.FONT_FAMILY, UIStyles.FONT_SIZE_TITLE, UIStyles.FONT_WEIGHT_BOLD)
    
    @staticmethod
    def get_subtitle_font() -> tuple:
        """
        Get font configuration for subtitles.
        
        Returns:
            Tuple of (family, size, weight)
        """
        return (UIStyles.FONT_FAMILY, UIStyles.FONT_SIZE_SUBTITLE, UIStyles.FONT_WEIGHT_BOLD)
    
    @staticmethod
    def get_large_font() -> tuple:
        """
        Get font configuration for large body text.
        
        Returns:
            Tuple of (family, size)
        """
        return (UIStyles.FONT_FAMILY, UIStyles.FONT_SIZE_LARGE)
    
    @staticmethod
    def get_normal_font() -> tuple:
        """
        Get font configuration for normal body text.
        
        Returns:
            Tuple of (family, size)
        """
        return (UIStyles.FONT_FAMILY, UIStyles.FONT_SIZE_NORMAL)
    
    @staticmethod
    def get_small_font() -> tuple:
        """
        Get font configuration for small text.
        
        Returns:
            Tuple of (family, size)
        """
        return (UIStyles.FONT_FAMILY, UIStyles.FONT_SIZE_SMALL)
    
    @staticmethod
    def get_tiny_font() -> tuple:
        """
        Get font configuration for tiny text.
        
        Returns:
            Tuple of (family, size)
        """
        return (UIStyles.FONT_FAMILY, UIStyles.FONT_SIZE_TINY)
    
    @staticmethod
    def get_button_config(size: str = "medium") -> Dict[str, Any]:
        """
        Get button configuration dictionary.
        
        Args:
            size: Button size - "small", "medium", or "large"
        
        Returns:
            Dictionary of button configuration options
        """
        width_map = {
            "small": UIStyles.BUTTON_WIDTH_SMALL,
            "medium": UIStyles.BUTTON_WIDTH_MEDIUM,
            "large": UIStyles.BUTTON_WIDTH_LARGE
        }
        
        return {
            "width": width_map.get(size, UIStyles.BUTTON_WIDTH_MEDIUM)
        }
    
    @staticmethod
    def get_status_color(status_type: str) -> str:
        """
        Get color for status messages.
        
        Args:
            status_type: Type of status - "success", "error", "warning", "info", or "default"
        
        Returns:
            Color hex code
        """
        color_map = {
            "success": UIStyles.SUCCESS_COLOR,
            "error": UIStyles.ERROR_COLOR,
            "warning": UIStyles.WARNING_COLOR,
            "info": UIStyles.INFO_COLOR,
            "default": UIStyles.TEXT_SECONDARY
        }
        
        return color_map.get(status_type, UIStyles.TEXT_SECONDARY)
    
    @staticmethod
    def get_frame_padding() -> str:
        """
        Get standard frame padding.
        
        Returns:
            Padding string for ttk.Frame
        """
        return str(UIStyles.PADDING_LARGE)
    
    @staticmethod
    def get_labelframe_padding() -> str:
        """
        Get standard labelframe padding.
        
        Returns:
            Padding string for ttk.LabelFrame
        """
        return str(UIStyles.PADDING_MEDIUM)


# Convenience functions for common style patterns

def apply_title_style(label_widget, text: str) -> None:
    """
    Apply title styling to a label widget.
    
    Args:
        label_widget: Tkinter Label widget
        text: Text to display
    """
    label_widget.config(
        text=text,
        font=UIStyles.get_title_font(),
        anchor="center"
    )


def apply_subtitle_style(label_widget, text: str, color: str = None) -> None:
    """
    Apply subtitle styling to a label widget.
    
    Args:
        label_widget: Tkinter Label widget
        text: Text to display
        color: Optional text color (defaults to secondary text color)
    """
    label_widget.config(
        text=text,
        font=UIStyles.get_large_font(),
        foreground=color or UIStyles.TEXT_SECONDARY,
        anchor="center"
    )


def apply_status_style(label_widget, text: str, status_type: str = "default") -> None:
    """
    Apply status message styling to a label widget.
    
    Args:
        label_widget: Tkinter Label widget
        text: Status message text
        status_type: Type of status - "success", "error", "warning", "info", or "default"
    """
    label_widget.config(
        text=text,
        font=UIStyles.get_small_font(),
        foreground=UIStyles.get_status_color(status_type),
        anchor="center",
        wraplength=UIStyles.TEXT_WRAP_LENGTH
    )
