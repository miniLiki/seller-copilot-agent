import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("PYTHON_DOTENV_DISABLED", "true")
os.environ.setdefault("SELLER_COPILOT_STORAGE", "mock")
