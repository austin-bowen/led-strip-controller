FROM python:3

# Install updates
RUN apt-get update && apt-get upgrade -y && apt-get clean
RUN pip install --upgrade pip

WORKDIR /usr/src/app

# Install project dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy in files
COPY src src

WORKDIR src/python

ENTRYPOINT ["python", "led_strip_controller.py", "/dev/ttyACM0"]
CMD ["sysload"]
