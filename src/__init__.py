"""Contract Chat UI - A desktop application for querying contract analysis results."""

__version__ = "1.0.0"

# Import core components for easier access
from src.json_loader import ContractJSONLoader, ValidationError
from src.data_store import ContractDataStore
from src.config_manager import ConfigManager
from src.openai_fallback_client import OpenAIClient
from src.contract_chat_ui import ContractChatUI

__all__ = [
    "ContractJSONLoader",
    "ContractDataStore",
    "ConfigManager",
    "OpenAIClient",
    "ContractChatUI",
    "ValidationError",
]
