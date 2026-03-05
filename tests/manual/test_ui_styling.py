"""
Manual Test Script for UI Styling

This script verifies that consistent styling has been applied across all screens.
Run this script to visually inspect the UI and verify:
- Consistent color scheme
- Consistent fonts
- Consistent button styles
- Minimum window size (1024x768)
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import tkinter as tk
from tkinter import ttk
from src.ui_styles import UIStyles


def test_ui_styles():
    """Test UI styles by displaying all style configurations."""
    
    root = tk.Tk()
    root.title("UI Styles Test")
    root.geometry(f"{UIStyles.WINDOW_DEFAULT_WIDTH}x{UIStyles.WINDOW_DEFAULT_HEIGHT}")
    root.minsize(UIStyles.WINDOW_MIN_WIDTH, UIStyles.WINDOW_MIN_HEIGHT)
    
    # Create main frame
    main_frame = ttk.Frame(root, padding=UIStyles.get_frame_padding())
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Create scrollable canvas
    canvas = tk.Canvas(main_frame)
    scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Test title font
    title = ttk.Label(
        scrollable_frame,
        text="UI Styles Test - Title Font",
        font=UIStyles.get_title_font()
    )
    title.pack(pady=UIStyles.PADDING_MEDIUM)
    
    # Test subtitle font
    subtitle = ttk.Label(
        scrollable_frame,
        text="Subtitle Font",
        font=UIStyles.get_subtitle_font()
    )
    subtitle.pack(pady=UIStyles.PADDING_SMALL)
    
    # Test color scheme
    colors_frame = ttk.LabelFrame(
        scrollable_frame,
        text="Color Scheme",
        padding=UIStyles.get_labelframe_padding()
    )
    colors_frame.pack(fill=tk.X, pady=UIStyles.PADDING_MEDIUM, padx=UIStyles.PADDING_LARGE)
    
    colors = [
        ("Primary Color", UIStyles.PRIMARY_COLOR),
        ("Secondary Color", UIStyles.SECONDARY_COLOR),
        ("Success Color", UIStyles.SUCCESS_COLOR),
        ("Error Color", UIStyles.ERROR_COLOR),
        ("Warning Color", UIStyles.WARNING_COLOR),
        ("Info Color", UIStyles.INFO_COLOR),
        ("Text Primary", UIStyles.TEXT_PRIMARY),
        ("Text Secondary", UIStyles.TEXT_SECONDARY),
    ]
    
    for name, color in colors:
        color_frame = ttk.Frame(colors_frame)
        color_frame.pack(fill=tk.X, pady=UIStyles.PADDING_SMALL)
        
        label = ttk.Label(color_frame, text=name, width=20)
        label.pack(side=tk.LEFT)
        
        color_box = tk.Label(
            color_frame,
            text=color,
            bg=color,
            fg="white" if color in [UIStyles.PRIMARY_COLOR, UIStyles.SECONDARY_COLOR, UIStyles.TEXT_PRIMARY] else "black",
            width=15,
            relief=tk.SOLID,
            borderwidth=1
        )
        color_box.pack(side=tk.LEFT, padx=UIStyles.PADDING_SMALL)
    
    # Test fonts
    fonts_frame = ttk.LabelFrame(
        scrollable_frame,
        text="Font Sizes",
        padding=UIStyles.get_labelframe_padding()
    )
    fonts_frame.pack(fill=tk.X, pady=UIStyles.PADDING_MEDIUM, padx=UIStyles.PADDING_LARGE)
    
    fonts = [
        ("Title Font", UIStyles.get_title_font()),
        ("Subtitle Font", UIStyles.get_subtitle_font()),
        ("Large Font", UIStyles.get_large_font()),
        ("Normal Font", UIStyles.get_normal_font()),
        ("Small Font", UIStyles.get_small_font()),
        ("Tiny Font", UIStyles.get_tiny_font()),
    ]
    
    for name, font in fonts:
        label = ttk.Label(fonts_frame, text=f"{name}: The quick brown fox", font=font)
        label.pack(anchor=tk.W, pady=UIStyles.PADDING_SMALL)
    
    # Test buttons
    buttons_frame = ttk.LabelFrame(
        scrollable_frame,
        text="Button Styles",
        padding=UIStyles.get_labelframe_padding()
    )
    buttons_frame.pack(fill=tk.X, pady=UIStyles.PADDING_MEDIUM, padx=UIStyles.PADDING_LARGE)
    
    button_sizes = ["small", "medium", "large"]
    for size in button_sizes:
        config = UIStyles.get_button_config(size)
        btn = ttk.Button(buttons_frame, text=f"{size.capitalize()} Button", **config)
        btn.pack(pady=UIStyles.PADDING_SMALL)
    
    # Test status messages
    status_frame = ttk.LabelFrame(
        scrollable_frame,
        text="Status Message Colors",
        padding=UIStyles.get_labelframe_padding()
    )
    status_frame.pack(fill=tk.X, pady=UIStyles.PADDING_MEDIUM, padx=UIStyles.PADDING_LARGE)
    
    status_types = ["success", "error", "warning", "info", "default"]
    for status_type in status_types:
        color = UIStyles.get_status_color(status_type)
        label = ttk.Label(
            status_frame,
            text=f"{status_type.capitalize()}: This is a {status_type} message",
            font=UIStyles.get_small_font(),
            foreground=color
        )
        label.pack(anchor=tk.W, pady=UIStyles.PADDING_SMALL)
    
    # Test window dimensions
    dimensions_frame = ttk.LabelFrame(
        scrollable_frame,
        text="Window Dimensions",
        padding=UIStyles.get_labelframe_padding()
    )
    dimensions_frame.pack(fill=tk.X, pady=UIStyles.PADDING_MEDIUM, padx=UIStyles.PADDING_LARGE)
    
    dimensions = [
        ("Minimum Width", UIStyles.WINDOW_MIN_WIDTH),
        ("Minimum Height", UIStyles.WINDOW_MIN_HEIGHT),
        ("Default Width", UIStyles.WINDOW_DEFAULT_WIDTH),
        ("Default Height", UIStyles.WINDOW_DEFAULT_HEIGHT),
    ]
    
    for name, value in dimensions:
        label = ttk.Label(dimensions_frame, text=f"{name}: {value}px", font=UIStyles.get_normal_font())
        label.pack(anchor=tk.W, pady=UIStyles.PADDING_SMALL)
    
    # Add some spacing at the bottom
    ttk.Label(scrollable_frame, text="").pack(pady=UIStyles.PADDING_LARGE)
    
    print("UI Styles Test Window Opened")
    print(f"Window size: {UIStyles.WINDOW_DEFAULT_WIDTH}x{UIStyles.WINDOW_DEFAULT_HEIGHT}")
    print(f"Minimum size: {UIStyles.WINDOW_MIN_WIDTH}x{UIStyles.WINDOW_MIN_HEIGHT}")
    print("\nVerify:")
    print("1. All colors are displayed correctly")
    print("2. All fonts are readable and properly sized")
    print("3. Buttons have consistent widths")
    print("4. Window respects minimum size (try resizing)")
    print("5. Spacing and padding are consistent")
    
    root.mainloop()


if __name__ == "__main__":
    test_ui_styles()
