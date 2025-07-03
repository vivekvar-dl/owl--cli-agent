# 🦉 Owl CLI: Your OS-Level AI Assistant

Owl CLI is a next-generation command-line interface that bridges the gap between natural language and system operations. Powered by Google's Gemini large language models, it functions as an intelligent, OS-integrated assistant that can understand your goals, execute commands, perform system analysis, and even operate autonomously in the background.

Unlike traditional CLIs that require you to know a rigid set of commands and flags, Owl CLI allows you to state your intent in plain English. It's designed to be a powerful tool for developers, system administrators, and anyone looking to streamline their workflow and interact with their operating system in a more intuitive way.

## ✨ Features

- **Natural Language Command Translation**: Simply tell the CLI what you want to do, and it will generate and execute the appropriate shell commands for you.
- **Interactive Autonomous Agent**: Engage in a conversational session with an AI agent that can execute multi-step plans, use tools to gather information, and even attempt to self-correct when it runs into errors.
- **Comprehensive Security Audit**: Perform a detailed security audit of your Windows system. The agent collects information on system policies, installed packages, and security event logs, then uses its intelligence to generate a professional-grade Markdown report with actionable recommendations.
- **Background Service Monitoring**: Install and run the agent as a background Windows service. In this mode, it can perform autonomous, periodic tasks, such as monitoring for system policy violations and logging its findings.
- **User-Friendly Home Page**: A clean, interactive home page guides you through the available features, making the tool accessible right from the start.

## ⚙️ Setup and Installation

Follow these steps to get Owl CLI up and running on your Windows machine.

### 1. Prerequisites
- Python 3.8+
- Git

### 2. Clone the Repository
```bash
git clone <your-repository-url>
cd owl-cli
```

### 3. Set up a Virtual Environment (Recommended)
```bash
python -m venv venv
venv\Scripts\activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Your API Key
The CLI requires a Google Gemini API key to function.

- Create a `.env` file in the root of the project directory.
- Add your API key to this file:

```env
GEMINI_API_KEY="YOUR_API_KEY_HERE"
```

You can get an API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

## 🚀 Usage

The easiest way to start is by launching the interactive home page.

```bash
python -m cli.cli
```

This will greet you with a menu of options.

### Home Page

The interactive home page allows you to easily navigate to the desired feature.

```
 C:\Users\you\owl-cli> python -m cli.cli

 ╭───────────────────────────── 🦉 Owl CLI ──────────────────────────────╮
 │                 Welcome to the Owl CLI!                  │
 │               Your OS-level AI Assistant               │
 ╰──────────────────────────────────────────────────────────────────────╯
  1.  Run a single, one-off command (e.g., 'list all python files')
  2.  Start an interactive session with the autonomous agent
  3.    Run a comprehensive security audit of the system
  4.  Manage the background service (install, start, stop)
  5.  Exit

 What would you like to do? [1/2/3/4/5] (1):
```

### Command Reference

You can also call commands directly.

#### Run a Single Command

```bash
python -m cli.cli run "your instruction here"
```

**Example:**
```bash
python -m cli.cli run "list all text files in the current directory and count them"
```
```
   Generated Commands
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Command                     ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ dir *.txt | find /c /v ""   │
└─────────────────────────────┘
╭───────────────────────────────── Explanation ──────────────────────────────────╮
│ This command first lists all files with the '.txt' extension in the current    │
│ directory and then pipes the output to the 'find' command to count the number  │
│ of lines, effectively counting the files.                                      │
╰────────────────────────────────────────────────────────────────────────────────╯
 Execute these commands? [y/n]:
```

#### Start the Autonomous Agent

```bash
python -m cli.cli agent
```
```
 Welcome to the Interactive Agent Session!
 Type 'quit' or 'exit' to end.

 You: Find out my public IP address
 Agent: Figuring out next action...

╭──────────────────────── Proposed Tool Call ─────────────────────────╮
│ Tool: web_search                                                   │
│ Args: {'query': 'what is my public IP address'}                    │
│                                                                    │
│ I need to find the user's public IP address. The most reliable way │
│ to do this is to use a web search, as external websites will see   │
│ the request coming from the public IP.                             │
╰────────────────────────────────────────────────────────────────────╯
 Agent [y/q/s] (y): y
╭─────────────────── Tool Output: web_search ────────────────────╮
│ {                                                              │
│     "success": true,                                           │
│     "results": [                                               │
│         {                                                      │
│             "title": "What Is My IP Address? - See Your Public │
│ Address - NordVPN",                                            │
│             "link": "https://nordvpn.com/what-is-my-ip/",       │
│             "snippet": "Your public IP address is 203.0.113.42"│
│         }                                                      │
│     ]                                                          │
│ }                                                              │
╰────────────────────────────────────────────────────────────────╯
 You:
```

#### Run a Security Audit

> **Note:** This command must be run from a terminal with **Administrator privileges** to access the Windows Security Event Log.

```bash
python -m cli.cli audit
```
```
╭──────────────────────────────── Security Audit Mode ─────────────────────────────────╮
│                           Starting Automated Security Audit                            │
╰──────────────────────────────────────────────────────────────────────────────────────╯
 System information collected.
 Querying Windows Security Event Log...
 Audit data collection complete.
 Generating security report...
╭─────────────────────────────── Security Audit Report ────────────────────────────────╮
│ # Security Audit Report                                                              │
│                                                                                      │
│ ## 1. Executive Summary                                                              │
│                                                                                      │
│ This report summarizes the security posture of the audited Windows 11 system.        │
│ Overall, the system shows good policy compliance and a relatively modern software    │
│ inventory. However, a critical finding is the presence of build tools for Visual     │
│ Studio 2019, which is now out of mainstream support...                               │
│                                                                                      │
│ ## 5. Recommendations                                                                │
│                                                                                      │
│ 1.  **Address Security Event Access**: The audit was unable to read Windows          │
│     Security Events due to insufficient privileges. This is a critical gap...        │
│ 2.  **Review Visual Studio 2019 Build Tools**: As Visual Studio 2019 is out of       │
│     mainstream support, assess if the `visualstudio2019buildtools` package is        │
│     still required...                                                                │
│                                                                                      │
╰──────────────────────────────────────────────────────────────────────────────────────╯

 Report saved to security_audit_report.md
```

#### Manage the Background Service

> **Note:** These commands must be run from a terminal with **Administrator privileges**.

```bash
# Install the service
python -m cli.cli service install

# Start the service
python -m cli.cli service start

# Stop the service
python -m cli.cli service stop

# Remove the service
python -m cli.cli service remove
```
The service will run autonomously in the background, checking for system policy violations every 5 minutes and logging its findings to `C:\Users\<YourUser>\.config\gemini-cli\logs\agent.log`.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google Gemini API for natural language understanding
- The Rich library for beautiful terminal output 