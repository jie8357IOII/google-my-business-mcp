import nox


@nox.session(python=["3.10", "3.11", "3.12", "3.13"])
def tests(session):
    session.install("-e", ".[dev]")
    session.run("pytest")


@nox.session
def lint(session):
    session.install("ruff")
    session.run("ruff", "check", "mybusiness_mcp", "tests")
