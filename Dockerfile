FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install --no-cache-dir .

WORKDIR /fonts
ENTRYPOINT ["font-splitter"]
