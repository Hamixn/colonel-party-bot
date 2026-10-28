FROM python:3.11-slim

RUN useradd -m -u 1000 user
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user:user . .

USER user
ENV PORT=7860
EXPOSE 7860

CMD ["python", "bot.py"]
