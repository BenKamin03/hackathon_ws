# Use a lightweight Python image
FROM python:3.12-slim

# Expose the application port
EXPOSE 8000

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Copy the requirements file first for caching purposes
COPY requirements.txt .

# Install dependencies
RUN python -m pip install --upgrade pip
RUN python -m pip install gunicorn uvicorn fastapi fastapi[standard]
RUN python -m pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Command to run your FastAPI application with gunicorn
CMD ["fastapi", "run", "main.py", "--port", "8000"]