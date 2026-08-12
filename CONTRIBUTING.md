# Contributing

1. Create a branch from `main`.
2. Install the development dependencies: `python -m pip install -e '.[dev]'`.
3. Run `pytest` and `python -m compileall mybusiness_mcp`.
4. Keep API behavior driven by Google Discovery Documents rather than duplicating endpoint definitions manually.
5. Never commit OAuth client secrets, refresh tokens, ADC files, or location/customer data.
