import torch
import pytest
import time
from unittest.mock import MagicMock, patch, ANY
from bittensor import subtensor, wallet
from bittensor.extrinsics.set_weights import set_weights_extrinsic


@pytest.fixture
def mock_subtensor():
    mock = MagicMock(spec=subtensor)
    mock.network = "mock_network"
    return mock


@pytest.fixture
def mock_wallet():
    mock = MagicMock(spec=wallet)
    return mock


@pytest.fixture
def mock_wait_epoch():
    with patch('bittensor.utils.subtensor.wait_epoch') as mock:
        mock.side_effect = lambda interval, subtensor: time.sleep(1)
        yield mock


@pytest.mark.parametrize(
    "uids,        weights,      wait_for_inclusion,  wait_for_finalization, prompt,  user_accepts,  commit_success,  reveal_success,  expected_message",
    [
        ([1, 2],  [0.4, 0.4],   True,                False,                 True,    True,          True,            True,              "Successfully set weights and finalized using commit-reveal."),
        ([1, 2],  [0.5, 0.4],   False,               False,                 False,   True,          True,            True,              "Not waiting for finalization or inclusion."),
        ([1, 2],  [0.5, 0.5],   True,                False,                 True,    True,          False,           False,             "Failed to commit weights."),
        ([1, 2],  [0.5, 0.5],   True,                False,                 True,    True,          True,            False,             "Failed to reveal weights."),
        ([1, 2],  [0.5, 0.5],   True,                True,                  True,    False,         False,           False,             "Prompt refused."),
    ],
    ids=[
        "happy-flow-WITH-commit-reveal",
        "not-waiting-finalization-inclusion",
        "error-flow-commit-failure",
        "error-flow-reveal-failure",
        "prompt-refused",
    ],
)

def test_set_weights_extrinsic_with_commit_reveal_active(
    mock_subtensor,
    mock_wallet,
    mock_wait_epoch,
    uids,
    weights,
    wait_for_inclusion,
    wait_for_finalization,
    prompt,
    user_accepts,
    commit_success,
    reveal_success,
    expected_message,
):
    uids_tensor = torch.tensor(uids, dtype=torch.int64)
    weights_tensor = torch.tensor(weights, dtype=torch.float32)
    with patch(
        "bittensor.utils.weight_utils.convert_weights_and_uids_for_emit",
        return_value=(uids_tensor, weights_tensor),
    ), patch(
        "rich.prompt.Confirm.ask", return_value=user_accepts
    ), patch.object(
        mock_subtensor,
        "commit_reveal_active",
        return_value=True,
    ) as mock_commit_reveal_active, patch.object(
        mock_subtensor,
        "commit_weights",
        return_value=(commit_success, "Mock return message"),
    ) as mock_commit_weights, patch.object(
        mock_subtensor,
        "reveal_weights",
        return_value=(reveal_success, "Mock return message")
    ) as mock_reveal_weights, patch.object(
        mock_subtensor,
        "_do_set_weights",
        return_value=(False, "Mock error message"),
    ) as mock_do_set_weights, patch(
        'bittensor.extrinsics.set_weights.wait_epoch', mock_wait_epoch
    ):
        result, message = set_weights_extrinsic(
            subtensor=mock_subtensor,
            wallet=mock_wallet,
            netuid=123,
            uids=uids,
            weights=weights,
            version_key=0,
            wait_for_inclusion=wait_for_inclusion,
            wait_for_finalization=wait_for_finalization,
            prompt=prompt,
        )

        assert result == (commit_success and reveal_success), f"Test {expected_message} failed."
        assert message == expected_message, f"Test {expected_message} failed."

        if user_accepts:
            mock_commit_weights.assert_called_once_with(
                wallet=mock_wallet,
                netuid=123,
                salt=ANY,
                uids=uids_tensor,
                weights=weights_tensor,
                wait_for_finalization=wait_for_finalization,
                wait_for_inclusion=wait_for_inclusion,
            )
            if commit_success:
                    mock_reveal_weights.assert_called_once_with(
                        wallet=mock_wallet,
                        netuid=123,
                        salt=ANY,
                        uids=uids_tensor,
                        weights=weights_tensor,
                        wait_for_finalization=wait_for_finalization,
                        wait_for_inclusion=wait_for_inclusion,
                    )
            else:
                mock_reveal_weights.assert_not_called()
        else:
            mock_commit_reveal_active.assert_not_called()
            mock_do_set_weights.assert_not_called()
            mock_commit_weights.assert_not_called()
            mock_reveal_weights.assert_not_called()


@pytest.mark.parametrize(
    "uids,        weights,      wait_for_inclusion,  wait_for_finalization, prompt,  user_accepts,  expected_success,  expected_message",
    [
        ([1, 2],  [0.5, 0.5],   True,                False,                 True,    True,          True,              "Successfully set weights and finalized."),
        ([1, 2],  [0.5, 0.4],   False,               False,                 False,   True,          True,              "Not waiting for finalization or inclusion."),
        ([1, 2],  [0.5, 0.5],   True,                False,                 True,    True,          False,             "Mock error message"),
        ([1, 2],  [0.5, 0.5],   True,                True,                  True,    False,         False,             "Prompt refused."),
    ],
    ids=[
        "happy-flow",
        "not-waiting-finalization-inclusion",
        "error-flow",
        "prompt-refused",
    ],
)
def test_set_weights_extrinsic_with_commit_reveal_inactive(
    mock_subtensor,
    mock_wallet,
    mock_wait_epoch,
    uids,
    weights,
    wait_for_inclusion,
    wait_for_finalization,
    prompt,
    user_accepts,
    expected_success,
    expected_message,
):
    uids_tensor = torch.tensor(uids, dtype=torch.int64)
    weights_tensor = torch.tensor(weights, dtype=torch.float32)
    with patch(
        "bittensor.utils.weight_utils.convert_weights_and_uids_for_emit",
        return_value=(uids_tensor, weights_tensor),
    ), patch(
        "rich.prompt.Confirm.ask", return_value=user_accepts
    ), patch.object(
        mock_subtensor,
        "commit_reveal_active",
        return_value=False,
    ) as mock_commit_reveal_active, patch.object(
        mock_subtensor,
        "commit_weights",
        return_value=(expected_success, "Mock return message"),
    ) as mock_commit_weights, patch.object(
        mock_subtensor,
        "reveal_weights",
        return_value=(expected_success, "Mock return message")
    ) as mock_reveal_weights, patch.object(
        mock_subtensor,
        "_do_set_weights",
        return_value=(expected_success, "Mock error message"),
    ) as mock_do_set_weights, patch(
        'bittensor.extrinsics.set_weights.wait_epoch', mock_wait_epoch
    ):
        result, message = set_weights_extrinsic(
            subtensor=mock_subtensor,
            wallet=mock_wallet,
            netuid=123,
            uids=uids,
            weights=weights,
            version_key=0,
            wait_for_inclusion=wait_for_inclusion,
            wait_for_finalization=wait_for_finalization,
            prompt=prompt,
        )

        assert result == expected_success, f"Test {expected_message} failed."
        assert message == expected_message, f"Test {expected_message} failed."

        if user_accepts:
            # mock_commit_reveal_active.assert_has_calls()
            mock_do_set_weights.assert_called_once_with(
                wallet=mock_wallet,
                netuid=123,
                uids=uids_tensor,
                vals=weights_tensor,
                version_key=0,
                wait_for_finalization=wait_for_finalization,
                wait_for_inclusion=wait_for_inclusion,
            )
            mock_commit_weights.assert_not_called()
            mock_reveal_weights.assert_not_called()
        else:
            mock_commit_reveal_active.assert_not_called()
            mock_do_set_weights.assert_not_called()
            mock_commit_weights.assert_not_called()
            mock_reveal_weights.assert_not_called()
