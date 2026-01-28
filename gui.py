import PySimpleGUI as sg
import os

# Constants for UI configuration
WINDOW_TITLE = "Contract Analysis Tool"
WINDOW_SIZE = (600, 400)
DROP_ZONE_SIZE = (500, 100)
SUPPORTED_FORMATS = ('.pdf', '.docx')
BUTTON_COLOR = ('white', '#007acc')
DISABLED_BUTTON_COLOR = ('gray', 'lightgray')

def create_window() -> sg.Window:
    """
    Create the main application window with drag-and-drop interface.

    Returns:
        sg.Window: The configured PySimpleGUI window
    """
    # Define the window layout
    layout = [
        # Title section
        [sg.Text("Contract Analysis Tool", font=('Helvetica', 16, 'bold'), justification='center', pad=(0, 20))],

        # Drop zone section - central area for file dropping
        [sg.Text("Drop Zone:", font=('Helvetica', 12))],
        [sg.Multiline(
            "Drop .pdf or .docx file here",
            size=DROP_ZONE_SIZE,
            key='-DROP_ZONE-',
            enable_events=True,
            pad=(20, 10),
            background_color='#f0f0f0',
            text_color='gray',
            font=('Helvetica', 10),
            no_scrollbar=True,
            border_width=2,
            drop=True  # Enable drag and drop
        )],

        # Button section
        [sg.Button(
            "Start Analysis",
            key='-START-',
            disabled=True,
            button_color=BUTTON_COLOR,
            size=(15, 2),
            font=('Helvetica', 10),
            pad=(10, 20)
        )],

        [sg.Button(
            "Save PDF",
            key='-SAVE-',
            disabled=True,
            button_color=DISABLED_BUTTON_COLOR,
            size=(15, 2),
            font=('Helvetica', 10),
            pad=(10, 10)
        )],

        # Status section at bottom
        [sg.Text(
            "Status: idle",
            key='-STATUS-',
            font=('Helvetica', 10),
            text_color='gray',
            pad=(10, 20),
            justification='center',
            expand_x=True
        )]
    ]

    # Create and return the window
    window = sg.Window(
        WINDOW_TITLE,
        layout,
        size=WINDOW_SIZE,
        element_justification='center',
        finalize=True,
        resizable=True,
        margins=(20, 20)
    )

    return window

def show_error_dialog(message: str) -> None:
    """
    Display an error dialog with the specified message.

    Args:
        message (str): Error message to display
    """
    sg.popup(
        message,
        title="Error",
        button_color=BUTTON_COLOR,
        icon=sg.SYSTEM_TRAY_MESSAGE_ICON_ERROR
    )

def update_status(window: sg.Window, status: str) -> None:
    """
    Update the status line text in the window.

    Args:
        window (sg.Window): The window to update
        status (str): Status message to display
    """
    window['-STATUS-'].update(f"Status: {status}")

def enable_start_button(window: sg.Window) -> None:
    """
    Enable the Start Analysis button.

    Args:
        window (sg.Window): The window containing the button
    """
    window['-START-'].update(disabled=False, button_color=BUTTON_COLOR)

def enable_save_button(window: sg.Window) -> None:
    """
    Enable the Save PDF button.

    Args:
        window (sg.Window): The window containing the button
    """
    window['-SAVE-'].update(disabled=False, button_color=BUTTON_COLOR)

def disable_buttons(window: sg.Window) -> None:
    """
    Disable both Start Analysis and Save PDF buttons.

    Args:
        window (sg.Window): The window containing the buttons
    """
    window['-START-'].update(disabled=True, button_color=DISABLED_BUTTON_COLOR)
    window['-SAVE-'].update(disabled=True, button_color=DISABLED_BUTTON_COLOR)

def is_valid_file_format(filename: str) -> bool:
    """
    Check if the file has a supported format.

    Args:
        filename (str): Path to the file to check

    Returns:
        bool: True if file format is supported, False otherwise
    """
    if not filename:
        return False

    _, ext = os.path.splitext(filename.lower())
    return ext in SUPPORTED_FORMATS

def handle_file_drop(window: sg.Window, file_path: str) -> None:
    """
    Handle when a file is dropped onto the drop zone.

    Args:
        window (sg.Window): The window to update
        file_path (str): Path to the dropped file
    """
    if not file_path:
        return

    # Validate file format
    if not is_valid_file_format(file_path):
        show_error_dialog(
            f"Unsupported file format. Please drop a .pdf or .docx file.\n\n"
            f"File: {os.path.basename(file_path)}"
        )
        return

    # Check if file exists and is readable
    if not os.path.exists(file_path):
        show_error_dialog(f"File not found: {file_path}")
        return

    # Update drop zone with file name and enable start button
    filename = os.path.basename(file_path)
    window['-DROP_ZONE-'].update(f"Selected: {filename}")
    enable_start_button(window)

    # Store the file path for later use
    window.metadata = {'file_path': file_path}

def run_gui() -> str:
    """
    Main function to run the GUI application.

    Returns:
        str: Path to the selected file when analysis is complete, or empty string if cancelled
    """
    window = create_window()
    selected_file = ""

    try:
        while True:
            event, values = window.read()

            if event == sg.WINDOW_CLOSED:
                break

            elif event == '-DROP_ZONE-':
                # Handle file drop event
                dropped_files = values['-DROP_ZONE-'].split('\n') if values['-DROP_ZONE-'] else []

                if dropped_files and dropped_files[0].strip():
                    # Extract file path from the dropped content
                    file_path = dropped_files[0].strip()
                    handle_file_drop(window, file_path)
                    # Clear the drop zone after handling
                    window['-DROP_ZONE-'].update("Drop .pdf or .docx file here")

            elif event == '-START-':
                # Start analysis button clicked
                if hasattr(window, 'metadata') and window.metadata.get('file_path'):
                    selected_file = window.metadata['file_path']
                    update_status(window, "analyzing")
                    break

            elif event == '-SAVE-':
                # Save PDF button clicked - this would be handled by the main application
                update_status(window, "generating PDF")

    finally:
        window.close()

    return selected_file

if __name__ == "__main__":
    # For testing the GUI standalone
    run_gui()