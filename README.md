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
python agent.py "list all python files in the current directory"
```

For an interactive session simply run:

```bash
python agent.py
```

This starts a conversation where you can iteratively provide tasks and review the agent's responses.

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

### Required Environment Variables

The following environment variables must be set for the tools to function correctly:

* `TAVILY_API_KEY` - API key for Tavily web search used by `tavilytool.py`.
* `GOOGLE_APPLICATION_CREDENTIALS` - Path to the Google Cloud service account JSON file.

Example:

```bash
export TAVILY_API_KEY="your-tavily-key"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
```

### Tavily Web Search CLI

You can use the standalone search script `tavilytool.py` to quickly query the web:

```bash
python tavilytool.py "open source llm projects" --depth advanced --max-results 3
```

This requires the `TAVILY_API_KEY` environment variable to be set as shown above.

## Contributing

Contributions are welcome! Please see `CONTRIBUTING.md` for guidelines on how to contribute to this project.

## License

This project is licensed under the BSD 3-Clause License - see the `LICENSE` file for details.
