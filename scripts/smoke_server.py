"""Manual Phase 1 MCP round-trip test for SignalRelay itself."""
from __future__ import annotations

import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "server.app"],
        env=os.environ.copy(),
    )
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            tools = await session.list_tools()
            tool_name = os.environ.get("SMOKE_TOOL", "get_signalrelay_signal")
            report = await session.call_tool(tool_name, {"symbol": "RELIANCE"})
            payload = {
                "tools": [tool.name for tool in tools.tools],
                "response": [getattr(item, "text", None) for item in report.content],
            }
            sys.stdout.write(json.dumps(payload, indent=2) + "\n")


if __name__ == "__main__":
    asyncio.run(main())
