# RAGFlow on the lab

[RAGFlow](https://github.com/infiniflow/ragflow) is a self-hosted retrieval engine. It reads documents (PDF, Word,
tables, scans), splits them by their layout, indexes them, and answers questions about them with a citation for
every answer. It runs on the lab at **https://ragflow.stbfarm.org**. [integration.md](integration.md) is the earlier
assessment (v0.21.1, 2026-05-14): what it is, what it costs to run, and what to use it for.

| File | What it does |
|---|---|
| `lab.sh` | Installs, upgrades, starts, stops or removes RAGFlow on the lab, from your machine |
| `install-nginx.sh` | Run once on the lab with sudo: publishes the site through the lab's nginx |
| `nginx/ragflow.stbfarm.org.conf` | The nginx site: HTTPS with the lab's origin certificate; only Cloudflare can connect |
| `integration.md` | The assessment |

## Run it

From your machine, in the repo (it reads `LAB` and `LAB_KEY` from `.secrets/lab.env`):

```sh
research/ragflow/lab.sh up       # the latest release; installs, or upgrades what is there, in the background
research/ragflow/lab.sh status   # version, containers, health
research/ragflow/lab.sh tunnel   # http://127.0.0.1:8088 on your machine, without the public site
research/ragflow/lab.sh down     # stop, keep the data
research/ragflow/lab.sh purge    # delete the data, the images and ~/ragflow (asks first)
```

Then, once, on the lab: `sudo sh ~/ragflow-lab/install-nginx.sh`. In Cloudflare: a proxied DNS record for
`ragflow.stbfarm.org` pointing at the lab, as for kestrel.stbfarm.org.

**Settings.**
- `RAGFLOW_VERSION=v1.0.0` pins a release. The default is the latest, looked up on GitHub each time `up` runs.
  `up` again with a newer release upgrades in place, and the data is kept.
- `RAGFLOW_WEB_PORT` changes the lab port (default 8088).
- `RAGFLOW_EMBED_MODEL` picks the embedding model.

## How it is set up

- **Where:** the release's own compose files, in `~/ragflow` on the lab, as the docker compose project `ragflow`.
  `lab.sh` changes only `docker/.env` and adds one override file, `docker/lab-override.yml`.
- **Ports:** one is published, the web UI on the lab's `127.0.0.1:8088`. RAGFlow's own nginx inside the container
  sends `/api/v1` to its API, so the API is at `https://ragflow.stbfarm.org/api/v1` with an API key made in the UI.
  MySQL, Elasticsearch, MinIO, Redis and the rest stay on the stack's own network. The override is built from the
  services the release defines, and `up` refuses to start if anything else would be published.
- **Logins:**
  - The admin is `admin@ragflow.io`.
  - Self sign-up is off, so the admin adds users.
  - The admin and database passwords are made on the first `up`. They are kept in `~/ragflow/lab-passwords.env` on
    the lab (mode 600), never in the repo: read the admin password there.
- **Embeddings:**
  - Releases since v0.22 no longer bundle embedding models, so the stack adds the CPU text-embeddings service.
  - It runs BAAI/bge-m3 (multilingual, about 21 GB of RAM).
  - `RAGFLOW_EMBED_MODEL=BAAI/bge-small-en-v1.5` needs 1.2 GB.
- **Chat model:** set one in the UI (Model providers). Two cases:
  - A hosted API works directly.
  - The lab's Ollama (`~/ollama`) listens on `127.0.0.1` only and was not running on 2026-11-22. A container cannot
    reach it there, so it would have to listen on the docker bridge, and RAGFlow's `ALLOW_ANY_HOST` would have to
    allow a private host.
  - Pick the provider type that matches the server: "Ollama" for Ollama, "OpenAI-API-Compatible" for an
    OpenAI-style server (the lesson in integration.md).
- **Resources:** about 8 GB of images. The lab disk was 97% full on 2026-11-22, with 33 GB free; `up` refuses below
  15 GB. Memory, at rest, is a few GB for the stack, plus the embedding model.
- **Public site:**
  - Cloudflare, then the lab's nginx (`nginx/ragflow.stbfarm.org.conf`), then 127.0.0.1:8088.
  - Only Cloudflare's addresses may connect.
  - Logins are limited to 10 a minute per visitor.
  - Uploads up to 512 MB, although Cloudflare's free plan stops at 100 MB.
  - Put Cloudflare Access in front if only the team should see the login page.
