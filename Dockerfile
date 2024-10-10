FROM python:3.11
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY . .
RUN pip install .

VOLUME /app/state

CMD ["picrew-bot"]
