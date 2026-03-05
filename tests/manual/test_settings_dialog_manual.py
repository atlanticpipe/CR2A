"""
Manual test for Settings Dialog

Run this script to manually test the settings dialog UI.
This allows visual verification of the dialog appearance and behavior.
"""

import sys
import os
import tkinter as tk
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.settings_dialog import show_settings_dialog
from src.config_manager import ConfigManager
import tempfile


def test_settings_dialog_not_required():
    """Test settings dialog in non-required mode (can be cancelled)."""
    print("Testing settings dialog (not required)...")
    
    # Create temporary config
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        config_manager = ConfigManager(config_path=str(config_path))
        
        # Create root window
        root = tk.Tk()
        root.title("Settings Dialog Test - Not Required")
        root.geometry("400x300")
        
        # Add label
        label = tk.Label(
            root,
            text="Click the button to open settings dialog\n(Can be cancelled)",
            font=("Segoe UI", 12),
            pady=20
        )
        label.pack()
        
        # Add button to open dialog
        def open_dialog():
            result = show_settings_dialog(
                parent=root,
                config_manager=config_manager,
                required=False,
                on_save_callback=lambda: print("API key saved!")
            )
            
            if result:
                api_key = config_manager.get_openai_key()
                result_label.config(
                    text=f"Saved! API key: {api_key[:10]}...",
                    foreground="green"
                )
            else:
                result_label.config(
                    text="Cancelled",
                    foreground="red"
                )
        
        button = tk.Button(
            root,
            text="Open Settings Dialog",
            command=open_dialog,
            font=("Segoe UI", 11),
            padx=20,
            pady=10
        )
        button.pack(pady=20)
        
        # Result label
        result_label = tk.Label(
            root,
            text="",
            font=("Segoe UI", 10)
        )
        result_label.pack()
        
        root.mainloop()


def test_settings_dialog_required():
    """Test settings dialog in required mode (cannot be cancelled)."""
    print("Testing settings dialog (required)...")
    
    # Create temporary config
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        config_manager = ConfigManager(config_path=str(config_path))
        
        # Create root window
        root = tk.Tk()
        root.title("Settings Dialog Test - Required")
        root.geometry("400x300")
        
        # Add label
        label = tk.Label(
            root,
            text="Click the button to open settings dialog\n(Required - cannot be cancelled)",
            font=("Segoe UI", 12),
            pady=20
        )
        label.pack()
        
        # Add button to open dialog
        def open_dialog():
            result = show_settings_dialog(
                parent=root,
                config_manager=config_manager,
                required=True,
                on_save_callback=lambda: print("API key saved!")
            )
            
            if result:
                api_key = config_manager.get_openai_key()
                result_label.config(
                    text=f"Saved! API key: {api_key[:10]}...",
                    foreground="green"
                )
            else:
                result_label.config(
                    text="Not saved (should not happen in required mode)",
                    foreground="red"
                )
        
        button = tk.Button(
            root,
            text="Open Settings Dialog (Required)",
            command=open_dialog,
            font=("Segoe UI", 11),
            padx=20,
            pady=10
        )
        button.pack(pady=20)
        
        # Result label
        result_label = tk.Label(
            root,
            text="",
            font=("Segoe UI", 10)
        )
        result_label.pack()
        
        root.mainloop()


def test_settings_dialog_with_existing_key():
    """Test settings dialog with an existing API key."""
    print("Testing settings dialog with existing key...")
    
    # Create temporary config
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        config_manager = ConfigManager(config_path=str(config_path))
        
        # Set an existing API key
        config_manager.set_openai_key("sk-existing1234567890abcdef")
        config_manager.save_config()
        
        # Create root window
        root = tk.Tk()
        root.title("Settings Dialog Test - With Existing Key")
        root.geometry("400x300")
        
        # Add label
        label = tk.Label(
            root,
            text="Click the button to open settings dialog\n(Should show existing key)",
            font=("Segoe UI", 12),
            pady=20
        )
        label.pack()
        
        # Add button to open dialog
        def open_dialog():
            result = show_settings_dialog(
                parent=root,
                config_manager=config_manager,
                required=False,
                on_save_callback=lambda: print("API key updated!")
            )
            
            if result:
                api_key = config_manager.get_openai_key()
                result_label.config(
                    text=f"Updated! API key: {api_key[:10]}...",
                    foreground="green"
                )
            else:
                result_label.config(
                    text="Cancelled",
                    foreground="red"
                )
        
        button = tk.Button(
            root,
            text="Open Settings Dialog",
            command=open_dialog,
            font=("Segoe UI", 11),
            padx=20,
            pady=10
        )
        button.pack(pady=20)
        
        # Result label
        result_label = tk.Label(
            root,
            text="",
            font=("Segoe UI", 10)
        )
        result_label.pack()
        
        root.mainloop()


if __name__ == "__main__":
    print("Manual Settings Dialog Tests")
    print("=" * 50)
    print()
    print("Choose a test:")
    print("1. Settings dialog (not required)")
    print("2. Settings dialog (required)")
    print("3. Settings dialog with existing key")
    print()
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        test_settings_dialog_not_required()
    elif choice == "2":
        test_settings_dialog_required()
    elif choice == "3":
        test_settings_dialog_with_existing_key()
    else:
        print("Invalid choice")
