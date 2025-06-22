"""
Entry point for running autogen as a module.

Usage: python -m autogen [OPTIONS] COMMAND [ARGS]...
"""

from .cli.main import app

if __name__ == "__main__":
    app()
