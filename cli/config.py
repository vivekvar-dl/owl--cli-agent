import os
import toml
import logging
from dataclasses import dataclass, field
from typing import Optional, Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class Config:
    """Configuration handler for the CLI tool."""

    api_key: Optional[str] = field(default_factory=lambda: os.environ.get("GEMINI_API_KEY"))
    google_api_key: Optional[str] = field(default_factory=lambda: os.environ.get("GOOGLE_API_KEY"))
    search_engine_id: Optional[str] = field(default_factory=lambda: os.environ.get("PROGRAMMABLE_SEARCH_ENGINE_ID"))
    model: str = "gemini-2.5-flash"
    interactive_mode: bool = False
    auto_execute: bool = False
    verbose: bool = False
    custom_prompt: Optional[str] = None
    config_dir: str = field(default_factory=lambda: os.path.expanduser("~/.config/gemini-cli"))
    config_file: str = field(default_factory=lambda: os.path.join(os.path.expanduser("~/.config/gemini-cli"), "config.toml"))
    _file_config: dict = field(init=False, repr=False)

    # Application Configuration
    log_dir: str = field(init=False)
    history_file: str = field(init=False)
    max_history: int = field(init=False)

    def __post_init__(self):
        """Post-initialization to set up dependent fields."""
        self._file_config = self._load_config_from_file()
        self.model = self._get_config("GEMINI_MODEL", self.model)
        self.log_dir = self._get_config("CLI_LOG_DIR", os.path.join(self.config_dir, "logs"))
        self.history_file = self._get_config("CLI_HISTORY_FILE", os.path.join(self.config_dir, "history.json"))
        self.max_history = int(self._get_config("CLI_MAX_HISTORY", 100))

    def _load_config_from_file(self) -> dict:
        """Loads configuration from the TOML file."""
        if not os.path.exists(self.config_file):
            self._create_default_config()
        try:
            with open(self.config_file, 'r') as f:
                return toml.load(f)
        except (toml.TomlDecodeError, IOError) as e:
            print(f"Warning: Could not read config file at {self.config_file}. Error: {e}")
            return {}

    def _create_default_config(self):
        """Creates a default configuration file."""
        os.makedirs(self.config_dir, exist_ok=True)
        default_config = {
            "api": {
                "GEMINI_API_KEY": "YOUR_API_KEY_HERE",
                "GEMINI_MODEL": "gemini-2.5-flash"
            },
            "application": {
                "CLI_LOG_DIR": os.path.join(self.config_dir, "logs"),
                "CLI_HISTORY_FILE": os.path.join(self.config_dir, "history.json"),
                "CLI_MAX_HISTORY": 100
            },
            "behavior": {
                "CLI_AUTO_EXECUTE": False,
                "CLI_VERBOSE": False,
                "CLI_INTERACTIVE_MODE": False
            },
            "customization": {
                "CLI_CUSTOM_PROMPT": ""
            }
        }
        try:
            with open(self.config_file, 'w') as f:
                toml.dump(default_config, f)
            print(f"Created default config file at: {self.config_file}")
        except IOError as e:
            print(f"Error creating default config file: {e}")

    def _get_config(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Get a configuration value, prioritizing environment variables,
        then the config file, and finally a default value.
        """
        # 1. Check environment variable
        value = os.environ.get(key)
        if value is not None:
            return value

        # 2. Check config file
        for section in self._file_config.values():
            if key in section:
                return section[key]

        # 3. Return default
        return default

    def validate(self) -> bool:
        """Validate the configuration."""
        if not self.api_key:
            logger.error("GEMINI_API_KEY environment variable not set.")
            print("ERROR: GEMINI_API_KEY environment variable not set. Please get your API key from https://aistudio.google.com/app/apikey")
            return False
        
        # We don't need to validate the search keys unless web search is used,
        # but it's good practice to check if we plan to use them.
        # For now, we will let the tool fail if they are not set.

        return True

    def __str__(self) -> str:
        """Return string representation of the configuration."""
        config_dict = self.__dict__.copy()
        if self.api_key:
            config_dict['api_key'] = f"{self.api_key[:4]}...{self.api_key[-4:]}" if len(self.api_key) > 8 else "****"
        del config_dict['_file_config'] # Don't print the raw file contents
        return str(config_dict)


# Singleton instance holder
_config_instance: Optional[Config] = None

def get_config() -> Config:
    """Returns the singleton Config instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance 