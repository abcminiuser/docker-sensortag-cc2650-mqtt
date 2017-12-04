# Pull base image
FROM alpine:edge

# Install dependencies
RUN apk add --no-cache bash
RUN apk add --no-cache python3 python3-dev bluez-deprecated

RUN pip3 install pexpect
RUN pip3 install pygatt
RUN pip3 install paho-mqtt

COPY sensortag.py /

CMD ["./sensortag.py"]
