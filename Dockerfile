FROM alpine:3.10.1

RUN true \
      && apk add python3 \
      && rm -rf /var/cache/apk/* \
      && pip3 install pg8000 boto3 requests \
      && rm -rf /root/.cache/pip

COPY app/ /app/app

WORKDIR /app

CMD [ "python3", "app" ]
