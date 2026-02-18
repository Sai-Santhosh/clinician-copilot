.PHONY: setup install dev build test lint typecheck clean

# Variables
NPM := npm

# Setup development environment
setup: install
	@echo "Frontend setup complete!"

# Install dependencies
install:
	$(NPM) install

# Run development server
dev:
	$(NPM) run dev

# Build for production
build:
	$(NPM) run build

# Run tests
test:
	$(NPM) run test

# Run tests with UI
test-ui:
	$(NPM) run test:ui

# Run tests with coverage
test-cov:
	$(NPM) run test:coverage

# Run linting
lint:
	$(NPM) run lint

# Run type checking
typecheck:
	$(NPM) run typecheck

# Preview production build
preview:
	$(NPM) run preview

# Clean up
clean:
	rm -rf node_modules dist coverage
	rm -f package-lock.json

# Show help
help:
	@echo "Available targets:"
	@echo "  setup      - Install dependencies"
	@echo "  install    - Install dependencies"
	@echo "  dev        - Run development server"
	@echo "  build      - Build for production"
	@echo "  test       - Run tests"
	@echo "  lint       - Run linting"
	@echo "  typecheck  - Run type checking"
	@echo "  clean      - Clean up generated files"
