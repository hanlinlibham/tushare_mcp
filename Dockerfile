FROM python:3.12-slim

WORKDIR /app

# System libs occasionally pulled in by pandas/numpy wheels — keep minimal
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential

COPY findatamcp ./findatamcp
COPY static ./static
COPY .env.example ./

ENV PYTHONUNBUFFERED=1 \
    MCP_SERVER_HOST=0.0.0.0 \
    MCP_SERVER_PORT=8006 \
    FINDATA_DATA_DIR=/data

VOLUME ["/data"]
EXPOSE 8006

# Default transport: Streamable HTTP. For SSE replace with `findatamcp.server_sse`.
CMD ["python", "-m", "findatamcp.server"]
