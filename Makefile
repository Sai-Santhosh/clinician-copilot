.PHONY: setup setup-backend setup-frontend dev dev-backend dev-frontend test lint clean help

# Default target
all: setup

# Full setup
setup: setup-backend setup-frontend
	@echo ""
	@echo "========================================="
	@echo "Setup complete!"
	@echo "========================================="
	@echo ""
	@echo "To start the application, run:"
	@echo "  make dev"
	@echo ""
	@echo "Or run backend and frontend separately:"
	@echo "  make dev-backend"
	@echo "  make dev-frontend"
	@echo ""

# Setup backend
setup-backend:
	@echo "Setting up backend..."
	cd backend && pip install -e ".[dev]"
	cd backend && alembic upgrade head
	cd backend && python scripts/seed_admin.py --demo
	@echo "Backend setup complete!"

# Setup frontend
setup-frontend:
	@echo "Setting up frontend..."
	cd frontend && npm install
	@echo "Frontend setup complete!"

# Run both backend and frontend (requires two terminals or use &)
dev:
	@echo "Starting development servers..."
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:5173"
	@echo ""
	@echo "Run these in separate terminals:"
	@echo "  make dev-backend"
	@echo "  make dev-frontend"

# Run backend development server
dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run frontend development server
dev-frontend:
	cd frontend && npm run dev

# Run all tests
test: test-backend test-frontend
	@echo "All tests completed!"

# Run backend tests
test-backend:
	cd backend && pytest tests/ -v --cov=app

# Run frontend tests
test-frontend:
	cd frontend && npm run test -- --run

# Run linting
lint: lint-backend lint-frontend
	@echo "All linting completed!"

# Lint backend
lint-backend:
	cd backend && ruff check app/ tests/
	cd backend && ruff format --check app/ tests/

# Lint frontend
lint-frontend:
	cd frontend && npm run lint

# Type checking
typecheck: typecheck-backend typecheck-frontend
	@echo "Type checking completed!"

# Type check backend
typecheck-backend:
	cd backend && mypy app/

# Type check frontend
typecheck-frontend:
	cd frontend && npm run typecheck

# Run evaluation
eval:
	cd backend && python eval/eval_runner.py

# Database migrations
migrate:
	cd backend && alembic upgrade head

# Seed demo users
seed:
	cd backend && python scripts/seed_admin.py --demo

# Generate encryption key
genkey:
	cd backend && python -c "from app.core.security import generate_encryption_key; print(generate_encryption_key())"

# Clean up
clean:
	cd backend && rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	cd backend && rm -f clinician_copilot.db test_clinician_copilot.db
	cd backend && find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	cd frontend && rm -rf node_modules dist coverage

# Show help
help:
	@echo "Clinician Copilot - Development Commands"
	@echo "========================================="
	@echo ""
	@echo "Setup:"
	@echo "  make setup          - Full setup (backend + frontend)"
	@echo "  make setup-backend  - Setup backend only"
	@echo "  make setup-frontend - Setup frontend only"
	@echo ""
	@echo "Development:"
	@echo "  make dev-backend    - Run backend server"
	@echo "  make dev-frontend   - Run frontend server"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run all tests"
	@echo "  make test-backend   - Run backend tests"
	@echo "  make test-frontend  - Run frontend tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           - Run all linting"
	@echo "  make typecheck      - Run type checking"
	@echo ""
	@echo "Other:"
	@echo "  make eval           - Run AI evaluation"
	@echo "  make migrate        - Run database migrations"
	@echo "  make seed           - Seed demo users"
	@echo "  make genkey         - Generate encryption key"
	@echo "  make clean          - Clean up generated files"
