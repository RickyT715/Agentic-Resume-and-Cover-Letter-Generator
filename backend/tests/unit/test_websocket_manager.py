"""Tests for WebSocket connection manager."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestConnectionManager:
    def test_init_empty(self):
        from api.websocket import ConnectionManager
        mgr = ConnectionManager()
        assert mgr.active_connections == []

    @pytest.mark.asyncio
    async def test_connect(self):
        from api.websocket import ConnectionManager
        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect(ws)
        assert ws in mgr.active_connections
        ws.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_multiple(self):
        from api.websocket import ConnectionManager
        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await mgr.connect(ws1)
        await mgr.connect(ws2)
        assert len(mgr.active_connections) == 2

    def test_disconnect(self):
        from api.websocket import ConnectionManager
        mgr = ConnectionManager()
        ws = MagicMock()
        mgr.active_connections.append(ws)
        mgr.disconnect(ws)
        assert ws not in mgr.active_connections

    def test_disconnect_not_in_list(self):
        from api.websocket import ConnectionManager
        mgr = ConnectionManager()
        ws = MagicMock()
        # Should not raise
        mgr.disconnect(ws)
        assert len(mgr.active_connections) == 0

    @pytest.mark.asyncio
    async def test_broadcast(self):
        from api.websocket import ConnectionManager
        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        mgr.active_connections = [ws1, ws2]
        msg = {"type": "test", "data": "hello"}
        await mgr.broadcast(msg)
        ws1.send_json.assert_called_once_with(msg)
        ws2.send_json.assert_called_once_with(msg)

    @pytest.mark.asyncio
    async def test_broadcast_removes_disconnected(self):
        from api.websocket import ConnectionManager
        mgr = ConnectionManager()
        ws_good = AsyncMock()
        ws_bad = AsyncMock()
        ws_bad.send_json.side_effect = Exception("disconnected")
        mgr.active_connections = [ws_good, ws_bad]
        await mgr.broadcast({"type": "test"})
        assert ws_bad not in mgr.active_connections
        assert ws_good in mgr.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_empty_connections(self):
        from api.websocket import ConnectionManager
        mgr = ConnectionManager()
        # Should not raise
        await mgr.broadcast({"type": "test"})


class TestProgressCallback:
    @pytest.mark.asyncio
    async def test_progress_callback_broadcasts(self):
        from api.websocket import progress_callback, manager
        original_connections = manager.active_connections[:]
        ws = AsyncMock()
        manager.active_connections = [ws]
        try:
            await progress_callback({"step": "compile_latex", "status": "running"})
            ws.send_json.assert_called_once()
            msg = ws.send_json.call_args[0][0]
            assert msg["type"] == "progress"
            assert msg["data"]["step"] == "compile_latex"
        finally:
            manager.active_connections = original_connections
