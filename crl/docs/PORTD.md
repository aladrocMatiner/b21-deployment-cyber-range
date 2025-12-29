# Port Daemon (portd)

A simple restapi to find a "free" (ie not used) port on the host machine. 

The compose file is found here: `crl/services/portd.yml`

The rationalie for portd is that since crl and crld need access to overlay networks they cannot run with host network nampespace (ie to see what ports are used on the host).
Portd can run in host network namespace and by exporting a unix socket crl and crld can retrive a free port by querying a simple rest api, see `crl/helpers.py` function `find_free_port()`

