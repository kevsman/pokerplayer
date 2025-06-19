import json
import os
import logging

OPPONENT_ANALYSIS_FILE = 'opponent_analysis_data.json'
logger = logging.getLogger(__name__)

def save_opponent_analysis(opponent_data, file_path=OPPONENT_ANALYSIS_FILE):
    """Save opponent analysis data to a file (JSON)."""
    try:
        logger.info(f"Saving opponent analysis to {file_path}. Data keys: {list(opponent_data.keys())}")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(opponent_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving opponent analysis: {e}")

def load_opponent_analysis(file_path=OPPONENT_ANALYSIS_FILE):
    """Load opponent analysis data from a file (JSON)."""
    if not os.path.exists(file_path):
        logger.info(f"Opponent analysis file {file_path} does not exist. Returning empty dict.")
        return {}
    try:
        logger.info(f"Loading opponent analysis from {file_path}.")
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading opponent analysis: {e}")
        return {}
