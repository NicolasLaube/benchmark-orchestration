FROM python:3.12-slim

WORKDIR /app

RUN pip install fastapi uvicorn

COPY app.py ./app.py

CMD [ "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000" ]