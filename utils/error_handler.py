import sys
import traceback

def handle_ecxeption(exc_type, exc_value, exc_traceback):
    """Handles errors by printing the traceback and exiting."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    print("\n" + "="*80)
    print("An error occurred:")
    print("+"*80)
    print(f"Type: {exc_type.__name__}")
    print(f"Value: {exc_value}")

    tb = traceback.extract_tb(exc_traceback)
    if tb:
        last = tb[-1]
        print(f"Location: File '{last.filename}', line {last.lineno}, in {last.name}")
    else:
        print("Location: No traceback available")

    print("\nFull Traceback:")
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    print("="*80 + "\n")
    sys.excepthook = sys.__excepthook__
    sys.exit(1)
sys.excepthook = handle_ecxeption
# sys.excepthook = sys.__excepthook__
# Uncomment the above line to disable custom error handling and use default behavior.
# Install an asyncio exception handler that funnels to our handler
def _asyncio_handler(loop, context):                     # define callback
    exc = context.get("exception")                       # grab Exception if present
    if exc is not None:
        handle_exception(type(exc), exc, exc.__traceback__)  # use our hook
    else:
        # Fallback when only a message exists — still print something useful
        print("[asyncio error]", context.get("message", "unknown error"))

try:
    asyncio.get_event_loop().set_exception_handler(_asyncio_handler)  # register
except RuntimeError:
    # No loop yet (possible during import); main() will create it, safe to ignore
    pass