# Set base image (host OS)
FROM tensorflow/tensorflow:2.4.0-gpu

RUN apt update && \
    apt install --no-install-recommends -y build-essential software-properties-common && \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt install --no-install-recommends -y python3.8 python3-pip python3-setuptools python3-distutils && \
    apt clean && rm -rf /var/lib/apt/lists/*

# By default, listen on port 5000
EXPOSE 5000/tcp

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any dependencies
# Install any dependencies
RUN python3.8 -m pip install --upgrade pip && \
    python3.8 -m pip install --no-cache-dir -r requirements.txt

# Copy the content of the local src directory to the working directory
COPY app .

CMD alias python3=/usr/bin/python3.8

# Specify the command to run on container start
CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]
