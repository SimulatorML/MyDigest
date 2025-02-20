.PHONY: setup run clean help

CONDA_ENV_NAME=mydigest
PYTHON_VERSION=3.11


setup:
	@echo "Creating conda environment ..."
	conda create -n ${CONDA_ENV_NAME} python=${PYTHON_VERSION} --yes
	@echo "Installing requirements ..."
	conda run -n ${CONDA_ENV_NAME} pip install -r requirements.txt

run:
	@echo "Running bot ..."
	conda run -n ${CONDA_ENV_NAME} python -m src.bot

clean:
	@echo "Removing conda environment ..."
	conda env remove -n ${CONDA_ENV_NAME} --yes

help:
	@echo "Available commands:"
	@echo "  make setup     : Setup project (create conda env and install requirements)"
	@echo "  make run       : Run the mydigest bot"
	@echo "  make clean     : Remove conda environment"
