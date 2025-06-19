import json
import os

OPPONENT_ANALYSIS_FILE = 'opponent_analysis_data.json'

def save_opponent_analysis(opponent_data, file_path=OPPONENT_ANALYSIS_FILE):
    """Save opponent analysis data to a file (JSON)."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(opponent_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving opponent analysis: {e}")

def load_opponent_analysis(file_path=OPPONENT_ANALYSIS_FILE):
    """Load opponent analysis data from a file (JSON)."""
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading opponent analysis: {e}")
        return {}
