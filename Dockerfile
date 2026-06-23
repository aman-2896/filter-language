# Start from an official slim Python image matching the project's version.
# "slim" is a smaller base (less to download, smaller final image) while still
# having what a normal Python app needs.
FROM python:3.12-slim

# Two settings recommended for Python in containers:
#  - PYTHONUNBUFFERED: print/log output appears immediately, not buffered,
#    so you see logs in real time when the container runs.
#  - PYTHONDONTWRITEBYTECODE: don't write .pyc files inside the container (noise).
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# All following commands run inside this directory in the image.
WORKDIR /app

# Copy ONLY requirements first, then install. This is a deliberate ordering:
# Docker caches each step, so as long as requirements.txt doesn't change, it
# reuses the cached install layer even when your source code changes — faster
# rebuilds. Installing before copying the code is a standard optimization.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the project into the image.
COPY . .

# Document that the app listens on port 8000 (informational).
EXPOSE 8000

# On container start: apply migrations (build the DB schema), seed the sample
# data (your management command), then run the server bound to 0.0.0.0 so it's
# reachable from outside the container. The "&&" runs each only if the prior
# step succeeded.
CMD python manage.py migrate && \
    python manage.py seed && \
    python manage.py runserver 0.0.0.0:8000