FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common.py notify.py poll_command.py bot_daemon.py ./

CMD ["python", "bot_daemon.py"]
