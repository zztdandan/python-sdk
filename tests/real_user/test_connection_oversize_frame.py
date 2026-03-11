import json
import sys

import pytest

from acp.connection import Connection
from acp.transports import spawn_stdio_transport


def _oversize_json_line_script(payload_size: int = 80 * 1024) -> str:
    payload = "X" * payload_size
    frame = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"text": payload},
    }
    line = json.dumps(frame)
    return f"import sys\nsys.stdout.write({line!r})\nsys.stdout.write('\\n')\nsys.stdout.flush()\n"


@pytest.mark.asyncio
async def test_connection_persists_oversize_frame_and_raises(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    script = _oversize_json_line_script()

    async with spawn_stdio_transport(sys.executable, "-c", script) as (reader, writer, _process):

        async def _handler(_method, _params, _is_notification):
            return None

        conn = Connection(_handler, writer, reader, listening=False)
        with pytest.raises(ValueError, match="Oversize ACP frame"):
            await conn.main_loop()

    out_dir = tmp_path / "acp_oversize_frames"
    files = list(out_dir.glob("frame_*.jsonl"))
    assert files, "Expected oversize frame record file to be created"
    assert files[0].stat().st_size > 64 * 1024
