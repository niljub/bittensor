import unittest
from bittensor.bittensor_plugin_system.plugins.example_plugin import ExamplePlugin


class TestExamplePlugin(unittest.TestCase):
    def test_example_plugin_execute(self):
        """Test the _core_execute method of ExamplePlugin."""
        plugin = ExamplePlugin()
        plugin.initialize("example_plugin/config.yaml")  # Assuming a valid path
        test_data = "test"
        result = plugin._core_execute(test_data)
        self.assertEqual(
            result, test_data, "The _core_execute method should return the input data."
        )


if __name__ == "__main__":
    unittest.main()
