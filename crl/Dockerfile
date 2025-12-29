FROM python:3.11-alpine

RUN apk add --update docker-cli openrc
COPY . /tmp/crl
RUN pip install /tmp/crl/
RUN rm -rf /tmp/crl
RUN mkdir -p /var/run/portd 
RUN mkdir -p /root/.docker/

ENTRYPOINT ["crl"]

