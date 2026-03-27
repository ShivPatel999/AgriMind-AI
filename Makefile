.PHONY: start install setup clean

# AgriMind AI Makefile

start:
	@./start

install:
	@python3 -m venv venv
	@. venv/bin/activate && pip install -r backend/requirements.txt
	@echo "✓ Dependencies installed"

setup:
	@if [ ! -f .env ]; then \
		echo "Create .env file with GROQ_API_KEY=your_key_here"; \
		exit 1; \
	fi
	@$(MAKE) install
	@$(MAKE) start

clean:
	@rm -rf venv __pycache__ .pytest_cache *.pyc
	@echo "✓ Cleaned up"

help:
	@echo "AgriMind AI Commands:"
	@echo "  make start   - Run the server"
	@echo "  make install - Install dependencies"
	@echo "  make setup   - Full setup (install + start)"
	@echo "  make clean   - Remove virtual environment"
