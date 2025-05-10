# Use an official Python runtime as a parent image
# We'll use a base image that makes Conda installation easier, e.g., continuumio/miniconda3
# Or, we can install Miniconda manually on python:3.10-slim. Let's stick with python:3.10-slim and install manually for flexibility.
FROM python:3.11-slim

# Set environment variables for Conda
ENV CONDA_DIR /opt/conda
ENV PATH $CONDA_DIR/bin:$PATH
ENV CONDA_ENV_NAME kickbot

# Install Miniconda
RUN apt-get update --yes && \
    apt-get install --yes --no-install-recommends wget ca-certificates && \
    wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh && \
    /bin/bash ~/miniconda.sh -b -p $CONDA_DIR && \
    rm ~/miniconda.sh && \
    conda init bash && \
    conda config --set auto_activate_base false && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the Conda environment file
COPY environment.yml .

# Create the Conda environment from the environment.yml file
# This will also install pip packages listed in environment.yml
RUN conda env create -f environment.yml && \
    conda clean -afy

# Copy the rest of the application code into the container at /app
# This includes your bot scripts, configuration files, etc.
COPY . .

# Configure bash to automatically activate the Conda environment
# This ensures that when you 'docker exec -it ... bash', the environment is ready.
RUN echo "conda activate ${CONDA_ENV_NAME}" >> ~/.bashrc

# Keep the container running indefinitely without starting the bot.
# This allows you to manually enter the container's shell and run commands.
# Default shell is now bash, which will source .bashrc and activate the env.
CMD ["tail", "-f", "/dev/null"] 