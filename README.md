# RAGFlow and coding models on the lab

Two self-hosted AI services for the lab, each installed, upgraded and deployed from this repo, with CI on GitHub and
continuous deployment on the lab itself. Which ones run is set in [`deploy/services`](deploy/services):

| Service | Status | Address | What it is |
|---|---|---|---|
| **RAGFlow** | **disabled** since 2026-11-23 (torn down, no data kept) | https://ragflow.stbfarm.org | [RAGFlow](https://github.com/infiniflow/ragflow), a retrieval engine: it reads documents (PDF, Word, tables, scans), indexes them by their layout, and answers questions about them with a citation for every answer. Web UI, HTTP API, an OpenAI-compatible chat API and an MCP endpoint. |
| **Coding models** | running | https://coder.stbfarm.org/v1 | Qwen3.8 27B by default, and an uncensored (abliterated) copy, on the lab's RTX 4090, behind per-person API keys. For opencode, VS Code agents, Claude Code and any OpenAI client: [coder/README.md](coder/README.md). |

[integration.md](integration.md) is the assessment of RAGFlow: what it is, what it costs to run, and when it is
worth it.

| File | What it does |
|---|---|
| `lab.sh` | Runs on your machine: every command below, sent to the lab over ssh |
| `ragflow.sh` | Runs on the lab: installs or upgrades RAGFlow, starts, stops, checks |
| `coder/coder.sh` | Runs on the lab: the coding models (Ollama on the 4090) and their API keys |
| `deploy/cd.sh` | Continuous deployment, run on the lab every 5 minutes by `deploy/ragflow-cd.timer` |
| `deploy/services` | Which services CD deploys and `install.sh` publishes: one name per line, comment one out to disable it |
| `deploy/install.sh` | Once on the lab with sudo: the CD timer and the enabled services' nginx sites (`deploy/install-nginx.sh`) |
| `nginx/`, `coder/nginx/` | The two nginx sites: HTTPS with the lab's origin certificate; only Cloudflare can connect |
| `.github/workflows/ci.yml` | CI: shellcheck, `nginx -t` on both sites, and dry runs of both setups |
| `integration.md` | The RAGFlow assessment, and lessons from a first trial |

## Run it

From your machine, in this repo. It reads `LAB` (user@host) and `LAB_KEY` (the key file, relative to this
folder) from `.secrets/lab.env`, which git ignores: copy it from poker-analysis's `.secrets/lab.env`.

```sh
./lab.sh status          # RAGFlow: version, containers, health, the last start-up and CD lines
./lab.sh coder status    # coding models: GPU, loaded model, API health, who has a key
./lab.sh deploy          # run the CD step now instead of waiting for the timer
./lab.sh coder key add NAME   # an API key for the coding models (then the sudo install below)
./lab.sh tunnel          # both services on your machine, without the public sites:
                         #   http://127.0.0.1:8088 (RAGFlow) and http://127.0.0.1:11435/v1 (coding models)
./lab.sh up | down | purge          # RAGFlow by hand (purge asks first)
./lab.sh coder up | down | purge    # the coding models by hand
```

## CI/CD

A push to `main` deploys itself, and so does a new RAGFlow release while RAGFlow is enabled. Each deploy brings up
the services listed in `deploy/services`: RAGFlow first, then the coding models.

**Turning a service off or on:**
- **Off:** comment it out in `deploy/services` and push. Then remove it from the lab (`./lab.sh purge`, or
  `./lab.sh coder purge`), and run `sudo sh ~/ragflow-lab/deploy/install.sh` to take its site down. CD logs a
  reminder while a disabled service's site is still published.
- **On:** uncomment it and push. CD installs it, then run the same sudo install to publish its site.
- RAGFlow was turned off this way on 2026-11-23. It held two accounts and no datasets or documents.

- **CI**, on GitHub Actions, runs on every push and pull request, and every Monday. It catches a RAGFlow release that
  breaks our settings before the lab tries it. It runs:
  - shellcheck on every script;
  - `nginx -t` on both sites, with a throwaway certificate and full-length test keys;
  - `ragflow.sh check`: fetches RAGFlow's latest release, applies our settings and port override, and validates
    them, without starting anything;
  - `coder/coder.sh check`.
- **CD** runs on the lab, which pulls; nothing on GitHub can reach the lab, and no lab address or key is stored
  there. Every 5 minutes `deploy/cd.sh`:
  1. fetches `main` (the repo is public, so no key or token is needed);
  2. reads RAGFlow's latest release;
  3. if either changed, or the coding models are not running, updates the checkout `~/ragflow-lab` and lints the
     scripts;
  4. runs `ragflow.sh up --wait`, which validates settings and ports before starting anything and waits for the
     health check;
  5. runs `coder/coder.sh up --wait`, which waits until the default model is loaded fully on the GPU.
- **Updates to `cd.sh` itself:** CD runs from a copy of itself. When an update changes `deploy/cd.sh`, the new
  version takes over and deploys.
- **A failed deploy** is logged and not retried until the commit or the release changes; `./lab.sh deploy` forces
  one. Validation happens before anything starts, so a bad setting leaves the running services as they were.
- **nginx** needs root, so CD does not change it. The log says to re-run `sudo sh ~/ragflow-lab/deploy/install.sh`
  when:
  - a site's config in the repo differs from the installed one;
  - a site is not published yet;
  - the coder API keys are newer than nginx's copy.

  If `nginx -t` fails during the install, every site is put back as it was.
- **Logs:** `~/ragflow/lab/cd.log` (its last lines are in `./lab.sh status`), and `journalctl -u ragflow-cd` on the
  lab.

**Set it up once:**
1. `./lab.sh setup` from your machine. It clones the repo to `~/ragflow-lab` on the lab.
2. `sudo sh ~/ragflow-lab/deploy/install.sh` on the lab. It installs the timer, which runs as you, not root, and the
   nginx sites. In Cloudflare, `ragflow.stbfarm.org` and `coder.stbfarm.org` are proxied DNS records pointing at the
   lab, as for kestrel.stbfarm.org.

**RAGFlow settings.**
- `RAGFLOW_VERSION=v1.0.0` pins a release. The default is the latest, looked up on GitHub each time `up` runs.
  `up` again with a newer release upgrades in place, and the data is kept.
- `RAGFLOW_WEB_PORT` changes the lab port (default 8088).
- `RAGFLOW_EMBED_MODEL` picks the embedding model.

The coding models' settings are at the top of `coder/coder.sh`.

## Security: this repo is public

- **Never in the repo:** the lab's address, login and key (`.secrets/`, ignored by git), passwords, and API keys.
- **On the lab only:**
  - RAGFlow's passwords, in `~/ragflow/lab-passwords.env` (mode 600);
  - the coder API keys, in `~/coder/api-keys` (mode 600), and nginx's root-only copy in
    `/etc/nginx/coder-keys.map`.
- **Nothing reaches the lab from GitHub:** the lab pulls this repo, and both public sites refuse any connection that
  does not come through Cloudflare.
- **Only one port of each service is reachable,** through nginx: RAGFlow's web UI, and the coder `/v1/` APIs with a
  key. Every database, queue and admin port stays on the lab's 127.0.0.1 or the services' own networks.
- **Before a push, check the diff.** The full history was scanned with TruffleHog and a pattern search on
  2026-11-23 and is clean. The history was rewritten that day to remove a note about another project, so clones from
  before then are out of date.

## RAGFlow

**Disabled since 2026-11-23**: the notes below are for turning it back on (`deploy/services`).

### How it is set up

- **Where:** the release's own compose files, in `~/ragflow` on the lab, as the docker compose project `ragflow`.
  `ragflow.sh` changes only `docker/.env` and adds one override file, `docker/lab-override.yml`.
- **Ports:** one is published, the web UI on the lab's `127.0.0.1:8088`. RAGFlow's own nginx inside the container
  sends `/api/v1` to its API, so the API is at `https://ragflow.stbfarm.org/api/v1` with an API key made in the UI.
  MySQL, Elasticsearch, MinIO, Redis and the rest stay on the stack's own network. The override is built from the
  services the release defines, and `up` refuses to start if anything else would be published.
- **Logins:**
  - The superadmin, `admin@ragflow.io`, only works in the **admin console**, https://ragflow.stbfarm.org/admin. The
    normal app refuses it with a 403 ("superadmin should not login to this page").
  - Self sign-up is off. The admin adds users in the console: Users, then New user. Those normal users log in at
    https://ragflow.stbfarm.org and do everything else: datasets, chats, model providers, API keys.
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
- **Resources:** about 8 GB of images. The lab disk was 97% full on 2026-11-22 (33 GB free), and 99% after the
  install (17 GB free); `up` refuses a first install below 15 GB. At rest it uses a few GB of memory, plus the
  embedding model. See coder/README.md for what was cleared on 2026-11-23.
- **Admin console, Services:** in v1.0.0 the three RAGFlow processes (`ragflow-server-…`, `ingestor-…`,
  `syncer-…`) show **Timeout** about half the time. This is not a fault. Each process sends a heartbeat only
  every 11th tick, about every 33 s (`SendHeartbeat` in `internal/service/admin_client.go` skips 10 ticks after
  each success). The console calls a process alive only if its last heartbeat is under 15 s old
  (`internal/admin/service.go`). So the status flips between Alive and Timeout while everything works. The real
  check is `https://ragflow.stbfarm.org/api/v1/system/healthz`, or `lab.sh status`.
- **Public site:**
  - Cloudflare, then the lab's nginx (`nginx/ragflow.stbfarm.org.conf`), then 127.0.0.1:8088.
  - Only Cloudflare's addresses may connect.
  - Logins are limited to 10 a minute per visitor.
  - Uploads up to 512 MB, although Cloudflare's free plan stops at 100 MB.
  - Put Cloudflare Access in front if only the team should see the login page.

### Use it as a model (OpenAI-compatible API)

A RAGFlow **chat assistant** (a model, plus the datasets it searches and its prompt) answers in OpenAI's chat format.
Any tool that takes a custom OpenAI-compatible provider can therefore talk to it as if it were a model: every answer
is grounded in the datasets and cites them.

- **Base URL:** `https://ragflow.stbfarm.org/api/v1/openai/<chat_id>`. The tool adds `/chat/completions` itself.
  `<chat_id>` is the assistant's ID, shown in the UI under Chat, then the assistant, then its API/embed settings.
  v1.0 removed the old `/api/v1/chats_openai/<chat_id>` path.
- **API key:** a RAGFlow API key (made at https://ragflow.stbfarm.org/user-setting/api), sent as `Authorization: Bearer <key>`.
- **Model name:** `model`, which means "the assistant's own model". There is no `/models` list, so type the name in by
  hand where a tool asks for one.
- **Extras**, in `extra_body`:
  - `"reference": true` returns the cited chunks;
  - `metadata_condition` filters the documents.
  - Both are documented in RAGFlow's HTTP API reference: `docs/references/http_api_reference.md` in `~/ragflow`.

**What it cannot do: tool calls.** RAGFlow drops any tools the client sends; the v1.0 source says so ("no tool calls on
OpenAI-compat path"). A coding agent's own model edits files and runs commands through tool calls, so RAGFlow can be
a model for **asking questions**, but not the model that drives an agent. For that, keep the agent's usual model and
give it RAGFlow as a tool (the MCP section below).

**opencode:** a custom provider in `~/.config/opencode/opencode.json`. Use it for questions; for edits, switch back to
a tool-calling model.
```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "ragflow": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "RAGFlow",
      "options": {
        "baseURL": "https://ragflow.stbfarm.org/api/v1/openai/<chat_id>",
        "apiKey": "{env:RAGFLOW_API_KEY}"
      },
      "models": { "model": { "name": "RAGFlow research assistant", "tool_call": false } }
    }
  }
}
```
Then choose it with `/models`. One assistant is one provider entry; add more with other `<chat_id>`s.

**VS Code:**
- **Continue** (`~/.continue/config.yaml`): a chat model.
  ```yaml
  models:
    - name: RAGFlow
      provider: openai
      model: model
      apiBase: https://ragflow.stbfarm.org/api/v1/openai/<chat_id>
      apiKey: ${{ secrets.RAGFLOW_API_KEY }}
      roles: [chat]
  ```
- **Cline and Roo Code:** API provider "OpenAI Compatible", with the base URL, the key, and model ID `model`. Their
  agents describe tools inside the prompt, and RAGFlow wraps every request in its own prompt and retrieval. Expect a
  good question-answerer, not a working file editor.
- **GitHub Copilot Chat:** custom OpenAI-compatible models are only offered in some plans and builds. Where offered,
  the same three values apply.

**Claude Code:** it speaks Anthropic's Messages format, not OpenAI's, and it needs tool calls for everything it does.
It can only reach RAGFlow through a translating proxy (LiteLLM, with `ANTHROPIC_BASE_URL` pointing at it), and even
then it could not edit or run anything. Use the MCP route below for Claude Code.

**Check it:**
```sh
curl -s https://ragflow.stbfarm.org/api/v1/openai/<chat_id>/chat/completions \
  -H "Authorization: Bearer $RAGFLOW_API_KEY" -H 'Content-Type: application/json' \
  -d '{"model":"model","stream":false,"messages":[{"role":"user","content":"Summarise what the documents say about ICM."}]}'
```

### Use it as a tool inside coding agents (MCP)

RAGFlow serves an MCP endpoint at **`https://ragflow.stbfarm.org/api/v1/mcp`**. It uses streamable HTTP, and each
client signs in with its own RAGFlow API key (made at https://ragflow.stbfarm.org/user-setting/api). Its tools:
- `ragflow_retrieval`: search the datasets, and get chunks with their sources;
- `ragflow_list_datasets`;
- `ragflow_list_chats`.

With these, an agent can look up a document set (papers, rulebooks, our own write-ups) while it codes. Keep the key in
an environment variable, never in a committed file:
`export RAGFLOW_API_KEY=ragflow-...` (in your shell profile).

**Claude Code:**
```sh
claude mcp add --transport http --scope user ragflow https://ragflow.stbfarm.org/api/v1/mcp \
  --header "Authorization: Bearer $RAGFLOW_API_KEY"
```
`--scope user` keeps it in your own `~/.claude.json`, not in the repo. `claude mcp list` should show it connected.

**opencode** (`~/.config/opencode/opencode.json`; opencode reads `{env:...}` itself):
```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "ragflow": {
      "type": "remote",
      "url": "https://ragflow.stbfarm.org/api/v1/mcp",
      "headers": { "Authorization": "Bearer {env:RAGFLOW_API_KEY}" }
    }
  }
}
```

**VS Code** (GitHub Copilot's agent mode; `.vscode/mcp.json`, or *MCP: Open User Configuration* for every
workspace). It asks for the key once and stores it in VS Code's secret storage:
```json
{
  "inputs": [{ "type": "promptString", "id": "ragflow-key", "description": "RAGFlow API key", "password": true }],
  "servers": {
    "ragflow": {
      "type": "http",
      "url": "https://ragflow.stbfarm.org/api/v1/mcp",
      "headers": { "Authorization": "Bearer ${input:ragflow-key}" }
    }
  }
}
```
Other VS Code agents work the same way: Cline, Roo and Continue take the same URL and header in their own MCP
settings.

**Without the public site:** run `./lab.sh tunnel` and use `http://127.0.0.1:8088/api/v1/mcp`.
**Cloudflare Access:** if Access protects the site, command-line agents are stopped at its login. Give them an Access
service token, sent as two more headers: `CF-Access-Client-Id` and `CF-Access-Client-Secret`.

**Check the endpoint** (from RAGFlow's MCP docs):
```sh
curl -s https://ragflow.stbfarm.org/api/v1/mcp -H "Authorization: Bearer $RAGFLOW_API_KEY" \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```
