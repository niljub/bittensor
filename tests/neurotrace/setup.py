from setuptools import setup, find_packages

setup(
    name="NeuroTrace",
    version="0.1",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'btcli=neurotrace.bin.btcli:main',
        ],
    },
)
