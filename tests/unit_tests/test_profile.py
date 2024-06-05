# Standard Library
from copy import deepcopy
from unittest.mock import patch, MagicMock, mock_open
from yaml import dump

# 3rd Party
import pytest
from munch import Munch

# Bittensor
from bittensor.commands.profile import ProfileCreateCommand
from bittensor import config as bittensor_config


class MockDefaults:
    profile = {
        "name": "default",
        "path": "~/.bittensor/profiles/",
    }

@pytest.mark.parametrize(
    "test_input,expected",
    [
        (
            {
                "profile": {
                    "name": "EmptyProfile",
                },
            },
            "EmptyProfile",
        ),
        (
            {
                "profile": {
                    "name": "PopulatedProfile",
                },
                "wallet": {
                    "name": "test_wallet_name",
                    "hotkey": "test_wallet_hotkey",
                    "path": "test_wallet_path",
                },
                "subtensor": {
                    "network": "test_subtensor_network",
                },
                "netuid": "1",
            },
            "PopulatedProfile",
        ),
    ],
    ids=["EmptyProfile", "PopulatedProfile"],
)

@patch("bittensor.commands.profile.ProfileCreateCommand._write_profile")
@patch("bittensor.commands.profile.defaults", MockDefaults)
def test_create_profile(mock_write_profile, test_input, expected):
    # Arrange
    mock_cli = MagicMock()
    mock_cli.config = Munch(test_input.items())

    # Act
    ProfileCreateCommand.run(mock_cli)

    # Assert
    mock_write_profile.assert_called_once()
    assert mock_cli.config.profile["name"] == expected

@pytest.mark.parametrize(
    "test_input, expected",
    [
        (
            bittensor_config(),
            True,
        ),
        # Edge cases
        (
            None,
            False,
        ),
    ],
)
def test_check_config(test_input, expected):
    # Arrange - In this case, all inputs are provided via test parameters, so we omit the Arrange section.

    # Act
    result = ProfileCreateCommand.check_config(test_input)

    # Assert
    assert result == expected


def test_write_profile():
    config = Munch(
        {
            "profile": {
                "name": "test",
                "path": "~/.bittensor/profiles/",
            },
            "wallet": {
                "name": "test_wallet_name",
                "hotkey": "test_wallet_hotkey",
                "path": "test_wallet_path",
            },
            "subtensor": {
                "network": "test_subtensor_network",
            },
            "netuid": "1",
        },
    )
    path = config.profile["path"]
    name = config.profile["name"]

    # Setup the mock for os.makedirs and open
    with patch("os.makedirs") as mock_makedirs, patch(
        "os.path.expanduser", return_value=path
    ), patch("builtins.open", mock_open()) as mock_file:
        ProfileCreateCommand._write_profile(config)

        # Assert that makedirs was called correctly
        mock_makedirs.assert_called_once_with(config.profile["path"], exist_ok=True)

        # Assert that open was called correctly; construct the expected file path and contents
        expected_path = f"{path}/btcli-{name}.yaml"

        # Assert the open function was called correctly and the right contents were written
        mock_file.assert_called_once_with(expected_path, "w+")
        mock_file().write.assert_called_once_with(dump(config))