import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

os.environ.setdefault("CDSS_DATABASE_URL", "sqlite:///./test_clinical_cdss.db")
os.environ.setdefault("CDSS_SQL_ECHO", "false")
os.environ.setdefault("CDSS_DEMO_DATA", "false")
