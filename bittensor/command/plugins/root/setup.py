from setuptools import setup, find_packages

setup(
    name='btcli.root',
    version='0.1.0',
    packages=find_packages(),
    entry_points={
        'your_cli_plugins': [
            'plugin_name = your_plugin.module:plugin_function',
        ],
    },
)