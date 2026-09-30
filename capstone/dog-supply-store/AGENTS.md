# Dog Supply Store agent guide

This is a standalone, local-first Python capstone. Keep its runtime and tests
inside the Python standard library; do not change the workshop application.

## Boundaries

- Keep application code, tests, local data, and instructions in this directory.
- The capstone-specific GitHub Actions workflow lives in the repository's
  `.github/workflows/` directory because GitHub requires that location.
- The default server bind address is loopback. Do not expose the demo publicly
  or collect real payment credentials.
- Keep product and checkout behavior dog-first, playful, and accessible.

## Validation

From this directory, run:

```powershell
py -m unittest discover -s tests -v
py -m compileall -q dog_supply_store tests
```

Use only Python's standard library. The CI workflow runs the same checks.
