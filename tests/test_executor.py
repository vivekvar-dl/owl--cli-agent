import unittest
from unittest.mock import patch, MagicMock

from cli.executor import CommandExecutor


class TestCommandExecutor(unittest.TestCase):
    """Test cases for the CommandExecutor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.executor = CommandExecutor()
    
    @patch('cli.executor.subprocess.Popen')
    def test_execute_command_success(self, mock_popen):
        """Test successful command execution."""
        # Mock successful command execution
        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = ("command output", "")
        mock_popen.return_value = process_mock
        
        # Execute command
        success, stdout, stderr = self.executor.execute_command("echo 'hello'")
        
        # Check results
        self.assertTrue(success)
        self.assertEqual(stdout, "command output")
        self.assertEqual(stderr, "")
        
        # Check that Popen was called with correct arguments
        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        self.assertEqual(args[0], ["echo", "hello"])
    
    @patch('cli.executor.subprocess.Popen')
    def test_execute_command_failure(self, mock_popen):
        """Test failed command execution."""
        # Mock failed command execution
        process_mock = MagicMock()
        process_mock.returncode = 1
        process_mock.communicate.return_value = ("", "command error")
        mock_popen.return_value = process_mock
        
        # Execute command
        success, stdout, stderr = self.executor.execute_command("invalid_command")
        
        # Check results
        self.assertFalse(success)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "command error")
    
    @patch('cli.executor.CommandExecutor.execute_command')
    def test_execute_commands_all_success(self, mock_execute_command):
        """Test executing multiple commands with all succeeding."""
        # Mock successful command executions
        mock_execute_command.side_effect = [
            (True, "output1", ""),
            (True, "output2", "")
        ]
        
        # Execute commands
        results = self.executor.execute_commands(["command1", "command2"])
        
        # Check results
        self.assertEqual(len(results), 2)
        self.assertTrue(results[0]["success"])
        self.assertTrue(results[1]["success"])
        self.assertEqual(results[0]["stdout"], "output1")
        self.assertEqual(results[1]["stdout"], "output2")
        
        # Check that execute_command was called twice
        self.assertEqual(mock_execute_command.call_count, 2)
    
    @patch('cli.executor.CommandExecutor.execute_command')
    def test_execute_commands_with_failure(self, mock_execute_command):
        """Test executing multiple commands with one failing."""
        # Mock command executions with second command failing
        mock_execute_command.side_effect = [
            (True, "output1", ""),
            (False, "", "error2")
        ]
        
        # Execute commands
        results = self.executor.execute_commands(["command1", "command2", "command3"])
        
        # Check results
        self.assertEqual(len(results), 2)  # Only two commands should be executed
        self.assertTrue(results[0]["success"])
        self.assertFalse(results[1]["success"])
        self.assertEqual(results[0]["stdout"], "output1")
        self.assertEqual(results[1]["stderr"], "error2")
        
        # Check that execute_command was called only twice (not for command3)
        self.assertEqual(mock_execute_command.call_count, 2)


if __name__ == "__main__":
    unittest.main() 