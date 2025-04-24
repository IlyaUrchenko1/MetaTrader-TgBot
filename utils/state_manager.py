import json
import os
from utils.logger import logger

STATE_FILE = "state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                logger.info(f"Loaded state from {STATE_FILE}")
                return state
        except Exception as e:
            logger.error(f"Error loading state from {STATE_FILE}: {e}")
            return {}
    return {}

def save_state(state_data):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state_data, f, indent=4)
        # logger.info(f"Saved state to {STATE_FILE}") # Optional: logging every save might be too verbose
    except Exception as e:
        logger.error(f"Error saving state to {STATE_FILE}: {e}") 