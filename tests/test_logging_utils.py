"""Tests for the log_node decorator."""

import logging
from typing import Any

import pytest

from apply_operator.tools.logging_utils import log_node


class TestLogNodeSync:
    """Tests for log_node with synchronous functions."""

    def test_returns_result(self) -> None:
        @log_node
        def my_node(state: Any) -> dict[str, Any]:
            return {"value": 42}

        result = my_node({})
        assert result == {"value": 42}

    def test_logs_start_and_complete(self, caplog: pytest.LogCaptureFixture) -> None:
        @log_node
        def my_node(state: Any) -> dict[str, Any]:
            return {}

        with caplog.at_level(logging.INFO):
            my_node({})

        messages = [r.message for r in caplog.records]
        assert any("my_node | started" in m for m in messages)
        assert any("my_node | completed" in m for m in messages)

    def test_exception_logged_and_reraised(self, caplog: pytest.LogCaptureFixture) -> None:
        @log_node
        def failing_node(state: Any) -> dict[str, Any]:
            raise ValueError("boom")

        with caplog.at_level(logging.ERROR), pytest.raises(ValueError, match="boom"):
            failing_node({})

        messages = [r.message for r in caplog.records]
        assert any("failing_node | failed" in m for m in messages)
        assert any("ValueError" in m for m in messages)

    def test_preserves_function_name(self) -> None:
        @log_node
        def my_node(state: Any) -> dict[str, Any]:
            return {}

        assert my_node.__name__ == "my_node"


class TestLogNodeAsync:
    """Tests for log_node with async functions."""

    @pytest.mark.asyncio
    async def test_returns_result(self) -> None:
        @log_node
        async def my_async_node(state: Any) -> dict[str, Any]:
            return {"value": 99}

        result = await my_async_node({})
        assert result == {"value": 99}

    @pytest.mark.asyncio
    async def test_logs_start_and_complete(self, caplog: pytest.LogCaptureFixture) -> None:
        @log_node
        async def my_async_node(state: Any) -> dict[str, Any]:
            return {}

        with caplog.at_level(logging.INFO):
            await my_async_node({})

        messages = [r.message for r in caplog.records]
        assert any("my_async_node | started" in m for m in messages)
        assert any("my_async_node | completed" in m for m in messages)

    @pytest.mark.asyncio
    async def test_exception_logged_and_reraised(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        @log_node
        async def failing_async_node(state: Any) -> dict[str, Any]:
            raise RuntimeError("async boom")

        with caplog.at_level(logging.ERROR), pytest.raises(RuntimeError, match="async boom"):
            await failing_async_node({})

        messages = [r.message for r in caplog.records]
        assert any("failing_async_node | failed" in m for m in messages)
        assert any("RuntimeError" in m for m in messages)

    @pytest.mark.asyncio
    async def test_preserves_function_name(self) -> None:
        @log_node
        async def my_async_node(state: Any) -> dict[str, Any]:
            return {}

        assert my_async_node.__name__ == "my_async_node"
