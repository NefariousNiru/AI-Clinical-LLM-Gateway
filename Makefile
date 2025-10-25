# Makefile

# Default target
.DEFAULT_GOAL := all

.PHONY: all format lint test

# Run everything
all: format lint test

# Auto-fix with Ruff + format with Black
format:
	ruff check . --fix
	black .

# Lint only (no fixes)
lint:
	ruff check .
	black --check .

# Run tests
test:
	pytest -v --maxfail=1 --disable-warnings
