# Terminology 
- **flag**, the string that is posted to CTFd to identify if a user has solved the challenge. 
- **challenge**, the entity that provides one flag, defines zero to many services (1 ctfd challenge = 1 crl challenge).
  - **challenge** | **exercise** | **task** | **single-challenge**
- **multi-challenge**, a collection of (single-)challenges 
  - **challenge** | **machine** (hack-the-box) | **multi flag challenges**
- **service**, in a challenge docker services are used.
  - **service** | **container** | **server** | **node** | **machine**
- **user**, the entity that logs in to CTFd and compete.
  - **user** | **hacker** | **player**
- **world**, the place where players play, runs services (docker stack). an instance of a blueprint.
  - **world** | **network** | **site** | **corporation** | **playground**
- **event**, specific named competention, specifies which blueprint and configuration options to use (ctfd, crld, traefik)
  - **event** | **course**
- **stored-event**, a copy of event configuration to be able to reuse the same settings for multiple events. 
- **blueprint**, defines a 1 or more challenges and or multi-challenges and how the challanges are connected (ie network).
  - **template** | **blueprint**
- **image**, a docker image stored on a private or public registry.

## Common sentences:
- A jeopardy style **event** consists of many **users** connecting to one **world** to capture many **flags** spread out over many **services**.
- In a cyber-range style **event** each **user** get their own isolated **world** that is accessible via VPN.  
- One **challenge** have one **flag** per **world**.
- Can you reset my **world**?
- I logged into my **world** and scanned for available **servers**.


