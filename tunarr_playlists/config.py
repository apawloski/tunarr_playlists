"""Configuration loader for channel definitions."""

import logging
import os
from typing import List, Dict, Any, Optional
import yaml

logger = logging.getLogger(__name__)


class ChannelConfig:
    """Represents a single channel configuration."""

    def __init__(self, data: Dict[str, Any]):
        """Initialize channel config from dictionary.

        Args:
            data: Channel configuration dictionary
        """
        self.name = data.get('name')
        self.number = data.get('number')
        self.source = data.get('source', {})
        self.replace_existing = data.get('replace_existing', True)

        # Validate required fields
        if not self.name:
            raise ValueError("Channel 'name' is required")
        if not self.number:
            raise ValueError("Channel 'number' is required")
        if not self.source:
            raise ValueError("Channel 'source' is required")

        # Validate source type
        source_type = self.source.get('type')
        if source_type not in ['plex_playlist', 'letterboxd']:
            raise ValueError(f"Invalid source type: {source_type}. Must be 'plex_playlist' or 'letterboxd'")

        # Validate source-specific fields
        if source_type == 'plex_playlist':
            if not self.source.get('playlist_name'):
                raise ValueError("'playlist_name' is required for plex_playlist source type")
        elif source_type == 'letterboxd':
            if not self.source.get('url'):
                raise ValueError("'url' is required for letterboxd source type")

    @property
    def source_type(self) -> str:
        """Get the source type."""
        return self.source.get('type')

    @property
    def is_plex_playlist(self) -> bool:
        """Check if this is a Plex playlist source."""
        return self.source_type == 'plex_playlist'

    @property
    def is_letterboxd(self) -> bool:
        """Check if this is a Letterboxd source."""
        return self.source_type == 'letterboxd'

    @property
    def playlist_name(self) -> Optional[str]:
        """Get Plex playlist name (if applicable)."""
        return self.source.get('playlist_name')

    @property
    def letterboxd_url(self) -> Optional[str]:
        """Get Letterboxd URL (if applicable)."""
        return self.source.get('url')

    def __repr__(self) -> str:
        """String representation."""
        return f"ChannelConfig(name={self.name}, number={self.number}, source_type={self.source_type})"


class ConfigLoader:
    """Loads and parses channel configuration from YAML file."""

    def __init__(self, config_path: str):
        """Initialize config loader.

        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = config_path

    def load_channels(self) -> List[ChannelConfig]:
        """Load all channel configurations from file.

        Returns:
            List of ChannelConfig objects

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        try:
            with open(self.config_path, 'r') as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")

        if not data:
            raise ValueError("Configuration file is empty")

        channels_data = data.get('channels', [])
        if not channels_data:
            raise ValueError("No channels defined in configuration file")

        channels = []
        for i, channel_data in enumerate(channels_data):
            try:
                channel = ChannelConfig(channel_data)
                channels.append(channel)
                logger.debug(f"Loaded channel config: {channel}")
            except ValueError as e:
                logger.error(f"Invalid channel configuration at index {i}: {e}")
                raise

        logger.info(f"Loaded {len(channels)} channel configurations from {self.config_path}")
        return channels
