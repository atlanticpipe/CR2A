"""CR2A - Contract Review & Analysis Application"""

__version__ = "1.0.0"

# Import core components for easier access
from config_manager import ConfigManager
from analysis_engine import AnalysisEngine
from query_engine import QueryEngine

__all__ = [
    "ConfigManager",
    "AnalysisEngine",
    "QueryEngine",
]
