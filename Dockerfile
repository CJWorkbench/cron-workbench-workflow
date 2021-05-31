FROM alpine:3.13.5

RUN apk add --no-cache python3 py3-pip

RUN python3 -mpip install --no-cache-dir httpx pg8000 tuspy

COPY app/ /app/app

WORKDIR /app

CMD [ "python3", "app" ]
