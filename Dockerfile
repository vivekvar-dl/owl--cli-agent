# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the entire project directory into the container at /app
COPY . /app/

# Install any needed packages specified in requirements.txt
# Use --no-cache-dir to keep the image size down
RUN pip install --no-cache-dir -r requirements.txt

# Set up the entrypoint to run the CLI
ENTRYPOINT ["python", "cli/cli.py"]

# The default command can be to show the help message
CMD ["--help"] 