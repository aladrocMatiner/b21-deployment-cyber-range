#!/bin/sh
for p in ${PROXYPORTS}
do
    socat UDP4-LISTEN:$p,fork UDP4:${PROXYHOST}:$p &
    socat TCP4-LISTEN:$p,fork TCP4:${PROXYHOST}:$p &
done

if [ "$DISABLE_PEERDNS" = "true" ]
then
    sed -i '/DNS = ${PEERDNS}/d' /defaults/peer.conf
    apk del coredns
    export USE_COREDNS="false" 
fi


exec /init