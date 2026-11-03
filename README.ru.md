# 🌐 Local Web Agent — offline LLM with real internet access

> Run a **local** large language model that **browses the web by itself** — search, read full pages, fetch live news — directly from the built‑in web UI, with **no paid APIs, no keys, no cloud**. Tested on a 4 GB RAM laptop running Windows 8.1, CPU‑only.

[Русская версия / Russian version](./README.ru.md)

![license](https://img.shields.io/badge/license-MIT-blue) ![platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey) ![keys](https://img.shields.io/badge/API%20keys-required%3A%200-green)

---

## Why this exists

Local models are smart but blind: they know nothing about *today*. The usual fix — plug in a hosted search API — brings three problems:

1. **Money & keys.** Most tutorials assume SerpAPI / Brave / Tavily / Google CSE, i.e. sign‑up + quota + billing.
2. **Google CSE is dead for new users.** Since **January 20, 2026** Google closed the *Custom Search JSON API* to new projects. A fresh project gets `403 PERMISSION_DENIED` no matter how many "Enable" buttons you press — the green checkmark in the console lies.
3. **Console‑only agents.** Many "LLM + internet" demos are a PowerShell/Python REPL. You type commands; there is no chat UI.

**Local Web Agent** solves all three. The model talks to the internet through **MCP (Model Context Protocol)** tools that use **keyless, free backends**:

| Capability | Backend | Key needed? |
|---|---|---|
| General web search | `ddgs` (DuckDuckGo / Mojeek / Brave / Startpage rotation) | ❌ none |
| Live news | Google News **RSS** | ❌ none |
| Independent index | Marginalia Search | free demo key `public` |
| Read a full page | direct HTTP + HTML→text extraction | ❌ none |
| Self‑diagnostics | `search_health` tool | ❌ none |

Everything runs in **one browser tab**. The model decides *on its own* when to search, which links to open, and how many pages to read in a single turn — exactly like a human researcher.

---

## What you get

- 🧠 A local LLM served by `llama-server` (llama.cpp) with its native web UI at `http://127.0.0.1:8080`.
- 🔌 An **MCP server** (`google_mcp.py`) exposing `web_search`, `news_search`, `read_page`, `search_health`.
- 🤖 **Tool‑calling in the browser**: the model emits tool calls, llama.cpp executes them server‑side (`--agent`), and the answer is grounded in live results.
- 🪟 Optional **cloudflared tunnel** to expose the UI outside your LAN.
- 🎛️ Helper batch scripts to switch between several GGUF models or run two at once.
- 📉 Runs on **4 GB RAM / CPU / Windows 8.1** — if it works here, it works anywhere.

---

## Architecture

```
┌─────────────┐   HTTP /tools    ┌──────────────────┐   HTTPS    ┌────────────────┐
│  Browser    │ ◄──────────────► │  llama-server    │ ◄────────► │  web_search    │
│  (web UI)   │                  │  (llama.cpp)     │  --agent   │  ddgs / RSS /  │
└─────────────┘                  │  + MCP client    │            │  Marginalia    │
                                 └────────┬─────────            └────────────────┘
                                          │ stdio (MCP)
                                          ▼
                                 ┌──────────────────┐
                                 │ google_mcp.py    │  ← Python, no keys
                                 │ (FastMCP server) │
                                 └──────────────────┘
```

The model never sees raw HTML. `read_page` strips scripts/menus/ads and returns clean article text, truncated to a configurable budget so the context window survives.

---

## Requirements

| Component | Minimum | Notes |
|---|---|---|
| OS | Windows 8.1 / 10 / 11, Linux, macOS | any |
| RAM | 4 GB | 8 GB+ recommended for ≥3B models or two models at once |
| CPU | x86‑64 | AVX2 helps; no GPU required |
| Python | 3.11+ | 3.13 is the last build shipping for Win 8.1 |
| llama.cpp | build with **MCP support** | must accept `--mcp-servers-config` and `--ui-mcp-proxy` (e.g. `b10679`+). Check with `llama-server --help \| findstr /i mcp`. |
| Disk | ~2–6 GB | for the GGUF model file(s) |

> ⚠️ **MCP is mandatory.** Older llama.cpp builds have no `--mcp-servers-config`. Update your build or this won't work. The console‑agent fallback (a PowerShell REPL) is described at the bottom.

---

## Installation

### 1. Python packages

```bash
python -m pip install "mcp<2" ddgs requests
```

> 📌 **Pin `mcp<2`.** In `mcp` 2.x the class `FastMCP` was renamed to `MCPServer`, and `from mcp.server.fastmcp import FastMCP` raises `ModuleNotFoundError` → llama.cpp connects but discovers **0 tools**. Either pin `<2` (recommended, simplest) or patch the import with a `try/except`.

### 2. The model (GGUF)

Download any instruction‑tuned GGUF. **Qwen3** is the most reliable for tool‑calling out of the box:

```bash
# ~1.0 GB, fits 4 GB RAM comfortably, native tool-calling + thinking toggle
curl -L -o Qwen3-1.7B-Q4_K_M.gguf \
  "https://huggingface.co/bartowski/Qwen3-1.7B-GGUF/resolve/main/Qwen3-1.7B-Q4_K_M.gguf"
```

Alternatives (see [Models](#models)):
- `Qwen2.5-3B-Instruct-Q4_K_M.gguf` — broader knowledge, weaker tool‑calling.
- `DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf` — best math/logic, often *thinks instead of searching*.

### 3. Clone this repo

```bash
git clone https://github.com/vanyapepei920-sudo/local-web-agent.git
cd local-web-agent
```

Layout:

```
local-web-agent/
├── google_mcp.py     # MCP server: web_search / news_search / read_page / search_health
├── mcp.json          # tells llama-server how to launch google_mcp.py
├── ai.bat            # menu: pick one GGUF, launch with internet
├── two.bat           # launch two models on ports 8080 + 8081
├── README.md         # (this file, English)
└── README.ru.md      # Russian version
```

### 4. Point `mcp.json` at your Python

`llama-server` spawns the MCP process **without a shell**, so a bare `python` usually fails (`failed to spawn 'python'`). Use the **absolute path**:

```json
{
  "mcpServers": {
    "web": {
      "command": "C:/Users/<you>/AppData/Local/Programs/Python/Python313/python.exe",
      "args": ["C:/path/to/local-web-agent/google_mcp.py"]
    }
  }
}
```

Find your interpreter with `where python` (Windows) or `which python3` (Linux/macOS). Use **forward slashes** in JSON.

---

## Run

```bash
# Windows (cmd)
llama-server.exe ^
  -m C:/path/to/Qwen3-1.7B-Q4_K_M.gguf ^
  --jinja --agent ^
  --mcp-servers-config C:/path/to/local-web-agent/mcp.json ^
  --ui-mcp-proxy ^
  --host 127.0.0.1 --port 8080 ^
  -t 4 -c 8192 --cache-type-k q4_0 --cache-type-v q4_0
```

```bash
# Linux / macOS
llama-server \
  -m ./Qwen3-1.7B-Q4_K_M.gguf \
  --jinja --agent \
  --mcp-servers-config ./mcp.json \
  --ui-mcp-proxy \
  --host 127.0.0.1 --port 8080 \
  -t 4 -c 8192 --cache-type-k q4_0 --cache-type-v q4_0
```

Watch the log for the success line:

```
start: MCP warmup: 'web' discovered 4 tools
setup: Added 4 MCP tools
listening on http://127.0.0.1:8080
```

Open **http://127.0.0.1:8080** and ask:

```
what is the USD/RUB exchange rate today?
```

The model will call `web_search` by itself, the snippets come back, and the answer is grounded in live data. Then try:

```
open the 2nd link and summarize the article
```

→ triggers `read_page`. And:

```
call search_health
```

→ reports which backends are alive.

---

## Configuration

Edit the top of `google_mcp.py`:

| Variable | Default | Meaning |
|---|---|---|
| `BRAVE_KEY` | `""` | optional Brave Search key (free tier 2000/mo) for stronger web results |
| `MARGINALIA_KEY` | `"public"` | free demo key, no sign‑up |
| `GOOGLE_KEY` | `""` | **leave empty** — dead for projects created after Jan 2026 |
| `read_page` `max_chars` | `6000` | per‑page text budget fed to the model |

`llama-server` flags worth tuning:

| Flag | Effect |
|---|---|
| `-c` | context window. `8192` ok for ≤2 GB models on 4 GB RAM; drop to `4096`/`2048` for 3–4 GB models or two servers |
| `-t` | CPU threads (≈ physical cores) |
| `--cache-type-k/v q4_0` | quantized KV cache — essential to fit long contexts in little RAM |
| `--jinja` | use the model's embedded chat template (required for tool tokens) |
| `--agent` | server‑side tool loop (the model's tool calls are executed automatically) |
| `--ui-mcp-proxy` | let the web UI reach the MCP tools |

---

## Models

| Model | Size (Q4_K_M) | Tool‑calling | Best for |
|---|---|---|---|
| **Qwen3‑1.7B** | ~1.0 GB | ✅ native, reliable | the daily agent + search |
| Qwen3‑4B | ~2.5 GB | ✅ native | smarter, but tight on 4 GB RAM |
| Qwen2.5‑3B | ~1.8 GB | ⚠️ flaky | broad knowledge chat |
| DeepSeek‑R1‑Distill‑1.5B | ~1.0 GB | ⚠️ thinks instead | math / logic puzzles |

**Rule of thumb:** keep **Qwen3** as your search agent. Reasoning models (R1, Qwen3‑*Thinking*) tend to narrate a solution instead of invoking `web_search`; if you must use them, force the call: `use web_search: <query>`.

---

## Optional: expose the UI outside your LAN

```bash
cloudflared tunnel --url http://127.0.0.1:8080
```

> 🔒 The web UI has **no authentication**. Only tunnel it onto a trusted network, or put an auth proxy in front. Never expose an unauthenticated local LLM to the open internet.

---

## Helper scripts

- **`ai.bat`** — scans a folder for `*.gguf`, prints a numbered menu, launches the chosen model with MCP. Switch brains in two clicks.
- **`two.bat`** — starts two models on ports `8080` and `8081`, both with MCP. Edit the paths/ports at the top. On 4 GB RAM this usually swaps — watch Task Manager; if memory ≥95% and the disk grinds, run one model at a time.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `failed to spawn 'python'` | llama.cpp spawns without a shell; bare `python` not on PATH | absolute interpreter path in `mcp.json` |
| `discovered 0 tools` | `mcp` 2.x renamed `FastMCP`, or `google_mcp.py` missing/broken | `pip install "mcp<2"`; verify the script runs standalone (it should hang silently, then Ctrl‑C) |
| `Nothing found` from search | all keyless backends rate‑limited / down at the moment | ask the model `call search_health`; retry; add `BRAVE_KEY` |
| `403 PERMISSION_DENIED` on Google | new project after Jan 2026 — CSE closed | don't fight it; this project uses keyless backends by design |
| Web UI hangs on `Waiting for result…` | a backend is slow (timeouts stack up) | wait ~60 s; lower per‑engine timeouts in `google_mcp.py` |
| PowerShell agent shows mojibake / syntax errors | `.ps1` saved as UTF‑8 **without BOM** on legacy Windows | save with BOM, or use ASCII‑only scripts |
| Model answers from memory, never searches | reasoning model, or weak tool template | use Qwen3, or prefix `use web_search:` |
| Server dies at startup | port 8080 taken by an old instance | `taskkill /F /IM llama-server.exe` (Win) / `pkill llama-server` |
| `MemoryError` while editing a GGUF | loading 1 GB of weights into RAM | stream the weight tail with `shutil.copyfileobj` (the included editor already does) |
| Two models = crawling | 4 GB RAM can't hold both + KV + OS | run one at a time via `ai.bat` |

---

## Console‑only fallback (no MCP build)

If your llama.cpp predates MCP, use the standalone PowerShell/Python agent instead: it parses `SEARCH:` / `READ:` lines from the model, fetches pages, and feeds the text back in a REPL. Same idea, no web UI. See the `legacy-console-agent/` branch.

---

## How it actually answers (the loop)

1. You ask a question in the browser.
2. llama.cpp renders the prompt with `--jinja`; the model, seeing the tool schemas, emits a `web_search` call.
3. `--agent` intercepts it, calls the MCP server over stdio.
4. `google_mcp.py` runs `ddgs`/RSS/Marginalia, returns a numbered snippet list.
5. The model reads the list, optionally emits `read_page` for 1–N links (it chooses which).
6. Clean article text returns; the model writes the final, grounded answer.

All of step 2–6 is invisible to you — you just see the answer and a small "🔧 web_search" chip in the UI.

---

## License

MIT — do whatever, attribution appreciated.

## Credits

Built on [llama.cpp](https://github.com/ggml-org/llama.cpp), [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk), [ddgs](https://pypi.org/project/ddgs/), [Qwen3](https://huggingface.co/Qwen), [Marginalia](https://marginalia-search.com/). The whole thing was forged on a Windows 8.1 laptop with 4 GB of RAM — proof that local AI on the web doesn't need a datacenter.



# 🌐 Local Web Agent — локальная нейросеть с настоящим выходом в интернет

> **Локальная** большая модель, которая **сама ходит в сеть** — ищет, читает полные страницы, достаёт свежие новости — прямо из встроенного веб‑интерфейса, **без платных API, без ключей, без облака**. Проверено на ноутбуке с **4 ГБ ОЗУ, Windows 8.1, без видеокарты**.

[English version](./README.md)

![license](https://img.shields.io/badge/license-MIT-blue) ![platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey) ![keys](https://img.shields.io/badge/%D0%9A%D0%BB%D1%8E%D1%87%D0%B8-API-requirement%3A%200-green)

---

## Зачем это нужно

Локальные модели умные, но слепые: они не знают, что происходит **сегодня**. Обычное лечение — подключить хостинговый поисковый API — упирается в три проблемы:

1. **Деньги и ключи.** Почти все туториалы предполагают SerpAPI / Brave / Tavily / Google CSE: регистрация, квоты, биллинг.
2. **Google CSE мёртв для новичков.** С **20 января 2026** Google закрыл *Custom Search JSON API* для новых проектов. Свежий проект получает `403 PERMISSION_DENIED`, сколько бы кнопок «Enable» ты ни нажимал — зелёная галочка в консоли врёт.
3. **Агенты только в консоли.** Многие демо «LLM + интернет» — это PowerShell/Python‑репл: ты печатаешь команды, чата нет.

**Local Web Agent** закрывает все три. Модель выходит в сеть через инструменты **MCP (Model Context Protocol)**, которые используют **бесплатные бэкенды без ключей**:

| Возможность | Бэкенд | Ключ нужен? |
|---|---|---|
| Поиск по вебу | `ddgs` (ротация DuckDuckGo / Mojeek / Brave / Startpage) | ❌ нет |
| Живые новости | Google News **RSS** | ❌ нет |
| Независимый индекс | Marginalia Search | бесплатный демо‑ключ `public` |
| Чтение страницы целиком | прямой HTTP + очистка HTML→текст | ❌ нет |
| Самодиагностика | инструмент `search_health` | ❌ нет |

Всё работает в **одной вкладке браузера**. Модель **сама решает**, когда искать, какие ссылки открывать и сколько страниц прочитать за один ход — как живой исследователь.

---

## Что внутри

- 🧠 Локальная LLM на `llama-server` (llama.cpp) с родным веб‑UI на `http://127.0.0.1:8080`.
- 🔌 **MCP‑сервер** (`google_mcp.py`) с инструментами `web_search`, `news_search`, `read_page`, `search_health`.
- 🤖 **Вызов инструментов в браузере**: модель генерирует тулколлы, llama.cpp исполняет их на сервере (`--agent`), ответ опирается на живые данные.
- 🪟 Опциональный **туннель cloudflared** для доступа извне локалки.
- 🎛️ Батники для переключения между GGUF‑моделями или запуска двух сразу.
- 📉 Едет на **4 ГБ ОЗУ / CPU / Windows 8.1** — если работает здесь, работает везде.

---

## Архитектура

```
┌─────────────┐   HTTP /tools    ┌──────────────────┐   HTTPS    ┌────────────────┐
│  Браузер    │ ◄──────────────► │  llama-server    │ ◄────────► │  web_search    │
│  (веб-UI)   │                  │  (llama.cpp)     │  --agent   │  ddgs / RSS /  │
└─────────────┘                  │  + MCP-клиент    │            │  Marginalia    │
                                 └────────┬─────────┘            └────────────────┘
                                          │ stdio (MCP)
                                          ▼
                                 ┌──────────────────┐
                                 │ google_mcp.py    │  ← Python, без ключей
                                 │ (FastMCP-сервер) │
                                 └──────────────────┘
```

Модель никогда не видит сырой HTML. `read_page` вырезает скрипты/меню/рекламу и возвращает чистый текст статьи, урезанный до настраиваемого бюджета, чтобы контекстное окно выжило.

---

## Требования

| Компонент | Минимум | Примечание |
|---|---|---|
| ОС | Windows 8.1 / 10 / 11, Linux, macOS | любая |
| ОЗУ | 4 ГБ | 8 ГБ+ для моделей ≥3B или двух сразу |
| CPU | x86‑64 | AVX2 ускоряет; GPU не нужен |
| Python | 3.11+ | 3.13 — последняя сборка под Win 8.1 |
| llama.cpp | сборка **с поддержкой MCP** | должен принимать `--mcp-servers-config` и `--ui-mcp-proxy` (напр. `b10679`+). Проверка: `llama-server --help | findstr /i mcp`. |
| Диск | ~2–6 ГБ | под GGUF‑модель(и) |

> ⚠️ **MCP обязателен.** Старые сборки llama.cpp не знают `--mcp-servers-config`. Обновите сборку — иначе не поедет. Консольный агент‑запасной вариант — в конце.

---

## Установка

### 1. Пакеты Python

```bash
python -m pip install "mcp<2" ddgs requests
```

> 📌 **Запиньте `mcp<2`.** В `mcp` 2.x класс `FastMCP` переименован в `MCPServer`, и `from mcp.server.fastmcp import FastMCP` падает с `ModuleNotFoundError` → llama.cpp подключается, но находит **0 инструментов**. Либо пин `<2` (проще всего), либо патч импорта через `try/except`.

### 2. Модель (GGUF)

Любая instruction‑тюнингованная GGUF. **Qwen3** надёжнее всех зовёт инструменты из коробки:

```bash
# ~1.0 ГБ, комфортно в 4 ГБ ОЗУ, нативные тулзы + переключатель thinking
curl -L -o Qwen3-1.7B-Q4_K_M.gguf \
  "https://huggingface.co/bartowski/Qwen3-1.7B-GGUF/resolve/main/Qwen3-1.7B-Q4_K_M.gguf"
```

Альтернативы (см. [Модели](#модели)):
- `Qwen2.5-3B-Instruct-Q4_K_M.gguf` — шире знания, слабее тулзы.
- `DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf` — лучшая математика/логика, часто *думает вместо поиска*.

### 3. Клонировать репозиторий

```bash
git clone https://github.com/vanyapepei920-sudo/local-web-agent.git
cd local-web-agent
```

Структура:

```
local-web-agent/
├── google_mcp.py     # MCP-сервер: web_search / news_search / read_page / search_health
├── mcp.json          # указывает llama-server, как запускать google_mcp.py
├── ai.bat            # меню: выбрать GGUF, запустить с интернетом
├── two.bat           # две модели на портах 8080 + 8081
├── README.md         # (этот файл, английский)
└── README.ru.md      # русская версия
```

### 4. Прописать ваш Python в `mcp.json`

`llama-server` спавнит MCP‑процесс **без оболочки**, поэтому голое `python` обычно не находится (`failed to spawn 'python'`). Ставьте **абсолютный путь**:

```json
{
  "mcpServers": {
    "web": {
      "command": "C:/Users/<you>/AppData/Local/Programs/Python/Python313/python.exe",
      "args": ["C:/path/to/local-web-agent/google_mcp.py"]
    }
  }
}
```

Интерпретатор: `where python` (Windows) или `which python3` (Linux/macOS). В JSON — **прямые слеши**.

---

## Запуск

```bash
# Windows (cmd)
llama-server.exe ^
  -m C:/path/to/Qwen3-1.7B-Q4_K_M.gguf ^
  --jinja --agent ^
  --mcp-servers-config C:/path/to/local-web-agent/mcp.json ^
  --ui-mcp-proxy ^
  --host 127.0.0.1 --port 8080 ^
  -t 4 -c 8192 --cache-type-k q4_0 --cache-type-v q4_0
```

```bash
# Linux / macOS
llama-server \
  -m ./Qwen3-1.7B-Q4_K_M.gguf \
  --jinja --agent \
  --mcp-servers-config ./mcp.json \
  --ui-mcp-proxy \
  --host 127.0.0.1 --port 8080 \
  -t 4 -c 8192 --cache-type-k q4_0 --cache-type-v q4_0
```

В логе ищите строку успеха:

```
start: MCP warmup: 'web' discovered 4 tools
setup: Added 4 MCP tools
listening on http://127.0.0.1:8080
```

Откройте **http://127.0.0.1:8080** и спросите:

```
какой сегодня курс доллара к рублю?
```

Модель сама вызовет `web_search`, вернутся сниппеты, и ответ будет опираться на живые данные. Затем попробуйте:

```
открой вторую ссылку и перескажи статью
```

→ сработает `read_page`. И:

```
вызови search_health
```

→ отчёт, какие бэкенды живы.

---

## Настройка

Верх файла `google_mcp.py`:

| Переменная | По умолчанию | Смысл |
|---|---|---|
| `BRAVE_KEY` | `""` | опциональный ключ Brave (бесплатно 2000/мес) для более сильной выдачи |
| `MARGINALIA_KEY` | `"public"` | бесплатный демо‑ключ, без регистрации |
| `GOOGLE_KEY` | `""` | **оставьте пустым** — мёртв для проектов после янв 2026 |
| `read_page` `max_chars` | `6000` | бюджет текста со страницы, подаваемый модели |

Флаги `llama-server`, которые стоит крутить:

| Флаг | Эффект |
|---|---|
| `-c` | размер контекста. `8192` ок для моделей ≤2 ГБ на 4 ГБ ОЗУ; режьте до `4096`/`2048` для 3–4 ГБ моделей или двух серверов |
| `-t` | потоки CPU (≈ число физических ядер) |
| `--cache-type-k/v q4_0` | квантованный KV‑кэш — спасение для длинного контекста на малой памяти |
| `--jinja` | использовать встроенный шаблон чата модели (нужен для токенов тулз) |
| `--agent` | серверный цикл инструментов (тулколлы модели исполняются автоматически) |
| `--ui-mcp-proxy` | дать веб‑UI доставать MCP‑инструменты |

---

## Модели

| Модель | Размер (Q4_K_M) | Тулзы | Для чего |
|---|---|---|---|
| **Qwen3‑1.7B** | ~1.0 ГБ | ✅ нативно, надёжно | дневной агент + поиск |
| Qwen3‑4B | ~2.5 ГБ | ✅ нативно | умнее, но впритык на 4 ГБ |
| Qwen2.5‑3B | ~1.8 ГБ | ⚠️ капризно | чат с широкими знаниями |
| DeepSeek‑R1‑Distill‑1.5B | ~1.0 ГБ | ⚠️ думает вместо поиска | математика / логика |

**Правило:** держите **Qwen3** как поискового агента. Reasoning‑модели (R1, Qwen3‑*Thinking*) любят рассуждать вслух вместо вызова `web_search`; если используете их — принуждайте: `используй web_search: <запрос>`.

---

## Опционально: вывести UI за пределы локалки

```bash
cloudflared tunnel --url http://127.0.0.1:8080
```

> 🔒 Веб‑UI **без авторизации**. Туннелите только в доверенную сеть или ставьте auth‑прокси. Никогда не выставляйте неаутентифицированную локальную LLM в открытый интернет.

---

## Батники‑помощники

- **`ai.bat`** — сканирует папку на `*.gguf`, печатает нумерованное меню, запускает выбранную модель с MCP. Смена мозга в два клика.
- **`two.bat`** — поднимает две модели на портах `8080` и `8081`, обе с MCP. Пути/порты правятся вверху. На 4 ГБ ОЗУ обычно свопит — следите за Диспетчером задач; если память ≥95% и диск свистит, гоняйте по одной.

---

## Диагностика

| Симптом | Причина | Лечение |
|---|---|---|
| `failed to spawn 'python'` | llama.cpp спавнит без оболочки; голое `python` не в PATH | абсолютный путь к интерпретатору в `mcp.json` |
| `discovered 0 tools` | `mcp` 2.x переименовал `FastMCP`, или `google_mcp.py` отсутствует/битый | `pip install "mcp<2"`; проверьте, что скрипт запускается автономно (должен молча висеть, затем Ctrl‑C) |
| `Nothing found` из поиска | все безключевые бэкенды временно rate‑limit‑нуты/легли | попросите модель `вызови search_health`; повторите; добавьте `BRAVE_KEY` |
| `403 PERMISSION_DENIED` на Google | новый проект после янв 2026 — CSE закрыт | не воюйте; этот проект по дизайну на безключевых бэкендах |
| UI висит на `Waiting for result…` | бэкенд медленный (таймауты складываются) | подождите ~60 с; урежьте таймауты движков в `google_mcp.py` |
| PowerShell‑агент: кракозябры / синтаксические ошибки | `.ps1` сохранён в UTF‑8 **без BOM** на legacy Windows | сохраняйте с BOM или используйте ASCII‑скрипты |
| Модель отвечает из памяти, не ищет | reasoning‑модель или слабый шаблон тулз | используйте Qwen3, либо префикс `используй web_search:` |
| Сервер умирает на старте | порт 8080 занят старым экземпляром | `taskkill /F /IM llama-server.exe` (Win) / `pkill llama-server` |
| `MemoryError` при правке GGUF | загрузка 1 ГБ весов в RAM | копируйте хвост весов потоком `shutil.copyfileobj` (в комплекте редактор так и делает) |
| Две модели = тормоза | 4 ГБ ОЗУ не держат обе + KV + ОС | гоняйте по одной через `ai.bat` |

---

## Запасной вариант: только консоль (нет MCP‑сборки)

Если ваша llama.cpp старше поддержки MCP — используйте автономный PowerShell/Python‑агент: он парсит строки `SEARCH:` / `READ:` из вывода модели, качает страницы и возвращает текст в репл. Та же идея, без веб‑UI. См. ветку `legacy-console-agent/`.

---

## Как рождается ответ (цикл)

1. Вы задаёте вопрос в браузере.
2. llama.cpp рендерит промпт через `--jinja`; модель, видя схемы инструментов, эмитит вызов `web_search`.
3. `--agent` перехватывает его и дёргает MCP‑сервер по stdio.
4. `google_mcp.py` гоняет `ddgs`/RSS/Marginalia, возвращает нумерованный список сниппетов.
5. Модель читает список и при желании эмитит `read_page` по 1–N ссылкам (выбирает сама).
6. Возвращается чистый текст статей; модель пишет финальный, обоснованный ответ.

Всё с шага 2 по 6 для вас невидимо — вы видите лишь ответ и маленький чип «🔧 web_search» в UI.

---

## Лицензия

MIT — делайте что хотите, атрибуция приветствуется.

## Благодарности

Построено на [llama.cpp](https://github.com/ggml-org/llama.cpp), [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk), [ddgs](https://pypi.org/project/ddgs/), [Qwen3](https://huggingface.co/Qwen), [Marginalia](https://marginalia-search.com/). Всё это выковано на ноутбуке с Windows 8.1 и 4 ГБ ОЗУ — доказательство, что локальный ИИ в сети не требует дата‑центра.


# Вопросы

Если у вас возник баг, вопрос. Пишите на почту helpaisearch@gmail.com или на Issues
Постараемся помочь.
