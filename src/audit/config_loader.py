"""Configuration loading for custom patterns and file types."""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
import yaml


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""
    pass


class ConfigLoader:
    """Loads and validates custom configuration for the audit system.
    
    Supports JSON and YAML configuration files with custom patterns,
    file extensions, and exclusion rules.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration loader.
        
        Args:
            config_path: Path to configuration file (JSON or YAML)
        """
        self.config_path = Path(config_path) if config_path else None
        self.config = self._load_config() if config_path else {}
    
    def _load_config(self) -> Dict:
        """Load configuration from file.
        
        Returns:
            Dictionary containing configuration
            
        Raises:
            ConfigurationError: If file cannot be read or parsed
        """
        if not self.config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Determine file type and parse
            if self.config_path.suffix in ['.yaml', '.yml']:
                config = yaml.safe_load(content)
            elif self.config_path.suffix == '.json':
                config = json.loads(content)
            else:
                raise ConfigurationError(
                    f"Unsupported configuration file type: {self.config_path.suffix}. "
                    "Use .json, .yaml, or .yml"
                )
            
            return config if config else {}
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in configuration file: {e}")
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error reading configuration file: {e}")
    
    def get_custom_patterns(self) -> Optional[Dict[str, List[str]]]:
        """Get custom detection patterns from configuration.
        
        Returns:
            Dictionary mapping pattern categories to regex pattern strings,
            or None if no custom patterns defined
            
        Raises:
            ConfigurationError: If patterns are invalid
        """
        if 'patterns' not in self.config:
            return None
        
        patterns = self.config['patterns']
        
        if not isinstance(patterns, dict):
            raise ConfigurationError("'patterns' must be a dictionary")
        
        # Validate each pattern category
        validated_patterns = {}
        for category, pattern_list in patterns.items():
            if not isinstance(pattern_list, list):
                raise ConfigurationError(
                    f"Pattern category '{category}' must contain a list of patterns"
                )
            
            # Validate each pattern is a valid regex
            validated_list = []
            for pattern in pattern_list:
                if not isinstance(pattern, str):
                    raise ConfigurationError(
                        f"Pattern in category '{category}' must be a string: {pattern}"
                    )
                
                # Try to compile the regex to validate syntax
                try:
                    re.compile(pattern)
                    validated_list.append(pattern)
                except re.error as e:
                    raise ConfigurationError(
                        f"Invalid regex pattern in category '{category}': {pattern}\n"
                        f"Error: {e}"
                    )
            
            if validated_list:
                validated_patterns[category] = validated_list
        
        return validated_patterns if validated_patterns else None
    
    def get_custom_extensions(self) -> Optional[Set[str]]:
        """Get custom file extensions from configuration.
        
        Returns:
            Set of file extensions (including leading dot), or None if not defined
            
        Raises:
            ConfigurationError: If extensions are invalid
        """
        if 'extensions' not in self.config:
            return None
        
        extensions = self.config['extensions']
        
        if not isinstance(extensions, list):
            raise ConfigurationError("'extensions' must be a list")
        
        # Validate and normalize extensions
        validated_extensions = set()
        for ext in extensions:
            if not isinstance(ext, str):
                raise ConfigurationError(f"Extension must be a string: {ext}")
            
            # Ensure extension starts with a dot
            if not ext.startswith('.'):
                ext = '.' + ext
            
            validated_extensions.add(ext)
        
        return validated_extensions if validated_extensions else None
    
    def get_custom_exclusions(self) -> Optional[List[str]]:
        """Get custom exclusion patterns from configuration.
        
        Returns:
            List of exclusion patterns, or None if not defined
            
        Raises:
            ConfigurationError: If exclusions are invalid
        """
        if 'exclusions' not in self.config:
            return None
        
        exclusions = self.config['exclusions']
        
        if not isinstance(exclusions, list):
            raise ConfigurationError("'exclusions' must be a list")
        
        # Validate each exclusion is a string
        for exclusion in exclusions:
            if not isinstance(exclusion, str):
                raise ConfigurationError(f"Exclusion pattern must be a string: {exclusion}")
        
        return exclusions if exclusions else None
