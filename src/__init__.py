"""CR2A - Contract Review & Analysis Application"""

__version__ = "1.0.0"

# Import core components for easier access
from src.config_manager import ConfigManager
from src.openai_fallback_client import OpenAIClient
from src.analysis_engine import AnalysisEngine
from src.query_engine import QueryEngine

__all__ = [
    "ConfigManager",
    "OpenAIClient",
    "AnalysisEngine",
    "QueryEngine",
]
