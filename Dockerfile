FROM python:latest
WORKDIR /app
ADD . /var/app
RUN if [ -f /var/app/requirements.txt ]; then /var/app/bin/pip install -r /var/app/requirements.txt; fi 
CMD python3 main.py
