import os
import unittest
from unittest.mock import patch

from cli.config import Config


class TestConfig(unittest.TestCase):
    """Test cases for the Config class."""
    
    def test_default_values(self):
        """Test that default values are set correctly."""
        # Mock environment variables
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}, clear=True):
            config = Config()
            
            # Check API configuration
            self.assertEqual(config.api_key, "test_key")
            self.assertEqual(config.api_url, "https://generativelanguage.googleapis.com/v1beta")
            self.assertEqual(config.model, "gemini-1.5-pro")
            
            # Check application configuration
            self.assertTrue(config.log_dir.endswith("/.cli/logs"))
            self.assertTrue(config.history_file.endswith("/.cli/history.json"))
            self.assertEqual(config.max_history, 100)
            
            # Check behavior configuration
            self.assertFalse(config.auto_execute)
            self.assertFalse(config.verbose)
    
    def test_custom_values(self):
        """Test that custom values from environment variables are set correctly."""
        # Mock environment variables with custom values
        env_vars = {
            "GEMINI_API_KEY": "custom_key",
            "GEMINI_API_URL": "https://custom-api.example.com",
            "GEMINI_MODEL": "custom-model",
            "CLI_LOG_DIR": "/custom/log/dir",
            "CLI_HISTORY_FILE": "/custom/history.json",
            "CLI_MAX_HISTORY": "50",
            "CLI_AUTO_EXECUTE": "true",
            "CLI_VERBOSE": "true"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            
            # Check API configuration
            self.assertEqual(config.api_key, "custom_key")
            self.assertEqual(config.api_url, "https://custom-api.example.com")
            self.assertEqual(config.model, "custom-model")
            
            # Check application configuration
            self.assertEqual(config.log_dir, "/custom/log/dir")
            self.assertEqual(config.history_file, "/custom/history.json")
            self.assertEqual(config.max_history, 50)
            
            # Check behavior configuration
            self.assertTrue(config.auto_execute)
            self.assertTrue(config.verbose)
    
    def test_missing_api_key(self):
        """Test that an error is raised when the API key is missing."""
        # Mock environment variables without API key
        with patch.dict(os.environ, {}, clear=True):
            # Check that the API key is required
            with self.assertRaises(ValueError):
                Config()
    
    def test_validate(self):
        """Test the validate method."""
        # Mock environment variables
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}, clear=True):
            config = Config()
            
            # Check that validation passes
            self.assertTrue(config.validate())
            
            # Check that validation fails when API key is empty
            config.api_key = ""
            self.assertFalse(config.validate())


if __name__ == "__main__":
    unittest.main() 