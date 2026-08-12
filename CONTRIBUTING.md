# Contributing

1. Create a branch from `main`.
2. Install the development dependencies: `python -m pip install -e '.[dev]'`.
3. Run `pytest` and `python -m compileall mybusiness_mcp`.
4. Keep API behavior driven by Google Discovery Documents. A legacy endpoint may
   use a narrow, version-controlled bundled catalog only when Google no longer
   publishes a working Discovery Document, the endpoint remains officially
   documented, and contract tests cover its methods and schemas.
5. Never commit OAuth client secrets, refresh tokens, ADC files, or location/customer data.
