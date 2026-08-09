"""Vercel Function entrypoint; the stdio MCP entrypoint remains server.app."""
from api.app import app

__all__ = ["app"]
