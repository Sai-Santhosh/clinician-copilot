.PHONY: setup install dev test lint typecheck format migrate seed run eval clean

# Variables
PYTHON := python
PIP := pip
UVICORN := uvicorn

# Setup development environment
setup: install migrate seed
	@echo "Backend setup complete!"

# Install dependencies
install:
	$(PIP) install -e ".[dev]"

# Run development server
dev:
	$(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

# Run production server
run:
	$(UVICORN) app.main:app --host 0.0.0.0 --port 8000

# Run tests
test:
	pytest tests/ -v --cov=app --cov-report=term-missing

# Run tests with coverage report
test-cov:
	pytest tests/ -v --cov=app --cov-report=html
	@echo "Coverage report generated in htmlcov/"

# Run linting
lint:
	ruff check app/ tests/
	ruff format --check app/ tests/

# Run type checking
typecheck:
	mypy app/

# Format code
format:
	ruff format app/ tests/
	ruff check --fix app/ tests/

# Run database migrations
migrate:
	alembic upgrade head

# Create new migration
migration:
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

# Seed admin user
seed:
	$(PYTHON) scripts/seed_admin.py --demo

# Seed only admin
seed-admin:
	$(PYTHON) scripts/seed_admin.py

# Run evaluation
eval:
	$(PYTHON) eval/eval_runner.py

# Generate encryption key
genkey:
	$(PYTHON) -c "from app.core.security import generate_encryption_key; print(generate_encryption_key())"

# Clean up
clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	rm -f clinician_copilot.db test_clinician_copilot.db
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Show help
help:
	@echo "Available targets:"
	@echo "  setup      - Full setup (install, migrate, seed)"
	@echo "  install    - Install dependencies"
	@echo "  dev        - Run development server with reload"
	@echo "  run        - Run production server"
	@echo "  test       - Run tests with coverage"
	@echo "  lint       - Run linting checks"
	@echo "  typecheck  - Run type checking"
	@echo "  format     - Format code"
	@echo "  migrate    - Run database migrations"
	@echo "  seed       - Seed demo users"
	@echo "  eval       - Run AI evaluation"
	@echo "  genkey     - Generate encryption key"
	@echo "  clean      - Clean up generated files"
