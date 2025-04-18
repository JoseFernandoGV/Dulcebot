FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1
ENV LANG C.UTF-8

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential libpq-dev postgresql-client && rm -rf /var/lib/apt/lists/*

COPY . /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["sh", "-c", "python vectorizar.py && chainlit run dulcebot.py -h 0.0.0.0 -p 8000"]
