.PHONY: setup run clean help

VENV_NAME=mydigest
PYTHON_VERSION=python3


setup:
	@echo "Creating environment ..."
	$(PYTHON_VERSION) -m venv $(VENV_NAME)
	@echo "Installing requirements ..."
	$(VENV_NAME)/bin/pip install -r requirements.txt

run:
	@echo "Running bot ..."
	$(VENV_NAME)/bin/python -m src.bot

clean:
	@echo "Removing conda environment ..."
	rm -rf $(VENV_NAME)

help:
	@echo "Available commands:"
	@echo "  make setup     : Setup project (create environment and install requirements)"
	@echo "  make run       : Run the mydigest bot"
	@echo "  make clean     : Remove environment"
