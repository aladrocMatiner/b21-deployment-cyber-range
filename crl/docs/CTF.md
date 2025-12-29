# Analysis of Capture The Flag challenges and frameworks
Capture The Flag (CTF) is a gamified way of learning cybersecurity.
The player need to solve a problem or exploit a system and find
a string which is both recognizable (flag{}) and hard to guess
(flag{c049r49rq09m48qc8urqcqpo4xh}). The flag is submitted on a
platform which rewards points and potentially tracks a scoreboard.

## Flag Terminology
**Flag Format**: The most common format for CTF flags is flag{...}. Some
organizers may choose a custom format (dice{...}, S2G{...}, HTB{...}). This
pattern can sometimes help the player solve the challenge (grep log,
substitution cipher).

**Flag Content**: Within the curly-brackets is usually a random hex-string
or a phrase in leet-speak. This makes it difficult for players to guess
the flag.

**Shared Flag**: Given a challenge in a CTF, the flag content is the same for
all participants. Players are discouraged from sharing flags but cheating is
possible.

**Individual Flag**: Given a challenge in a CTF, the flag content is unique per
player or team. This makes it impossible to share flags between participants
without getting detected.

## Challenge Terminology
**WhiteBox Service**: Player will get connection info (IP/Domain/URL/Port) and
often the Dockerfile and source files running on the server (with a fake flag).

**BlackBox Service**: Player may need to find the machine, enumerate services,
discover a vulnerability, and exploit said vulnerability. No server files are
supplied. 

**WhiteBox Binary**: Player will get both a binary (with the real flag) and the
source code (with a fake flag).

**BlackBox Binary**: Player will only get a binary which contains the flag
(Reverse Engineering).

**Downloadable**: Player will download a file: packet capture, cipher, image,
custom metadata. It may contain a hidden flag or reference to another location
(OSINT).

## Jeopardy
A collection of challenges solved by teams or individuals within a limited
timeframe. While some are docker/VM services, a substantial amount only
consists of text or downloadable files. The challenges can often be solved in
any order without dependencies. The services are often hosted on public
addresses and shared between all teams/players.  It is therefore rare to see a
BlackBox Service / Pwn + Privilege Escalation challenge.  Brute force and nmap
scans are usually forbidden.

The challenges are categorized:
- Web (cookies, SQLi, logins, hidden pages)
- Crypto (RNG, weak keys, ciphers)
- Forensics (pcap, logs, metadata)
- Pwn (vulnerability exploit, privilege escalation)
- Reverse Engineering (deconstructing binaries, gdb, ghidra, radare2)
- OSINT (social media platforms, reverse image search, social networks)
- Misc

The scoring of the challenges are usually dynamic (the value decrease as more
players solve it). New players can then identify low-hanging fruit and veteran
players know where to focus their effort to climb the leaderboard.  There two
additional benefits with dynamic scoring; teams are less likely to share flags
with eachother, and there is no need to assign a difficulty to the challenge.

## Cyber Range
A collection of vulnerable machines in a virtual network, allowing players to
practive penetration testing methodologies: reconnaissance, enummeration,
exploitation, post-exploitation, privilege escalation, persistence, pivoting.
BlackBox Service challenges are the best fit for cyber ranges in combination
with Downloadable challenges which can be found in the post-exploitation step.
The ranges are usually only accessible through a VPN connection.

## HackTheBox
A platform serving single BlackBox Service challenges and tracking player
score. HackTheBox design their challenges with two flags; one obtainable by a
low privilege user in the post-exploitation step (/home/user/flag.txt), and one
only accessible after the privilege escalation step by the root user
(/root/flag.txt). Since the platform is running 24/7, the containers are
spawned manually by the players by clicking a button.  A few seconds later a
private IP and port is shown, only accessible through a VPN tunnel (the config
can be generated on demand).

## CERT-SE
The Computer Security Incident Response Team (CSIRT) of Sweden is organizing
a CTF every year. The category for the whole CTF is Forensics and consists
of a pcap containing multiple flags which are handed in via email.

## Tool With Many Names (TWMN)
The cyber range at KTH mainly consists of BlackBox Service challenges in a
virtual network accessible via VPN. Flags are placed at checkpoints throughout
the range. The infrastructure consist of images from ansible files running on
Google Cloud Platform (GCP) and managed by the TWMN script. The flags are
randomly generated when the machines are restored; either automatically every
24h or manually by supervisors. The players share instances of the range in
groups of 10, which opens up challenges in regards to cheating and collateral
damage.  KAU has added CTFd in the frontend, and set up an issue board for
reporting broken machines.

Comparing TWMN with Jeopardy, we see that the player is allowed to use brute
force. In addition there are dependencies between challenges in TWMN. 
Here we see that TWMN includes more Jeopardy categories than just Web and Pwn
in a clever way.

## S2G (NTNU CBCC)
The System Security Group (S2G) at NTNU organize bi-weekly Jeopardy CTFs,
having a large collection (500+) challenges in varied categories.
The system is automated using a standardized format for challenges, CTFd
as the frontend, and OpenStack for running docker containers and VMs.
Unsolved challenges are reused in addition to a steady flow of new ones.

The default static flags are set when building the challenge which creates some
problems. Previous writeups from players may contain the real flag, making the
challenge unlikely to be reused since the flag can be found without solving it.
It is also awkward to share challenges if a different flag format is used.
Finally, if a CTF needs unique flags for each player, a new image needs to be
built for each one. 

Most of the docker-based challenges from S2G are WhiteBox services. 
Removing the player's access to the Dockerfile and source files could
drastically increase the difficulty and may render some challenges impossible.
Such challenges might be unfit for a cyber range.

## Cyber Range Light (CRL)
An initiative at KAU based on the experiences from running TWMN and with
support from CBCC to collaborate with S2G.
CRL focuses on automating CTF infrastructure using docker and CTFd:
- Jeopardy Public Shared Flags (Traditional)
- Jeopardy VPN Shared Flags (S2G)
- Jeopardy VPN Individual Flags
- Cyber Range VPN Shared Flags (TWMN)
- Cyber Range VPN Individual Flags

In order to reuse container images in docker swarm when using individual
flags, the flag must be set in run-time and not when building the image.
In order to support all categories of Jeopardy CTFs, CRL must be able to
manage non-service challenges as well (upload necessary content to CTFd).

### Components/Pipeline
**Challenge**:
- README.md: 
    - Description
    - Build guide
    - Writeup
- meta.yml (S2G meta.xml):
    - CTFd content:
        - Name
        - Description
        - Downloadable files
        - Connection info
        - Default real flag 
    - metadata:
        - Author
        - History
- building files:
    - Dockerfile w/ fake flag
    - Source files
- player files:
    - Dockerfile w/ fake flag (if WhiteBox Service)
    - Source files (if WhiteBox Service)
    - Binaries, Images, etc.

**Blueprint**: A collection of challenge (meta.yml) picked by the organizer
(similar to the S2G event file). May have static flags (Shared) or placeholders
(Individual).  It is an yml file very similar to a docker-compose file but including custom tags with CTFd challenge data. 

**World**: An instance of a blueprint with flags (and VPN credentials) set. 

**Event**: Blueprint + CTFd instance. In addition to the challenge info in the blueprint,
CTFd metadata is also included e.g., URL (https://{event}.crl.kau.se) and admin token
(for creating challenges and managing flags).

**CTFd**: Automatically spawned on a public address 
(https://{event}.crl.kau.se) using DNS wildcards.
Challenge content is posted via the REST API when the first world is created.
Flags managed via the REST API when a world is created/deleted.
For Jeopardy CTFs, chall.crl.kau.se:{port} could be used for services.

### Use cases
Leo could set up a blueprint called "DVAD25" with a collection of challenges.
It will be a Cyber Range + VPN + Individual Flags.
Leo also creates an event called "DVAD25-VT25" which pairs the "DVAD25" blueprint
with a CTFd instance.

Alice wants to play DVAD25-VT25: 
- a world is created with unique flags
- a wireguard config is created and sent to Alice
- a CTFd instance is spawned (https://dvad25-vt25.crl.kau.se)
- challenge content are posted to CTFd
- Alice's flags are posted to CTFd
- Alice's world is accessible to Alice via VPN

Bob wants to play DVAD25-VT25: 
- a world is created with unique flags
- a wireguard config is created and sent to Bob
- a CTFd instance already exists for DVAD25-VT25
- Bob's flags are posted to CTFd
- Bob's world is accessible to Bob via VPN

Jonathan could set up a blueprint called ArcnilyaCTF with a collection of
challenges. It will be a Jeopardy + Public + Shared Flags.
Jonathan creates an event with the same name, including CTFd metadata.

Jonathan launches the event:
- a world is created with default flags
- a CTFd instance is spawned (https://arcnilyactf.crl.kau.se)
- challenge content (with connection info) are posted to CTFd
- default flags are posted to CTFd
- world is accessible to everyone on chall.crl.kau.se:{port}

