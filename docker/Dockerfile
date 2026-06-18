FROM python:3.12-slim

LABEL org.opencontainers.image.title="Apple MCP Server"
LABEL org.opencontainers.image.description="Enterprise MCP server for Apple iCloud: Calendar, Reminders, Mail"
LABEL org.opencontainers.image.source="https://github.com/thetaroot/apple-mcp"

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY dist/ /tmp/dist/
RUN if [ -n "$(ls /tmp/dist/*.whl 2>/dev/null)" ]; then \
        pip install --no-cache-dir /tmp/dist/apple_mcp*.whl; \
    else \
        pip install --no-cache-dir .; \
    fi && rm -rf /tmp/dist

RUN mkdir -p /data/pyicloud && chown nobody:nogroup /data/pyicloud

USER nobody

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

EXPOSE 8080

ENTRYPOINT ["python", "-m", "apple_mcp"]
CMD ["--transport", "http"]
