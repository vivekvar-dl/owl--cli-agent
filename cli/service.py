import servicemanager
import socket
import sys
import os
import time
import threading

import win32service
import win32serviceutil
import win32event

# To get the agent and its logger configured
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cli.agent import Agent
from cli.logger import setup_logging

class AgentService(win32serviceutil.ServiceFramework):
    """A Windows service that runs the Gemini agent in the background."""
    _svc_name_ = "GeminiAgent"
    _svc_display_name_ = "Gemini AI Agent"
    _svc_description_ = "Runs a Gemini-powered AI agent to perform background system monitoring and tasks."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.stop_requested = False
        self.agent_thread = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.stop_requested = True
        # Wait for the agent thread to finish
        if self.agent_thread:
            self.agent_thread.join()

    def SvcDoRun(self):
        # Setup logging for the service
        setup_logging(service_mode=True)
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()

    def main(self):
        """The main loop for the service."""
        # The agent's background task loop runs in its own thread
        self.agent_thread = threading.Thread(target=self.agent_task_loop)
        self.agent_thread.start()
        
        # Wait for the stop signal
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STOPPED,
            (self._svc_name_, '')
        )

    def agent_task_loop(self):
        """The loop that runs the agent's background tasks."""
        agent = Agent()
        # Check every 5 minutes
        check_interval_seconds = 300 

        while not self.stop_requested:
            agent.run_background_tasks()
            
            # Wait for the specified interval, but break early if a stop is requested
            wait_result = win32event.WaitForSingleObject(self.hWaitStop, check_interval_seconds * 1000)
            if wait_result == win32event.WAIT_OBJECT_0:
                break

def handle_service_command():
    """Handles the command-line arguments for the service."""
    # This is necessary for the pywin32 library to find the service class
    # when it's being installed or controlled from the command line.
    # The class must be in the global namespace of the script being run.
    # We are essentially making `AgentService` available to the `win32serviceutil` handler.
    globals()['AgentService'] = AgentService
    win32serviceutil.HandleCommandLine(AgentService)

if __name__ == '__main__':
    handle_service_command() 