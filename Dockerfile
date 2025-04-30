FROM python:3.11
ENV PYTHONUNBUFFERED=1

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
		fonts-noto-mono \
		&& rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV PATH="/app/.venv/bin:$PATH"

COPY . .
RUN uv sync --locked --no-dev

VOLUME /app/state

CMD ["picrew-bot"]
