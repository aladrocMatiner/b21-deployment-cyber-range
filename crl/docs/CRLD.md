# Cyber Range Lite Daemon (crld)
Is a rest api for crl and is mostly used with the [ctfd crl plugin](https://git.cs.kau.se/csma/cyber-range/ctfd-plugins/-/tree/main/crl)

### crld (debugging) 
**Attention**: Most common usage (and what is configured with crl init --use-crld) is for usage with the ctfd crld plugin and then crld is not rechable from the host)
Endpoints:
  - POST /EVENT/create/USER ; creates and starts the world - returns config 
  - POST /EVENT/reset/USER  ; stops and recreates world - returns status
  - GET /EVENT/config/USER  ; returns config
  - GET /EVENT/status/USER  ; returns status
  - GET /EVENT/wireguard/USER/config  ; Get wireguard user configuration. Same as /EVENT/config/USER
  - GET /EVENT/wireguard/USER/network ; Get wireguard IPs.

`curl -iX POST http://localhost:5000/poc/create/ada`
