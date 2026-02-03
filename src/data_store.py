"""
Contract Data Store Module

Provides in-memory storage and efficient access to contract analysis data.
"""

import logging
from typing import Dict, Any, List, Tuple, Optional


logger = logging.getLogger(__name__)


class ContractDataStore:
    """
    In-memory storage for contract analysis data with efficient field access.
    
    This class provides fast access to contract data using dot-notation field paths
    and keyword-based searching. It builds a schema map on initialization for
    optimized lookups.
    """
    
    def __init__(self):
        """Initialize empty data store."""
        self.data: Dict[str, Any] = {}
        self.schema_map: Dict[str, str] = {}
        logger.debug("ContractDataStore initialized")
    
    def load_data(self, contract_data: Dict[str, Any]) -> None:
        """
        Load contract data into store and build schema map.
        
        Args:
            contract_data: Parsed contract JSON data
        """
        logger.info("Loading contract data into store")
        self.data = contract_data
        self._build_schema_map()
        logger.info("Contract data loaded. Total fields in schema map: %d", len(self.schema_map))
    
    def _build_schema_map(self) -> None:
        """
        Build a flat map of all field paths for fast lookups.
        
        This creates a dictionary mapping field paths (e.g., 'parties.buyer.name')
        to their locations in the data structure.
        """
        self.schema_map = {}
        self._traverse_and_map(self.data, "")
        logger.debug("Schema map built with %d entries", len(self.schema_map))
    
    def _traverse_and_map(self, obj: Any, path: str) -> None:
        """
        Recursively traverse data structure and build field path mappings.
        
        Args:
            obj: Current object being traversed
            path: Current path in dot notation
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                self.schema_map[new_path.lower()] = new_path
                self._traverse_and_map(value, new_path)
        elif isinstance(obj, list):
            # For lists, map the path to the list itself
            if path:
                self.schema_map[path.lower()] = path
            # Also traverse list items
            for i, item in enumerate(obj):
                indexed_path = f"{path}[{i}]"
                self.schema_map[indexed_path.lower()] = indexed_path
                self._traverse_and_map(item, indexed_path)
        else:
            # Leaf node - map the path
            if path:
                self.schema_map[path.lower()] = path
    
    def get_field(self, field_path: str) -> Optional[Any]:
        """
        Retrieve data by field path (e.g., 'parties.buyer.name').
        
        Args:
            field_path: Dot-notation path to field
            
        Returns:
            Field value or None if not found
        """
        logger.debug("Getting field: %s", field_path)
        
        if not field_path:
            logger.warning("Empty field path provided")
            return None
        
        # Split path into components
        parts = field_path.split('.')
        current = self.data
        
        try:
            for part in parts:
                # Handle array indexing (e.g., risks[0])
                if '[' in part and ']' in part:
                    field_name = part[:part.index('[')]
                    index_str = part[part.index('[') + 1:part.index(']')]
                    
                    if field_name:
                        current = current[field_name]
                    
                    index = int(index_str)
                    current = current[index]
                else:
                    current = current[part]
            
            logger.debug("Field found: %s", field_path)
            return current
            
        except (KeyError, IndexError, ValueError, TypeError) as e:
            logger.debug("Field not found: %s (error: %s)", field_path, e)
            return None
    
    def search_fields(self, keywords: List[str]) -> List[Tuple[str, Any]]:
        """
        Search for fields matching keywords.
        
        This method searches both field names and field values for the given keywords.
        
        Args:
            keywords: List of search terms
            
        Returns:
            List of (field_path, value) tuples matching the search
        """
        logger.debug("Searching fields with keywords: %s", keywords)
        
        if not keywords:
            logger.warning("No keywords provided for search")
            return []
        
        # Normalize keywords to lowercase for case-insensitive search
        normalized_keywords = [kw.lower() for kw in keywords]
        results = []
        
        # Search through schema map
        for field_path_lower, field_path_original in self.schema_map.items():
            # Check if any keyword matches the field path
            path_matches = any(kw in field_path_lower for kw in normalized_keywords)
            
            if path_matches:
                value = self.get_field(field_path_original)
                if value is not None:
                    results.append((field_path_original, value))
                    continue
            
            # Check if any keyword matches the field value (for string values)
            value = self.get_field(field_path_original)
            if isinstance(value, str):
                value_lower = value.lower()
                if any(kw in value_lower for kw in normalized_keywords):
                    results.append((field_path_original, value))
        
        logger.debug("Search found %d matching fields", len(results))
        return results
    
    def get_all_data(self) -> Dict[str, Any]:
        """
        Get complete contract data dictionary.
        
        Returns:
            Complete contract data
        """
        logger.debug("Retrieving all contract data")
        return self.data
    
    def is_loaded(self) -> bool:
        """
        Check if data has been loaded into the store.
        
        Returns:
            True if data is loaded, False otherwise
        """
        return bool(self.data)
    
    def get_field_paths(self) -> List[str]:
        """
        Get all available field paths in the data store.
        
        Returns:
            List of field paths in dot notation
        """
        return list(self.schema_map.values())
    
    def clear(self) -> None:
        """Clear all data from the store."""
        logger.info("Clearing data store")
        self.data = {}
        self.schema_map = {}
