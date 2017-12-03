# Pull base image
FROM debian:stretch

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-dev \
    python3-pip \
    python3-virtualenv \
    python3-wheel \
    bluez \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install setuptools
RUN pip3 install pexpect
RUN pip3 install pygatt
RUN pip3 install paho-mqtt

COPY sensortag.py /

CMD ["./sensortag.py"]
