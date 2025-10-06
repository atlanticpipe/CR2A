import sys                              # stdlib: process + exit codes
import traceback                        # stdlib: pretty traceback printer

def handle_exception(exc_type, exc_value, exc_traceback) -> None:
    # Global exception hook: print a clean error report and exit non-zero.
    # Let Ctrl+C behave normally (no noisy stack trace for KeyboardInterrupt).
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)  # delegate default handling
        return

    # Human-friendly header.
    print("\n" + "-" * 80)              # visual separator
    print("An error occurred:")         # title
    print("-" * 80)                     # separator

    # Core exception details.
    print(f"Type:  {exc_type.__name__}")  # exception class name
    print(f"Value: {exc_value}")          # exception message text

    # Full traceback for diagnostics (to stderr).
    traceback.print_exception(exc_type, exc_value, exc_traceback)

    # Extract concise traceback info for quick debugging
    tb = traceback.extract_tb(exc_traceback)             # get traceback list
    if tb:
        last = tb[-1]                                    # last frame = error origin
        print(f"Location: File '{last.filename}', line {last.lineno}, in {last.name}")
    else:
        print("Location: No traceback available")        # edge case: no traceback object
    
    # Print full traceback for detailed debugging
    print("\nFull Traceback:")
    traceback.print_exception(exc_type, exc_value, exc_traceback)  # prints formatted trace
    print("*" * 80 + "\n")                              # visual separator

    # Restore the default system exception hook (optional defensive cleanup)
    sys.excepthook = sys.__excepthook__

    # Exit non-zero so batch tools / CI know this failed
    sys.exit(1)

import asyncio  # needed for registering the asyncio exception handler

# Install our global exception hook so *all* uncaught errors use handle_exception.
sys.excepthook = handle_exception
# If you ever need to revert to Python's default behavior, use:
# sys.excepthook = sys.__excepthook__

# Asyncio exception handler → funnels to our synchronous handler above.
def _asyncio_handler(loop, context) -> None:
    # Bridge asyncio errors to handle_exception for consistent reporting.
    exc = context.get("exception")                 # actual Exception if present
    if exc is not None:
        handle_exception(type(exc), exc, exc.__traceback__)  # reuse our hook
        return
    # Fallback when only a message is provided by asyncio
    print("[asyncio error]", context.get("message", "unknown error"))

# Try to register the handler on the *current running* event loop.
try:
    loop = asyncio.get_running_loop()              # safer than get_event_loop()
    loop.set_exception_handler(_asyncio_handler)   # register bridge handler
except RuntimeError:
    # No running loop yet (e.g., during module import). The main program can
    # call this again *after* creating the loop, so we silently skip here.
    pass
