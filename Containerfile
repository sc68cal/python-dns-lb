FROM python:3

COPY server.py /app/
COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt

CMD python /app/server.py
