FROM lscr.io/linuxserver/wireguard:latest

RUN apk update && apk add socat
ADD custom-entrypoint.sh /
RUN chmod +x /custom-entrypoint.sh

ENTRYPOINT ["/custom-entrypoint.sh"]
