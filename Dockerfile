FROM python:latest
WORKDIR /
ADD /app .
COPY requirements.txt .
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi 
CMD python3 main.py
