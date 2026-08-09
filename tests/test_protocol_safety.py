import ast
from pathlib import Path

import pytest


def test_server_source_has_no_print_calls() -> None:
    for path in Path("server").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert not any(isinstance(node, ast.Call) and getattr(node.func, "id", None) == "print" for node in ast.walk(tree))


def test_deliberate_rogue_stdout_is_not_valid_json_rpc() -> None:
    """A diagnostic reminder: a print before a JSON-RPC frame corrupts stdio."""
    import json
    with pytest.raises(json.JSONDecodeError):
        json.loads("debug: this should have gone to stderr")

