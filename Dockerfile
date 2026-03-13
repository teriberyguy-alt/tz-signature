FROM python:3.12-slim

# Install Tesseract OCR (required by pytesseract)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app code
COPY . .

# Expose the port Render expects
EXPOSE 5000

# Run the app
CMD ["python", "app.py"]
