FROM python:3.11-alpine

# No build deps needed — Flask + Werkzeug are pure Python
RUN pip install --no-cache-dir flask==3.0.3

WORKDIR /app

COPY app.py .
COPY templates/ templates/

# Pre-create /data mount point
RUN mkdir -p /data

# Run as non-root for security
RUN addgroup -S greenstack && adduser -S greenstack -G greenstack
RUN chown greenstack:greenstack /app /data
USER greenstack

# Init DB on first run, then serve
CMD ["sh", "-c", "python -c 'import app; app.init_db()' && python app.py"]

EXPOSE 5000
