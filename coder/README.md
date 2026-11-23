# Coding models on the lab

Coding models for opencode and other agents run on the lab's RTX 4090. They are served by Ollama, which speaks
OpenAI's chat API with tool calls, so agents can edit files and run commands through them. It also speaks Anthropic's
Messages API. They run at **https://coder.stbfarm.org/v1**, and every request needs an API key. They are set up,
deployed and checked the same way as RAGFlow, by the same CI/CD ([../README.md](../README.md)).

| Model name | What it is | Context | Speed on the 4090 |
|---|---|---|---|
| `qwen3.8-abliterated:27b` (**default**, always loaded) | Qwen3.8 27B with its refusals removed (huihui-ai's abliterated GGUF, 4-bit, 16.6 GB) | 98,304 | 46 tok/s, 50 with thinking |
| `qwen3.8:27b` | Qwen3.8 27B as Qwen released it, August 2026, 4-bit (17.7 GB), from Ollama's library | 98,304 | 67 tok/s, 109 with thinking |

Both call tools, think (levels `low`, `medium` and `xhigh`; `medium` by default), and read images.

| File | What it does |
|---|---|
| `coder.sh` | Runs on the lab: `up`, `status`, `down`, `purge`, `key add/list/rm`, `check` |
| `nginx/coder.stbfarm.org.conf` | The public site: Cloudflare only, a key on every request, only the `/v1/` APIs |

## Run it

From the repo root, on your machine:

```sh
./lab.sh coder status          # container, GPU, loaded and downloaded models, API health
./lab.sh coder key add NAME    # an API key for one person or tool; printed once
./lab.sh coder key list        # who has a key (the names only)
./lab.sh coder key rm NAME
./lab.sh coder up              # by hand; CD does this on every deploy
./lab.sh coder down            # stop it, which frees the 4090 (the downloaded models stay)
./lab.sh tunnel                # also forwards http://127.0.0.1:11435/v1, with no key needed
```

**Keys:**
- They live only on the lab, in `~/coder/api-keys` (mode 600).
- nginx reads them from `/etc/nginx/coder-keys.map`, so after adding or removing a key, run once on the lab:
  `sudo sh ~/ragflow-lab/deploy/install.sh`. The CD log reminds you when the keys are newer than nginx's copy.
- Give each person their own key, so one can be removed without affecting the others.

**First time:**
1. A proxied DNS record for `coder.stbfarm.org` in Cloudflare, pointing at the lab (done 2026-11-23).
2. `./lab.sh coder key add <you>`.
3. `sudo sh ~/ragflow-lab/deploy/install.sh` on the lab.

## Connect opencode

### 1. Get a key

From this repo, on a machine with lab access (one key per person):

```sh
./lab.sh coder key add <name>     # prints the key once: pass it on privately
```

Then, on the lab, let nginx accept it: `sudo sh ~/ragflow-lab/deploy/install.sh`.

### 2. Save the key on your computer

Readable only by you, and never in a repo:

```sh
mkdir -p ~/.config/opencode
printf '%s\n' 'sk-lab-...' > ~/.config/opencode/lab-coder.key
chmod 600 ~/.config/opencode/lab-coder.key
```

### 3. Add the lab to opencode

Merge this into `~/.config/opencode/opencode.json`, keeping any providers already there. opencode reads the key from
the file (`{file:...}`).

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "lab": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Lab",
      "options": {
        "baseURL": "https://coder.stbfarm.org/v1",
        "apiKey": "{file:~/.config/opencode/lab-coder.key}"
      },
      "models": {
        "qwen3.8:27b": {
          "name": "Qwen3.8 27B (lab 4090)",
          "tool_call": true,
          "reasoning": true,
          "limit": { "context": 98304, "output": 16384 }
        },
        "qwen3.8-abliterated:27b": {
          "name": "Qwen3.8 27B abliterated (lab 4090)",
          "tool_call": true,
          "reasoning": true,
          "limit": { "context": 98304, "output": 16384 }
        }
      }
    }
  }
}
```

To make the lab model opencode's default, add `"model": "lab/qwen3.8-abliterated:27b"` at the top level: the
model the lab keeps loaded, so no swap is needed. If you would rather keep the
key in an environment variable, use `"apiKey": "{env:LAB_CODER_KEY}"` and `export LAB_CODER_KEY=sk-lab-...` in your
shell profile.

### 4. Check and use it

```sh
opencode models lab        # lists lab/qwen3.8:27b and lab/qwen3.8-abliterated:27b
cd ~/some/project
opencode                   # uses the default; /models switches
opencode run -m lab/qwen3.8-abliterated:27b "explain what this repo does"     # one-off, without the interface
```

The uncensored model is the default (chosen 2026-11-23). `lab/qwen3.8:27b`, the stock model, is faster (67 against
46 tok/s) and keeps Qwen's own tuning: switch to it with `/models` when speed matters more than refusals.

Tested on 2026-11-23: through opencode, the lab model read a file with a bug, fixed it with a tool call, and
explained the fix.

### Good to know

- **One request at a time:** if two people use the model at once, the second waits until the first finishes.
- **Swapping models:** only one fits on the GPU, so the first request after switching models takes a few seconds.
- **Errors:**
  - `401`: the key is missing or wrong, or the sudo install was not run after the key was made.
  - `404`: the URL is not under `/v1/`.
  - Nothing at all: check `./lab.sh coder status`.
- **Removing someone:** `./lab.sh coder key rm <name>`, then the sudo install on the lab.

## Other tools

The same three values work everywhere: base URL `https://coder.stbfarm.org/v1`, your key, and a model name from the
table above.

- **VS Code, Continue** (`~/.continue/config.yaml`):
  ```yaml
  models:
    - name: Qwen3.8 27B abliterated (lab)
      provider: openai
      model: qwen3.8-abliterated:27b
      apiBase: https://coder.stbfarm.org/v1
      apiKey: ${{ secrets.LAB_CODER_KEY }}
      roles: [chat, edit, apply]
      capabilities: [tool_use]
  ```
- **VS Code, Cline and Roo Code:** API provider "OpenAI Compatible", with the base URL, the key and the model name.
- **Claude Code** works through Ollama's Anthropic Messages API:
  ```sh
  ANTHROPIC_BASE_URL=https://coder.stbfarm.org ANTHROPIC_AUTH_TOKEN=$LAB_CODER_KEY claude --model qwen3.8-abliterated:27b
  ```
- **Any OpenAI client:**
  ```sh
  curl https://coder.stbfarm.org/v1/chat/completions -H "Authorization: Bearer $LAB_CODER_KEY" \
    -H 'Content-Type: application/json' \
    -d '{"model":"qwen3.8-abliterated:27b","messages":[{"role":"user","content":"Write a Python function that reverses a list."}]}'
  ```

## The uncensored model

`qwen3.8-abliterated:27b` is Qwen3.8 27B with "abliteration" applied: the direction in its activations that
produces refusals is removed from the weights. It no longer declines requests the stock model refuses, such as some
security, exploit or red-team code. It is not smarter.

- **Source:**
  - [huihui-ai/Huihui-Qwen3.8-27B-abliterated-GGUF](https://huggingface.co/huihui-ai/Huihui-Qwen3.8-27B-abliterated-GGUF),
    the most downloaded abliterated Qwen3.8 (4.5 million downloads; published 2026-08-16, two days after the model).
  - The file is the dynamic 4-bit `Q4_K_M` (16.6 GB). Ollama refuses the plain `Q4_K` tag.
- **Measured on the 4090, 2026-11-23:**
  - fully on the GPU at a 98k context (19 GB);
  - correct tool call;
  - but slower than the stock model: 46 against 67 tok/s, and 50 against 109 with thinking.
- **The default since 2026-11-23,** by choice. Abliteration costs some quality and speed; the stock model stays one
  `/models` away.
- **Swapping:** only one model fits on the 4090. The uncensored one stays loaded; the first request for the stock
  model swaps it in, and later requests for the uncensored one swap back. Each swap takes a few seconds.
- **Responsibility:** the model will write what it is asked, including insecure or harmful code. Whoever uses it is
  responsible for what they do with the output, under the law and the licences involved. Qwen3.8 and the
  abliterated weights are Apache 2.0.

## How the models were chosen (2026-11-23)

1. The first choice was **Qwen3-Coder 30B-A3B** (July 2025): 18.6 GB, a mixture of experts with 3.3B active, made
   for agentic coding.
2. A check for newer models found **Qwen3.8 27B** (August 2026) in Ollama's library. Its official model card
   ([Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B)) reports, with the Claude Code harness:
   - SWE-bench Pro 61.7, against Qwen3.6-27B's 53.5 and Opus 4.6 Max's 53.4;
   - Terminal Bench 2.1: 73.0;
   - LiveCodeBench v6: 90.3.

   Qwen3-Coder 30B has no SWE-bench Pro score; on the easier SWE-bench Verified it reads about 51 in third-party
   runs. The other candidates found were devstral-small-2 (15.2 GB), glm-4.7-flash (19.0 GB) and laguna-xs-2.1
   (20.3 GB).
3. **Both were measured on the 4090**, each at a 65k context:

   | | Memory | Speed | Tool call |
   |---|---|---|---|
   | Qwen3-Coder 30B | 22 GB | 160 tok/s | correct |
   | Qwen3.8 27B | 17 GB | 67 tok/s, 109 with thinking | correct |

   Qwen3.8 was chosen: much stronger on agentic coding, and fast enough. Qwen3-Coder was removed.
4. **Context:**
   - 131,072 tokens spilled 12% of the model onto the CPU.
   - **98,304** fits fully on the GPU, using 22 GB of the 4090's 24.5 GB.
   - `up --wait` fails if a model does not fit fully, so a bad setting is caught.

Scores move fast: check again when a new model family appears, then measure it on the 4090 the same way before
switching.

## How it is set up

- **The container:**
  - `coder-ollama`, image `ollama/ollama:latest` (0.34.4 on 2026-11-23), restarted by Docker if it stops.
  - Only the RTX 4090 is visible inside, chosen by its name and fixed by its UUID.
  - Port 127.0.0.1:11435.
  - The models are in `~/coder/models`.
- **Memory:**
  - The default model, the uncensored one, stays loaded (`OLLAMA_KEEP_ALIVE=-1`).
  - One model at a time, one request at a time.
  - Flash attention and an 8-bit KV cache.
- **Sharing the lab:**
  - The research pipeline only takes a GPU with under 2 GB in use, so it leaves the 4090 alone while a model is
    loaded, and keeps the RTX PRO 6000 and the 3090.
  - `./lab.sh coder down` gives the 4090 back to training.
- **The public site:**
  - Only `/v1/` is served: chat completions, completions, models, embeddings, responses, and Anthropic's messages.
  - Ollama's own `/api/`, which can download and delete models, is never reachable from outside.
  - Requests are limited to 5 a second per key, with bursts of 40.
- **Changing models:**
  - Edit the defaults at the top of `coder.sh` (`CODER_MODELS`, `CODER_CONTEXT`, `CODER_GPU`) and push.
  - `NAME=SOURCE` downloads any Ollama or `hf.co/...` model and serves it under a short name.
  - CD downloads and loads the new model, and refuses to start a download with under 25 GB of disk free. Remove a
    model you no longer list on the lab with `docker exec coder-ollama ollama rm NAME`.

## Disk space on the lab (2026-11-23)

The lab disk was 99% full, with 17 GB free. To make room, these were deleted, all chosen by the owner:
- The uv cache was pruned (2.5 GB) and the pip cache purged.
- In poker-analysis `research/blueprint`, the early heads-up runs `run3` to `run7`, `runvec` and their `slum_` and
  `frozen_` copies were removed (about 19 GB). `run2` was kept, since scripts still default to it.
- Two Ollama models retired in poker-analysis `research/AGENTS.md`, `wizard-vicuna-uncensored:13b` and
  `Tiger-Gemma-9B`, were removed. The 5 GB of Tiger-Gemma weights stay, shared with `tiger-gemma-tools:9b`.

After the two coding models (34 GB), about 15 GB is free. Elasticsearch, inside RAGFlow, stops accepting documents
below 5 GB free.
