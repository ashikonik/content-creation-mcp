# content-creation-mcp — build tooling

This directory holds two things that ship separately from the top-level
project README:

- `src/` — the TypeScript MCP server. See the project README for usage.
- `build/` — the Python scripts that generate the server's data artifacts.

## What the build produces

| Script | Reads | Writes |
|---|---|---|
| `python3 -m build.build_index` | `../skills/`, `../agents/` | `data/index.json` |
| `python3 -m build.build_provenance` | the corpus + `data/excluded.json` | `data/provenance.json` |
| `python3 -m build.write_credits` | `data/provenance.json` | `../CREDITS.md` |

Each script accepts `--check`, which verifies the committed artifact is
byte-identical to what a fresh run would produce and exits non-zero
otherwise. This is the determinism gate: CI runs both `--check` variants,
so a stale or hand-edited artifact fails the build.

`build_index.py` pins `generated_at` to the Unix epoch rather than wall
clock time. That is deliberate — a real timestamp would make the output
differ on every run and break the byte-reproducibility the `--check` gate
depends on.

## Regenerating

From the repository root:

```bash
python3 mcp/build/build_index.py
python3 mcp/build/build_provenance.py
python3 mcp/build/write_credits.py
```

The order matters: `build_provenance.py` reads `data/index.json` to pick up
content domains, and `write_credits.py` reads `data/provenance.json`.

## Licensing

`data/provenance.json` records where every skill and agent came from and
which licence governs it. The licence is detected **at the upstream origin**,
not in this repository — a skill copied here keeps its original licence, and
content with no discoverable licence is recorded as `UNKNOWN` rather than
inheriting this project's MIT licence.

Publishing an `UNKNOWN`-licensed entry requires an explicit human sign-off
listed in `LICENCE_SIGNOFF` in `build/build_provenance.py`. Without that
entry the build fails, so an unverified licence can never be reintroduced
silently.

## Installing

The Python package installs the build scripts as console entry points:

```bash
pip install .
content-creation-mcp-build-index --check
```

The MCP server itself is Node-based and is not affected by this package.
