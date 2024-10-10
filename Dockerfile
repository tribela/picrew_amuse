FROM python:3.11
ENV PYTHONUNBUFFERED=1

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
		fonts-noto-mono \
		&& rm -rf /var/lib/apt/lists/*
COPY . .
RUN pip install .

VOLUME /app/state

CMD ["picrew-bot"]
