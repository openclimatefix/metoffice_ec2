# Use the official image as a parent image.
FROM continuumio/miniconda3

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
SHELL ["conda", "run", "-n", "metoffice_ec2", "/bin/bash", "-c"]

# Copy the rest of your app's source code from your host to your image filesystem.
COPY . .

# Install metoffice_ec2 Python library within Conda environment.
RUN pip install -e .

# Run the specified command within the container.
CMD [ "conda", "run", "-n", "metoffice_ec2", "python", "scripts/ec2.py" ]
