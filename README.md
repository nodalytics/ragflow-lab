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
  install (17 GB free); `up` refuses a first install below 15 GB. Memory, at rest, is a few GB for the stack, plus the embedding model.
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

## Use it as a model (OpenAI-compatible API)

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
  -d '{"model":"model","stream":false,"messages":[{"role":"user","content":"What does the 2026-11-17 upgrades note say about nm43?"}]}'
```

## Use it as a tool inside coding agents (MCP)

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

**Without the public site:** run `research/ragflow/lab.sh tunnel` and use `http://127.0.0.1:8088/api/v1/mcp`.
**Cloudflare Access:** if Access protects the site, command-line agents are stopped at its login. Give them an Access
service token, sent as two more headers: `CF-Access-Client-Id` and `CF-Access-Client-Secret`.

**Check the endpoint** (from RAGFlow's MCP docs):
```sh
curl -s https://ragflow.stbfarm.org/api/v1/mcp -H "Authorization: Bearer $RAGFLOW_API_KEY" \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```
