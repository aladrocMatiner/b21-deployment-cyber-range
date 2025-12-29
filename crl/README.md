# Cyber Range Lite (crl)

The aim of this project is to automate a complete setup of a Capture The Flag (CTF) event by using only docker stack (compose), CTFd and some configuration files. 

More documentation found in docs/ folder.

Since crl modifies files in the current execution folder (`./Events`) and possibly in `~/.docker/` as the root user 
it is recommended to use the common root user to run crl commands.

## Quick setup
All the steps are done as the root user so you need either to be able to login as root or become root (eg. sudo su) on your server.

Minimal steps to install (tested on Ubuntu 22.04 and debian bookworm):  
1. Install docker.
    ```bash
    curl -sSL https://get.docker.com/ | sh
    ```
2. Initialize docker swarm.
   ```bash
   docker swarm init
   ```
3. Clone repository in the directory where you intend to run crl:
   ```bash
   git clone https://git.cs.kau.se/csma/cyber-range/crl.git 
   cd crl
   ```
4. Clone example challenges repository.
   ```bash
   git clone https://git.cs.kau.se/csma/cyber-range/public-challenges.git challenges/
   ```
5. Login to a docker repo once to create file ~/.docker/config.json
   ```bash 
   docker login # or to a private repo eg. docker login docker.cs.kau.se
   ```
6. Initialize CRL, only needs to be run once.
   ```bash
   ./crlcli init --use-crld      
   ```
   Output:
   ```bash 
   Creating network crl_default
   Creating service crl_crld
   Creating service crl_portd
   ```
   
Note) login in to all private docker registries (i.e. where private challenges are stored) before continuing eg. `docker login docker.cs.kau.se`

## Workflow

### Create a new event 

Create a new event named testevent using example event configuration, blueprint and a default admin world.
  
```bash
./crlcli create --event stored-events/examples/template.yml testevent admin
```
Output:
```bash
Creating service crl-testevent_ctfd
Waiting for http://testevent-ctfd:8000 to be available
Done, http://testevent-ctfd:8000 took 4 seconds to connect
External CTF for event is : http://127.0.0.1:50781
- admin
[POST CHALLENGE]: Challenge my-first-challenge posted.
[POST HINT]: Hint (#1) for my-first-challenge posted.
[POST HINT]: Hint (#2) for my-first-challenge posted.
[POST HINT]: Hint (#3) for my-first-challenge posted.
[POST HINT]: Hint (#4) for my-first-challenge posted.
[POST CHALLENGE]: Challenge Combined-challenge SSH posted.
[POST CHALLENGE]: Challenge Combined-challenge HTTP posted.
[POST CHALLENGE]: Challenge Single-challenge with multiple services/servers posted.
[POST CHALLENGE]: Challenge Attachment only challenge posted.
```

### CTFd

Visit http://127.0.0.1:50781 (exact url and port is shown in the output of `External CTF for event is :`) and login with `admin` password: `password123`

### Start admin world.
```bash
./crlcli start testevent admin
```
Output:
```bash
Will start these worlds in testevent: admin
Creating network crl-testevent-admin_internal
Creating network crl-testevent-admin_single-challenge-multi-service_internal
Creating network crl-testevent-admin_public
Creating network crl-testevent-admin_single-challenge_internal
Creating service crl-testevent-admin_single-challenge_local-dummy-server
Creating service crl-testevent-admin_multi-challenge
Creating service crl-testevent-admin_single-challenge-multi-service_backend
Creating service crl-testevent-admin_single-challenge-multi-service_frontend
Creating service crl-testevent-admin_wireguard
Creating service crl-testevent-admin_single-challenge_server
```

### List all flags for a user 
```bash
./crlcli list testevent admin
```
Output:

UP | NAME                                                               | NET                                                                | PORTS               | FLAGS
-- | :----------------------------------------------------------------- | :----------------------------------------------------------------- | :------------------ | :------------------------------------------------------------------------------
 ✓ | wireguard(wo462fn8ahm2gzlpiin8gb4ec)                               | public(10.0.5.5) VIP: public(10.0.5.4)                             | ['50327:51820/udp'] | []
 ✓ | single-challenge_server(7sm9yshc03ibzzhyspflbeeo9)                 | public(10.0.5.6),single-challenge_internal(10.0.6.4)               |                     | ['flag{admin-m8LEDl27Cks2uDHOdKfkpTb3Oq0DFpAUIPj2IqmnWRTXz29GYHvd}']
 ✓ | single-challenge_local-dummy-server(cgofloa2j0uo2nfc2yhige3t5)     | single-challenge_internal(10.0.6.2)                                |                     | []
 ✓ | multi-challenge(smtdfdrmt4x68ua142gi2ctnt)                         | internal(10.0.3.2)                                                 |                     | ['flag{admin-lWE0T4NjOjpG1Hyc8PX6YiOo0m3Brb7pGKjxcy3EQhhOuL14oZNQ}', 'apabepa']
 ✓ | single-challenge-multi-service_backend(vqzf49ic8sek3xp1h7zs6cqsc)  | single-challenge-multi-service_internal(10.0.4.2)                  |                     | ['flag{admin-igiaBopIgtpdUfBTUQcqLnXhaEEdTXEM1j43UJl7HC2uMYqFlRys}']
 ✓ | single-challenge-multi-service_frontend(usk3pb2d7p0g5fck7cqbg85jc) | public(10.0.5.2),single-challenge-multi-service_internal(10.0.4.4) |                     | []

### Delete a world
```bash
./crlcli delete testevent admin
```

## Development
To ensure that you only run your local changes you need to set a non default image for crl to use (`export CRL_IMAGE="crl"`). 
After setting the `CRL_IMAGE`/`WG_IMAGE` environment variable; `docker compose build` will build your local `CRL_IMAGE`/`WG_IMAGE` images and, crlcli etc. will use your locally built image (ie it will not work in production on a multi node setup).

The images that can be configured are:
- `export CRL_IMAGE="crl"` 
- `export WG_IMAGE="wireguard"`
- `export CTFD_IMAGE="ctfd"` --- image needs to exist (ie built needs to be built and configured externally 
- `export TRAEFIK_IMAGE="traefik"` --- very uncommon to change

Do note that `docker compose build` will not build `CTFD_IMAGE`/`TRAEFIK_IMAGE` images so these needs to be built/exist a priori. 
While possible to (mis)use the environment variables CRL_IMAGE and WG_IMAGE to point to your own registry, the recommendation if you permanently want to use your own registry is to change the default setting (`docker.cs.kau.se/csma/cyber-range/crl`) for `image` and `CRL_IMAGE` in `docker-compose.yml` and corresponding for `WG_IMAGE`, `CTFD_IMAGE` etc.  

## License
All code is released under GNU GENERAL PUBLIC LICENSE Version 3 (GPL3) 
