import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Loads and tracks configuration file with hot reload support."""

    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config: Optional[Dict[str, Any]] = None
        self.last_mtime: Optional[float] = None

    def load(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Validate required fields
        required_fields = ['model', 'temperature', 'max_tokens']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required config field: {field}")

        self.config = config
        self.last_mtime = self.config_path.stat().st_mtime
        return config

    def check_and_reload(self) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if config file has been modified and reload if necessary.

        Returns:
            Tuple of (was_reloaded: bool, config: Optional[Dict])
        """
        if not self.config_path.exists():
            return False, self.config

        current_mtime = self.config_path.stat().st_mtime

        # First load or file has been modified
        if self.last_mtime is None or current_mtime > self.last_mtime:
            try:
                config = self.load()
                return True, config
            except Exception as e:
                logger.error(f"Error reloading config: {e}")
                return False, self.config

        return False, self.config

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        if self.config is None:
            self.load()
        return self.config
