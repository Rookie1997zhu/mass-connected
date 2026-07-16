FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc default-libmysqlclient-dev pkg-config \
    libgl1 libglib2.0-0 libx11-6 \
    libreoffice-writer libreoffice-calc \
    fonts-wqy-zenhei fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# OCR（阶段 B/C）：单独分层，保留上方 OCC/VTK 重层缓存，避免每次重复下载大依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-kor tesseract-ocr-chi-sim \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --timeout 300 --retries 10 pytesseract pymupdf

COPY . .

RUN mkdir -p /app/media

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
