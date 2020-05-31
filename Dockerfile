# Use the official image as a parent image.
FROM continuumio/miniconda3

# Make logs show up immediately, not only after loop finishes
ENV PYTHONUNBUFFERED 1
ENV SENTRY_ENV production
ENV RELEASE_VERSION 1.2.0

# Set the working directory.
WORKDIR /usr/src/app

# Update Conda.
RUN conda update -n base -c defaults conda

# Copy the file from your host to your current location.
COPY environment.yml .

# Create the Conda environment inside your image filesystem.
RUN conda env create -f environment.yml

# Make RUN commands use the new environment:
# From https://pythonspeed.com/articles/activate-conda-dockerfile/
# SHELL ["conda", "run", "-n", "metoffice_ec2", "/bin/bash", "-c"]

# Make sure python uses the right venv
ENV PATH /opt/conda/envs/metoffice_ec2/bin:$PATH

# Copy the rest of your app's source code from your host to your image filesystem.
COPY . .

# Install metoffice_ec2 Python library within Conda environment.
RUN pip install -e .

# Run the specified command within the container.
CMD [ "python", "-u", "scripts/ec2.py" ]
