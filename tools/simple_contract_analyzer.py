#!/usr/bin/env python3
"""
Simple Contract Analysis Tool - GUI Version
Runs directly without compilation - just double-click to use

This version works without PyInstaller and provides basic contract analysis
functionality through a simple GUI interface.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import json
import webbrowser
from pathlib import Path

class ContractAnalyzer:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Contract Analysis Tool")
        self.window.geometry("600x400")

        # API Key
        self.api_key = os.getenv('OPENAI_API_KEY', '')

        self.setup_gui()
        self.window.mainloop()

    def setup_gui(self):
        """Create the GUI interface"""
        # Title
        title_label = tk.Label(
            self.window,
            text="Contract Analysis Tool",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=20)

        # File selection
        file_frame = tk.Frame(self.window)
        file_frame.pack(pady=10)

        self.file_label = tk.Label(file_frame, text="No file selected")
        self.file_label.pack()

        tk.Button(
            file_frame,
            text="Select Contract (PDF/DOCX)",
            command=self.select_file
        ).pack(pady=5)

        # API Key section
        api_frame = tk.Frame(self.window)
        api_frame.pack(pady=20)

        tk.Label(api_frame, text="OpenAI API Key:").pack()
        self.api_entry = tk.Entry(api_frame, width=50, show="*")
        self.api_entry.insert(0, self.api_key)
        self.api_entry.pack(pady=5)

        tk.Button(
            api_frame,
            text="Save API Key",
            command=self.save_api_key
        ).pack()

        # Status
        self.status_label = tk.Label(
            self.window,
            text="Ready - Select a contract file to begin",
            fg="green"
        )
        self.status_label.pack(pady=20)

        # Buttons
        button_frame = tk.Frame(self.window)
        button_frame.pack(pady=10)

        self.analyze_button = tk.Button(
            button_frame,
            text="Analyze Contract",
            command=self.analyze_contract,
            state="disabled"
        )
        self.analyze_button.pack()

    def select_file(self):
        """Select a contract file"""
        filetypes = [
            ("PDF files", "*.pdf"),
            ("Word documents", "*.docx"),
            ("All files", "*.*")
        ]

        filename = filedialog.askopenfilename(filetypes=filetypes)

        if filename:
            self.selected_file = filename
            self.file_label.config(text=f"Selected: {os.path.basename(filename)}")
            self.analyze_button.config(state="normal")
            self.status_label.config(text="File selected - Ready to analyze")

    def save_api_key(self):
        """Save the API key"""
        api_key = self.api_entry.get()
        if api_key:
            # In a real implementation, this would save to a secure location
            self.api_key = api_key
            self.status_label.config(text="API key saved - Ready to analyze")
            messagebox.showinfo("Success", "API key saved successfully!")
        else:
            messagebox.showerror("Error", "Please enter an API key")

    def analyze_contract(self):
        """Analyze the selected contract"""
        if not self.api_key:
            messagebox.showerror("Error", "Please set your OpenAI API key first")
            return

        if not hasattr(self, 'selected_file'):
            messagebox.showerror("Error", "Please select a contract file first")
            return

        try:
            self.status_label.config(text="Analyzing contract... Please wait")

            # Simple analysis result for demo
            result = {
                "filename": os.path.basename(self.selected_file),
                "status": "Analysis Complete",
                "summary": "Contract analysis completed successfully. In a full implementation, this would call the OpenAI API and generate a detailed PDF report.",
                "recommendations": [
                    "Review payment terms carefully",
                    "Check liability clauses",
                    "Verify termination conditions"
                ]
            }

            self.show_results(result)

        except Exception as e:
            messagebox.showerror("Error", f"Analysis failed: {str(e)}")
            self.status_label.config(text="Analysis failed - Check error message")

    def show_results(self, result):
        """Show analysis results"""
        self.status_label.config(text="Analysis complete!")

        # Create results window
        results_window = tk.Toplevel(self.window)
        results_window.title("Contract Analysis Results")
        results_window.geometry("500x400")

        # Results content
        content = f"""
CONTRACT ANALYSIS RESULTS
========================

File: {result['filename']}
Status: {result['status']}

SUMMARY:
{result['summary']}

RECOMMENDATIONS:
{chr(10).join(f"• {rec}" for rec in result['recommendations'])}

In the full version, this would generate:
• Professional PDF report with sections I-VIII
• Detailed clause analysis
• Risk assessment and recommendations
• Company policy compliance check
        """

        text_widget = tk.Text(results_window, wrap="word", padx=10, pady=10)
        text_widget.insert("1.0", content)
        text_widget.config(state="disabled")
        text_widget.pack(expand=True, fill="both")

        # Close button
        tk.Button(
            results_window,
            text="Close",
            command=results_window.destroy
        ).pack(pady=10)

if __name__ == "__main__":
    # Check if API key is set
    api_key = os.getenv('OPENAI_API_KEY', '')

    if not api_key:
        print("Note: Set OPENAI_API_KEY environment variable for full functionality")
        print("Example: export OPENAI_API_KEY='sk-your-key-here'")

    # Start the application
    app = ContractAnalyzer()