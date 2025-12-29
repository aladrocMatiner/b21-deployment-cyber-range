# Tutorial: Generate a CRL Event (Codex Challenges)

This guide walks you through generating a new CRL event using the Codex challenges we prepared. It is clear, step by step, and beginner-friendly.

## What This Creates
- A new **CTFd instance** for the event
- A set of **Codex challenges** loaded into CTFd
- A **world** (containers) for the admin user

## Prerequisites
- Docker running
- Swarm initialized (`docker swarm init`)
- Logged in to a Docker registry (so `~/.docker/config.json` exists)

## Step 1: Go to the CRL folder

```bash
cd /home/aladroc/src-local/__aladrocMatiner/b21-deployment-cyber-range/crl
```

## Step 2: Create the event

We use the stored event file generated for the Codex mix.

```bash
CRL_IMAGE=crl ./crlcli create --event stored-events/generated/mix-10.yml codexgen admin
```

Expected output includes a CTFd URL like:
```
External CTF for event is : http://127.0.0.1:57737
```

## Step 3: Start the world (containers)

```bash
CRL_IMAGE=crl ./crlcli start codexgen admin
```

This spins up the services for the admin world.

## Step 4: Open CTFd

Open the URL printed in Step 2. For example:

```
http://127.0.0.1:57737
```

Login:
- Username: `admin`
- Password: `password123`

## Step 5: Verify challenges

You should see the Codex mix challenges (web, attachment, multi-service). If they appear, the event is ready.

## Optional: Stop or delete later

Stop world:
```bash
CRL_IMAGE=crl ./crlcli stop codexgen admin
```

Delete world and event data:
```bash
CRL_IMAGE=crl ./crlcli delete codexgen admin
```

Note: In case delete fails due to missing CTFd metadata, you can remove the stack manually:
```bash
docker stack rm crl-codexgen
rm -rf Events/codexgen
```

---

You now have a clean, repeatable process to spin up Codex challenges. Nice work.
