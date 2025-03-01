.PHONY: setup run clean help

VENV_NAME=mydigest
VENV_BIN = $(VENV_NAME)/bin
PYTHON_VERSION=python3

# Determine OS and adjust paths
ifeq ($(OS),Windows_NT)
	VENV_BIN = $(VENV_NAME)/Scripts
	PYTHON_VERSION = python
endif

setup:
	@echo "Creating environment ..."
	$(PYTHON_VERSION) -m venv $(VENV_NAME)
	@echo "Installing requirements ..."
	$(VENV_BIN)/pip install -r requirements.txt

run:
	@echo "Running bot ..."
	$(VENV_BIN)/python -m src.bot

clean:
ifeq ($(OS),Windows_NT)
	@echo "Removing environment (Windows)..."
	rmdir /s /q $(VENV_NAME)
else
	@echo "Removing environment (macOS/Linux)..."
	rm -rf $(VENV_NAME)
endif


help:
	@echo "Available commands:"
	@echo "  make setup     : Setup project (create environment and install requirements)"
	@echo "  make run       : Run the mydigest bot"
	@echo "  make clean     : Remove environment"