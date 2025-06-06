# CLI Agent

The CLI Agent is a powerful, tool-augmented agent designed to assist with a wide variety of tasks directly from your command line. It leverages an extensible system of tools to interact with your file system, execute commands, make HTTP requests, manage Git repositories, and much more, streamlining complex workflows and boosting productivity.

## Features

*   Extensible tool system, allowing for easy addition of new capabilities.
*   Interactive mode for step-by-step task execution and refinement.
*   Configuration managed via a central [`config.yaml`](config.yaml:1) file.
*   Core tools for essential operations:
    *   File operations (read, write, list, delete)
    *   Command execution
    *   HTTP requests
    *   Git integration

## Prerequisites

*   Python 3.x

## Installation/Setup

1.  **Clone the repository:**
    ```bash
    git clone <YOUR_REPOSITORY_URL_HERE>
    cd cli-agent
    ```
2.  **Install dependencies:**
    It's recommended to create a virtual environment first.
    ```bash
    pip install -r requirements.txt
    ```
    The requirements file lists runtime packages such as `google-cloud-aiplatform`,
    `vertexai`, `requests`, and `PyYAML`.
3.  **Configure the agent:**
    Copy the example configuration file (if one is provided, e.g., `config.example.yaml`) to [`config.yaml`](config.yaml:1) and customize it according to your needs. At a minimum, you will need to review and potentially update settings in [`config.yaml`](config.yaml:1).

## Basic Usage

To run the agent with a specific task:

```bash
python agent.py "Your task description here, for example: list all python files in the current directory"
```

The agent also supports an interactive mode, which can be triggered by running the agent without a specific task or with a flag (details to be defined). This mode allows for a more conversational approach to task execution.

## Available Tools

The agent comes equipped with a suite of built-in tools to perform various operations. Some examples include:

*   `read_file`: Reads the content of a specified file.
*   `write_file`: Writes content to a specified file.
*   `execute_command`: Executes a shell command.
*   `git_tool`: Performs Git operations like clone, commit, push.

New tools can be developed and integrated to extend the agent's capabilities.

## Configuration

The agent's behavior is controlled through the [`config.yaml`](config.yaml:1) file. Key configurable aspects include:

*   GCP Project ID (if using Google Cloud services)
*   Default AI Model name
*   Safe mode settings (to prevent accidental execution of harmful commands)
*   API keys for various services

Refer to the comments within [`config.yaml`](config.yaml:1) (or `config.example.yaml`) for detailed explanations of each configuration option.

## Contributing

Contributions are welcome! Please see `CONTRIBUTING.md` for guidelines on how to contribute to this project.

## License

This project is licensed under the BSD 3-Clause License - see the `LICENSE` file for details.
