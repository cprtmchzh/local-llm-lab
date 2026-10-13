FROM python:3.12-slim

WORKDIR /app
COPY server.py proxy.py /app/
USER 65532:65532
EXPOSE 8080
CMD ["python", "/app/server.py"]
