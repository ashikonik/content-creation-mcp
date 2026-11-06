"""Build-time tooling for the content-creation MCP server.

This package holds the scripts that generate the server's data artifacts:

* ``build_index.py`` — writes ``data/index.json`` from ``skills/`` and
  ``agents/``.
* ``build_provenance.py`` — writes ``data/provenance.json``, the licence and
  origin table.
* ``write_credits.py`` — regenerates ``CREDITS.md`` from the provenance
  table.

The module exists so ``packages = ["build"]`` in ``pyproject.toml`` resolves
to an actual package; without it the console-script entry points fail on
install.
"""
