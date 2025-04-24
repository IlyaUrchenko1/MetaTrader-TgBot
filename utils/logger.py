import logging
import sys
import utils.constants as const # Import constants to get LOG_FILE

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # Set the lowest level to capture all messages

# Create formatter
log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s")

# --- Console Handler ---
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO) # Show INFO level and above in console
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

# --- File Handler ---
try:
    file_handler = logging.FileHandler(const.LOG_FILE, mode='a') # Append mode
    file_handler.setLevel(logging.DEBUG) # Log DEBUG level and above to file
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)
    logger.info(f"Logging initialized. Console level: INFO, File level ({const.LOG_FILE}): DEBUG")
except Exception as e:
    logger.error(f"Failed to initialize file logging to {const.LOG_FILE}: {e}")

# Example usage (will log to console and file if file handler is set up)
# logger.debug("This is a debug message.")
# logger.info("This is an info message.")
# logger.warning("This is a warning message.")
# logger.error("This is an error message.")
# logger.critical("This is a critical message.") 