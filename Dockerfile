FROM python:latest
RUN apt-get update -y
RUN apt-get install -y python3-pip
WORKDIR /
RUN pip install -r requirements.txt
CMD python3 app/main.py
