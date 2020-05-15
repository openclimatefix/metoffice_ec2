# Use the official image as a parent image.
FROM continuumio/miniconda3

# Set the working directory.
WORKDIR /usr/src/app

# Copy the file from your host to your current location.
COPY environment.yml .

# Create the Conda environment inside your image filesystem.
RUN conda env create -f environment.yml
RUN conda activate metoffice_ec2

# Copy the rest of your app's source code from your host to your image filesystem.
COPY . .

# Install metoffice_ec2 Python library within Conda environment.
RUN pip install -e .

# Run the specified command within the container.
CMD [ "python", "scipts/ec2.py" ]
