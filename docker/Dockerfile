FROM python:3.12-slim

LABEL org.opencontainers.image.title="Apple MCP Server"
LABEL org.opencontainers.image.description="Enterprise MCP server for Apple iCloud: Calendar, Reminders, Mail"
LABEL org.opencontainers.image.source="https://github.com/thetaroot/apple-mcp"

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

USER nobody

HEALTHCHECK --interval=60s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import apple_mcp; print(apple_mcp.__version__.VERSION)" || exit 1

EXPOSE 8080

ENTRYPOINT ["python", "-m", "apple_mcp"]
CMD ["--transport", "http"]
