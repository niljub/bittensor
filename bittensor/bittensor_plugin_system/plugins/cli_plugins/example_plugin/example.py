from bittensor.bittensor_plugin_system.core.base_plugin import BasePlugin
import logging


class ExamplePlugin(BasePlugin):
    """
    An example plugin that extends the BasePlugin abstract class,
    demonstrating the implementation of a concrete plugin.
    """

    def initialize(self, config_path: str) -> None:
        """
        Initializes the ExamplePlugin with specific configuration.

        Overrides the initialize method from BasePlugin to perform
        plugin-specific initialization logic.

        Args:
            config_path (str): The path to the configuration YAML file.
        """
        super().initialize(config_path)
        # Additional initialization logic specific to ExamplePlugin
        self.logger.info("ExamplePlugin initialized with config at %s", config_path)

    def _core_execute(self, data: any) -> any:
        """
        The core functionality of the ExamplePlugin.

        Args:
            data (any): Input data for the plugin to process.

        Returns:
            any: The result of processing the input data. For demonstration, returns the data.
        """
        # Implement the core functionality of the plugin here
        self.logger.info("Executing ExamplePlugin with data: %s", data)
        # For demonstration purposes, return the input data
        return data

    def shutdown(self) -> None:
        """
        Shuts down the ExamplePlugin, releasing any resources if necessary.

        Overrides the shutdown method from BasePlugin to perform
        plugin-specific cleanup and resource release.
        """
        # Implement cleanup and resource release here
        self.logger.info("Shutting down ExamplePlugin.")
