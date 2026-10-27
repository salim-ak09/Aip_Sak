# Dockerfile for aip_Sak Autonomous AI Pentest Platform
FROM python:3.12-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY src ./src
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

FROM python:3.12-slim AS runtime

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/aip_Sak /usr/local/bin/aip_Sak

# Security hardening: run as non-root
RUN useradd -m -u 1000 venice && \
    mkdir -p /home/venice/.venicept /app/engagements && \
    chown -R venice:venice /home/venice /app

USER venice
ENV PATH="/usr/local/bin:${PATH}"

ENTRYPOINT ["aip_Sak"]
CMD ["--help"]
