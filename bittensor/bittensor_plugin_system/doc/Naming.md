# Plugin System Naming Convention Documentation

To maintain a consistent and organized architecture within the Bittensor Plugin System, a clear and concise naming convention is established. This convention ensures easy identification, management, and extension of plugins. Below are the defined standards for naming various components of the plugin system.

## Directory Naming

- **Suffix Requirement**: All plugin directories must have the suffix `_plugin`. This suffix clearly identifies a directory as containing plugin code.
  - **Example**: `redis_transport_plugin`, `subnet_cli_plugin`

## Main Plugin File Naming

- **Uniform Name**: The main file within each plugin directory should have a uniform name across all plugins to simplify the identification of the plugin's entry point.
  - **Example**: For a plugin directory named `subnet_cli_plugin`, the main file should be named `subnet_cli_plugin.py`.

## Configuration Defaults File Naming

- **Uniform Name**: The defaults config file within each plugin directory should have a uniform name across all plugins to simplify the identification of the plugin's defaults.
  - **Example**: For a plugin directory named `subnet_cli_plugin`, the defauls file should be named `defaults.yml`.

## Plugin Class Naming

- **Type Inclusion**: All plugin classes should include the name of the type of plugin they represent. This inclusion helps in quickly understanding the plugin's purpose and categorizing it accordingly.
  - **Transport Plugin Example**: A transport plugin for Redis should be named `RedisTransport`.
  - **CLI Plugin Example**: A CLI plugin for managing subnets should be named `SubnetCLI`.

## Plugin Configuration Class Naming

- **Suffix Convention**: For plugins that require backward compatibility with the legacy CLI or have specific configuration classes, such classes should be named with the suffix `Config` and should precede with the Plugin's name.
  - **Example**: For a `SubnetCLI` plugin, the configuration class should be named `SubnetCLIConfig`.

## General Guidelines

- **Clarity and Consistency**: Names should be clear, concise, and consistent across the plugin ecosystem. Avoid abbreviations unless they are commonly understood.
- **CamelCase for Classes**: Use CamelCase for class names to maintain readability and adhere to Python's naming conventions.
- **Lowercase with Underscores for Directories and Files**: Use lowercase letters for directory and file names, separating words with underscores. This approach matches Python's package and module naming conventions.
