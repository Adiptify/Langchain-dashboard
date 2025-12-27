import logging
import os
from datetime import datetime

def setup_logging(log_file='log.txt'):
    """
    Sets up logging to a specified file.
    """
    if os.path.exists(log_file):
        try:
            # Attempt to close existing handlers to release the file
            for handler in logging.root.handlers[:]:
                if isinstance(handler, logging.FileHandler) and handler.baseFilename == os.path.abspath(log_file):
                    handler.close()
                    logging.root.removeHandler(handler)
            os.remove(log_file) # Try removing again after closing handlers
        except PermissionError:
            # If still locked, rename the old log file and start fresh
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            old_log_name = f"log_old_{timestamp}.txt"
            try:
                os.rename(log_file, old_log_name)
                print(f"Warning: Could not delete log.txt, renamed to {old_log_name} to continue.")
            except Exception as e:
                print(f"Error renaming old log file: {e}. Proceeding without clearing log.")
        except Exception as e:
            print(f"Error clearing log.txt: {e}. Proceeding without clearing log.")

    # Ensure basicConfig is only called once or is reset properly
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    import sys
    # Force UTF-8 for console output on Windows
    if sys.platform == "win32":
        try:
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8', errors='replace')
        except Exception:
            pass

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

def log_process_completion(process_name, status="completed", details=None):
    """
    Logs the completion or status of a process.
    """
    if details:
        logger.info(f"Process: {process_name} - Status: {status} - Details: {details}")
    else:
        logger.info(f"Process: {process_name} - Status: {status}")
