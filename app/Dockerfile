FROM python:3.12-slim

WORKDIR /app

RUN useradd --create-home --uid 1000 cpl \
    && mkdir -p /data \
    && chown cpl:cpl /data

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
RUN chown -R cpl:cpl /app

USER cpl
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8088
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8088"]
