# ---- Base image ----
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy and install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Expose port 8000
EXPOSE 8000

# Start the server (reload=False for production)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
