FROM python:latest
WORKDIR /
ADD . /app
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi 
CMD python3 app/main.py
