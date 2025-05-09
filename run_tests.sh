#!/bin/bash
# Script to run all tests in the kickbot project

# Activate the conda environment if not already activated
if [[ -z "${CONDA_DEFAULT_ENV}" || "${CONDA_DEFAULT_ENV}" != "kickbot" ]]; then
    echo "Activating kickbot conda environment..."
    # Ensure conda is correctly initialized for shell scripts
    eval "$(conda shell.bash hook)" 
    conda activate kickbot
fi

# Set the PYTHONPATH to include the project root
export PYTHONPATH=$(pwd):$PYTHONPATH

# Run the tests using pytest, targeting the tests directory
echo "Running tests with pytest..."
python -m pytest tests/

# Exit with the same code as the test runner
exit $? 