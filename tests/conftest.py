"""Shared test fixtures."""

import os
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def tmp_storage(tmp_path):
    """Storage backed by a temporary directory."""
    from core.storage import Storage
    return Storage(base_dir=str(tmp_path / ".investment-assistant"))


@pytest.fixture
def sample_stock_playbook():
    return {
        "stock_name": "TestCorp",
        "ticker": "TC",
        "core_thesis": {
            "summary": "Test thesis",
            "key_points": ["point1", "point2"],
            "market_gap": "Test gap"
        },
        "validation_signals": ["signal1"],
        "invalidation_triggers": ["trigger1"],
        "operation_plan": {
            "holding_period": "6 months",
            "target_price": 100,
            "stop_loss": 80,
            "position_size": "5%"
        },
        "related_entities": ["CompA", "CompB"],
    }


@pytest.fixture
def mock_openai_client():
    """Patch OpenAI so OpenAIClient can be instantiated without a real key."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "mock response"

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("core.openai_client.OpenAI", return_value=mock_client) as mock_cls:
        yield {
            "client_cls": mock_cls,
            "client_instance": mock_client,
            "response": mock_response,
        }
