.PHONY: setup run clean

CONDA_ENV_NAME=mydigest
PYTHON_VERSION=3.11

setup:
	@echo "Creating conda environment ..." 
	conda create -n ${CONDA_ENV_NAME} python=${PYTHON_VERSION} --yes
	@echo "Installing requirements ..."
	conda run -n ${CONDA_ENV_NAME} pip install -r requirements.txt
    @echo "Conda environment activation ..."
    conda activate ${CONDA_ENV_NAME}

run: setup
	@echo "Running bot ..."
	PYTHONPATH=$(PWD) conda run -n ${CONDA_ENV_NAME} python src/main.py

clean:
	@echo "Removing conda environment ..."
	conda env remove -n ${CONDA_ENV_NAME} --yes

help:
	@echo "Available commands:"
	@echo "  make setup     : Setup project (create conda env and install requirements)"
	@echo "  make run       : Run the mydigest bot"
	@echo "  make clean     : Remove conda environment"