import sys
from pathlib import Path


JOBS_DIR = Path(__file__).resolve().parent.parent

if str(JOBS_DIR) not in sys.path:
    sys.path.insert(0, str(JOBS_DIR))