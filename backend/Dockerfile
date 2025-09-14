FROM python:3.13

WORKDIR /app

EXPOSE 8000

# Install Arelle (pinned)
RUN apt-get update -y && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/Arelle/Arelle.git /opt/arelle \
    && cd /opt/arelle \
    && git checkout 122eb892bdcdd7692921bf0ac39e228807a1c4f4

# Install Arelle runtime dependencies (regex, lxml, etc.)
# Prefer repo requirements if present; otherwise install key deps explicitly
RUN sh -lc "if [ -f /opt/arelle/requirements.txt ]; then \
      pip install --no-cache-dir -r /opt/arelle/requirements.txt; \
    else \
      pip install --no-cache-dir regex lxml isodate; \
    fi"

# Install PyPI API package (for Python API fallback)
RUN pip install --no-cache-dir arelle-release

ENV ARELLE_CACHE_DIR=/app/arelle_cache

CMD ["sh", "-c", "pip install --no-cache-dir -r requirements.txt && mkdir -p $ARELLE_CACHE_DIR && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]