FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_DATA_DIR=/var/data \
    HF_HOME=/var/data/huggingface

WORKDIR /app

COPY requirements.txt .
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu "torch>=2.2.0,<3" \
    && pip install --no-cache-dir -r requirements.txt

COPY *.py ./
COPY .streamlit/config.toml .streamlit/config.toml
RUN mkdir -p /var/data/item_photos /var/data/huggingface

EXPOSE 8501

CMD ["sh", "-c", "streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT:-8501} --server.headless=true"]
