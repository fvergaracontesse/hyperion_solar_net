# Set base image (host OS)
FROM python:3.8-slim-buster

# By default, listen on port 5000
EXPOSE 5000/tcp

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

RUN apt-get update

# Install any dependencies
RUN pip install -r requirements.txt

# Copy the content of the local src directory to the working directory
COPY app .

# Specify the command to run on container start
CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]
