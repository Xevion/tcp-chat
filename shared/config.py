"""Resolve runtime configuration from a TOML file with CLI overrides.

Precedence, highest first: an explicit CLI value, the config file's value, the
constants default. Missing files are treated as empty configuration.
"""

from typing import Optional

import tomli

DEFAULT_CONFIG_PATH = 'tcp-chat.toml'


class Config:
    def __init__(self, data: Optional[dict] = None):
        self.data = data or {}

    @classmethod
    def load(cls, path: str = DEFAULT_CONFIG_PATH) -> 'Config':
        try:
            with open(path, 'rb') as handle:
                return cls(tomli.load(handle))
        except FileNotFoundError:
            return cls({})

    def get(self, section: str, key: str, cli=None, default=None):
        """First of: the CLI value, the file's [section] key, a top-level key, the default."""
        if cli is not None:
            return cli
        section_data = self.data.get(section, {})
        if key in section_data:
            return section_data[key]
        if key in self.data:
            return self.data[key]
        return default
