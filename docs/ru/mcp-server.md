# RDT MCP-сервер

> **Rambo Docker Tools** — генератор `docker-compose.yml`.  
> MCP-сервер предоставляет всю функциональность RDT в виде типизированных инструментов [Model Context Protocol](https://modelcontextprotocol.io), обеспечивая нативную интеграцию с Claude Desktop, Cursor, Windsurf, VS Code Copilot, Continue и любым другим MCP-совместимым AI-клиентом.

---

## Содержание

- [Зачем MCP, если есть Skill](#зачем-mcp-если-есть-skill)
- [Установка](#установка)
- [Настройка клиентов](#настройка-клиентов)
  - [Claude Desktop](#claude-desktop)
  - [Cursor](#cursor)
  - [Windsurf](#windsurf)
  - [VS Code + Continue](#vs-code--continue)
- [Доступные инструменты](#доступные-инструменты)
  - [rdt_init](#rdt_init)
  - [rdt_add](#rdt_add)
  - [rdt_remove](#rdt_remove)
  - [rdt_list](#rdt_list)
  - [rdt_doctor](#rdt_doctor)
  - [rdt_check](#rdt_check)
  - [rdt_up](#rdt_up)
- [Формат ответов](#формат-ответов)
- [Типичный сценарий работы агента](#типичный-сценарий-работы-агента)

---

## Зачем MCP, если есть Skill

RDT поставляется с двумя вариантами интеграции для AI-агентов.

| | MCP-сервер | Skill (`rdt-skill.md`) |
|---|---|---|
| Работает в Claude Desktop, Cursor, Windsurf | ✅ | ❌ |
| Работает в Augment Code | ✅ | ✅ |
| Типизированные параметры, без составления shell-команд | ✅ | ❌ |
| Структурированные JSON-ответы | ✅ | ❌ |
| Не требует терминала / запуска процессов | ✅ | ❌ |
| Нулевые дополнительные зависимости | ❌ | ✅ |

**Используйте MCP**, если хотите, чтобы RDT был доступен в нескольких клиентах без настройки промптов в каждом.  
**Используйте Skill**, если работаете исключительно в Augment Code и хотите минимальных накладных расходов.

Оба подхода не исключают друг друга — можно настроить их одновременно.

---

## Установка

MCP-сервер — опциональное дополнение. Установите его вместе с RDT:

```bash
# pip
pip install "rdt-rambo[mcp]"

# pipx (рекомендуется для системных CLI-инструментов)
pipx install "rdt-rambo[mcp]"

# из исходников
pip install -e ".[mcp]"
```

После установки бинарник `rdt-mcp` доступен в PATH:

```bash
rdt-mcp --help
```

Сервер общается по протоколу **stdio** (стандартный ввод/вывод) — клиент запускает процесс и обменивается JSON-RPC сообщениями через его stdin/stdout. Привязка к порту или сетевая конфигурация не требуется.

---

## Настройка клиентов

### Claude Desktop

Отредактируйте `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) или `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "rdt": {
      "command": "rdt-mcp"
    }
  }
}
```

Перезапустите Claude Desktop. Инструменты RDT появятся на панели инструментов (иконка 🔧).

---

### Cursor

Создайте или отредактируйте `.cursor/mcp.json` в корне проекта (область видимости — проект) или `~/.cursor/mcp.json` (глобально):

```json
{
  "mcpServers": {
    "rdt": {
      "command": "rdt-mcp"
    }
  }
}
```

Перезагрузите Cursor. Инструменты RDT теперь доступны AI-агенту Cursor.

---

### Windsurf

Отредактируйте `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "rdt": {
      "command": "rdt-mcp"
    }
  }
}
```

---

### VS Code + Continue

Добавьте в `~/.continue/config.json`:

```json
{
  "mcpServers": [
    {
      "name": "rdt",
      "command": "rdt-mcp",
      "args": []
    }
  ]
}
```

---

## Доступные инструменты

Все инструменты принимают необязательный параметр `project_dir` — абсолютный путь к рабочей директории. Если он не указан, используется текущая рабочая директория. Все пути к файлам (`file`) разрешаются относительно `project_dir`.

---

### rdt_init

Инициализировать новые `docker-compose.yml`, `.env` и `.env.example` в директории проекта.

| Параметр | Тип | Обязательный | По умолчанию | Описание |
|----------|-----|:------------:|--------------|----------|
| `file` | string | нет | `docker-compose.yml` | Имя или путь к compose-файлу |
| `force` | boolean | нет | `false` | Перезаписать существующие файлы |
| `project_dir` | string | нет | cwd | Абсолютный путь к директории проекта |

**Успешный ответ:**
```json
{
  "status": "ok",
  "file": "docker-compose.yml",
  "created": [
    "docker-compose.yml",
    "/абсолютный/путь/.env",
    "/абсолютный/путь/.env.example"
  ]
}
```

**Ответ при ошибке:**

```json
{ "status": "error", "message": "File already exists: docker-compose.yml. Use force=True to overwrite." }
```

---

### rdt_add

Добавить сервис в `docker-compose.yml`. Создаёт блок compose, записывает учётные данные в `.env` / `.env.example`, генерирует companion-файлы конфигурации (например, `nginx/nginx.conf`, `prometheus/prometheus.yml`), настраивает volumes и healthcheck.

Всегда предпочитайте `rdt_add` ручному редактированию compose-файла.

| Параметр | Тип | Обязательный | По умолчанию | Описание |
|----------|-----|:------------:|--------------|----------|
| `service` | string | **да** | — | Имя сервиса (например, `postgres`, `redis`, `nginx-proxy`). Используйте `rdt_list` для просмотра всех вариантов. |
| `file` | string | нет | `docker-compose.yml` | Путь к compose-файлу |
| `project_dir` | string | нет | cwd | Абсолютный путь к директории проекта |
| `port` | integer | нет | порт пресета | Переопределить порт хоста |
| `volume` | string | нет | `<service>_data` | Имя volume или путь bind-mount (например, `./data/pg`) |
| `depends_on` | string[] | нет | `[]` | Сервисы, от которых зависит этот сервис |
| `hardcore` | boolean | нет | `false` | Генерировать надёжные случайные пароли вместо заглушек |
| `no_ports` | boolean | нет | `false` | Открывать порты только внутри Docker-сети, не на хост |
| `network` | string | нет | `bridge` | Тип или имя external-сети: `bridge` \| `host` \| `none` \| `<имя>` |
| `container_name` | string | нет | имя сервиса | Явное имя контейнера |
| `hc_interval` | string | нет | по пресету | Интервал healthcheck (например, `10s`) |
| `hc_timeout` | string | нет | по пресету | Таймаут healthcheck (например, `5s`) |
| `hc_retries` | integer | нет | по пресету | Количество попыток healthcheck |
| `hc_start_period` | string | нет | по пресету | Начальный период healthcheck (например, `30s`) |
| `set_vars` | object | нет | `{}` | Переопределить любую внутреннюю переменную мастера (например, `{"nginx_upstream": "app:8080"}`) |

**Успешный ответ:**
```json
{
  "status": "ok",
  "service": "postgres",
  "port": 5432,
  "env_vars": {
    "POSTGRES_USER": "postgres",
    "POSTGRES_PASSWORD": "postgres",
    "POSTGRES_DB": "postgres"
  },
  "artifacts_created": [],
  "hints": []
}
```

**Ответ при ошибке:**
```json
{ "status": "error", "message": "Service 'postgres' already exists in docker-compose.yml." }
```

---

### rdt_remove

Удалить сервис из `docker-compose.yml`. Опционально очищает осиротевшие переменные `.env` и companion-файлы конфигурации, сгенерированные для этого сервиса.

| Параметр | Тип | Обязательный | По умолчанию | Описание |
|----------|-----|:------------:|--------------|----------|
| `service` | string | **да** | — | Имя сервиса для удаления |
| `file` | string | нет | `docker-compose.yml` | Путь к compose-файлу |
| `project_dir` | string | нет | cwd | Абсолютный путь к директории проекта |
| `clean_env` | boolean | нет | `false` | Удалить осиротевшие переменные из `.env` и `.env.example` |
| `clean_artifacts` | boolean | нет | `false` | Удалить companion-файлы конфигурации сервиса |

**Успешный ответ:**
```json
{
  "status": "ok",
  "removed": "postgres",
  "removed_volumes": ["postgres_data"],
  "cleaned_env_vars": ["POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"],
  "cleaned_files": [],
  "dependents_warned": ["pgadmin"]
}
```

> **Примечание:** `dependents_warned` содержит сервисы, у которых был `depends_on: [<удалённый сервис>]`. Удаление всё равно выполняется, но эти сервисы могут требовать обновления или также удаления.

---

### rdt_list

Список всех доступных пресетов сервисов. Только чтение — ничего не изменяет.

| Параметр | Тип | Обязательный | По умолчанию | Описание |
|----------|-----|:------------:|--------------|----------|
| `category` | string | нет | — | Фильтр по категории (например, `Relational DB`, `NoSQL / Cache`, `Monitoring`) |

**Ответ:**
```json
{
  "presets": [
    {
      "name": "postgres",
      "display_name": "PostgreSQL",
      "category": "Relational DB",
      "image": "postgres:16-alpine",
      "default_port": 5432,
      "container_port": 5432,
      "has_healthcheck": true
    }
  ]
}
```

---

### rdt_doctor

Запустить полную диагностику проекта. Проверяет доступность Docker, Compose v2, валидность YAML, полноту `.env`, конфликты портов, висячие ссылки в `depends_on` и наличие companion-файлов конфигурации.

**Всегда вызывайте `rdt_doctor` перед завершением задачи.** Это единственная команда, которая валидирует весь сгенерированный стек целиком.

| Параметр | Тип | Обязательный | По умолчанию | Описание |
|----------|-----|:------------:|--------------|----------|
| `file` | string | нет | `docker-compose.yml` | Путь к compose-файлу |
| `project_dir` | string | нет | cwd | Абсолютный путь к директории проекта |

**Ответ:**
```json
{
  "checks": [
    { "name": "docker",          "status": "ok",   "message": "Docker 27.3.1",                  "details": [] },
    { "name": "compose",         "status": "ok",   "message": "Docker Compose v2.29.7",         "details": [] },
    { "name": "compose_valid",   "status": "ok",   "message": "Valid",                          "details": [] },
    { "name": "env_vars",        "status": "ok",   "message": "All variables are set",          "details": [] },
    { "name": "port_conflicts",  "status": "ok",   "message": "No conflicts",                   "details": [] },
    { "name": "dangling_deps",   "status": "ok",   "message": "No dangling deps",               "details": [] },
    { "name": "companion_files", "status": "ok",   "message": "All files present",              "details": [] }
  ],
  "summary": { "ok": 7, "warn": 0, "error": 0, "skip": 0 }
}
```

Статусы проверок: `ok`, `warn`, `error`, `skip`.

---

### rdt_check

Validate `docker-compose.yml` syntax by running `docker compose config`. Detects YAML errors, unknown keys, and invalid references.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `file` | string | no | `docker-compose.yml` | Compose file path |
| `project_dir` | string | no | cwd | Absolute path to the project directory |
| `timeout_seconds` | number | no | `120` | Positive execution deadline in seconds |

**Success response:**
```json
{ "status": "ok", "valid": true, "command": "docker compose -f docker-compose.yml config", "returncode": 0, "stdout": "...", "stderr": "", "stdout_truncated": false, "stderr_truncated": false, "code": null, "message": null }
```

**Failure response:**
```json
{ "status": "error", "valid": false, "code": "command_failed", "returncode": 1, "error": "invalid configuration", "command": "docker compose -f docker-compose.yml config", "stdout": "", "stderr": "invalid configuration", "stdout_truncated": false, "stderr_truncated": false, "message": null }
```

---

### rdt_up

Start the Docker Compose stack via `docker compose up`.

> **Do not call this tool unless the user explicitly asks to start the stack.**
> The standard agent workflow ends with `rdt_doctor` — the user starts the stack themselves.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `file` | string | no | `docker-compose.yml` | Compose file path |
| `project_dir` | string | no | cwd | Absolute path to the project directory |
| `detach` | boolean | no | `true` | Run containers in the background |
| `timeout_seconds` | number | no | `120` | Positive execution deadline in seconds |

**Response:**
```json
{ "status": "ok", "command": "docker compose -f docker-compose.yml up -d", "returncode": 0, "stdout": "", "stderr": "", "stdout_truncated": false, "stderr_truncated": false, "code": null, "message": null }
```

Both Compose tools capture output and return the final 64 KiB of each stream; the corresponding truncation flag indicates omitted output. Failures use `command_failed`, `executable_not_found`, or `timeout` in `code`. A missing executable has a null return code. A timeout terminates the command, but the stack may already have changed; RDT does not retry or undo those changes. Set `timeout_seconds` to a positive number to override the default.

---

## Response Format

All tools return a JSON object. The fields present depend on the tool:

- **`status`** (`"ok"` / `"error"`) — included when the operation mutates state (`rdt_init`, `rdt_add`, `rdt_remove`)
- **`message`** — human-readable error description, present only when `status` is `"error"`
- Tool-specific payload fields (see each tool's documentation above)

An error from `rdt_up` can occur after the stack has changed. Inspect its diagnostics before taking further action.

---

## Типичный сценарий работы агента

```
1. rdt_list           → узнать доступные сервисы и их точные имена
2. rdt_init           → создать docker-compose.yml, .env, .env.example
3. rdt_add (×N)       → добавить каждый нужный сервис
                         связать сервисы через depends_on
                         использовать no_ports=true для внутренних сервисов
                         использовать hardcore=true для production-паролей
4. rdt_doctor         → валидировать весь стек (обязательно)
5. rdt_check          → проверить синтаксис YAML (опционально, doctor это покрывает)
6.  → представить результаты пользователю
     показать учётные данные из полей env_vars
     попросить пользователя запустить `rdt up` или вызвать rdt_up если попросят
```

### Пример: Postgres + pgAdmin

```
rdt_init()
rdt_add("postgres", hardcore=True, volume="./data/pg")
rdt_add("pgadmin", depends_on=["postgres"], no_ports=False)
rdt_doctor()
```

### Пример: Стек мониторинга

```
rdt_init()
rdt_add("prometheus")
rdt_add("grafana", depends_on=["prometheus"])
rdt_doctor()
```

### Пример: Удаление сервиса с очисткой

```
rdt_remove("postgres", clean_env=True, clean_artifacts=True)
rdt_doctor()   # подтвердить что оставшийся стек всё ещё валиден
```


## Read-only project previews

`rdt_init`, `rdt_add`, and `rdt_remove` accept `dry_run` (default `false`). Set it to
`true` to return a structured plan without writing files or launching Docker:

```json
{"service": "postgres", "project_dir": "/path/to/project", "hardcore": true, "dry_run": true}
```

A successful preview returns `status: "ok"`, `dry_run: true`, `operation`,
`project_root`, `actions`, and `warnings`. Each action contains `path`, `kind`,
`action` (`create`, `update`, `delete`, or `skip`), `diff`, and `keys`.
Environment key entries contain a key and action; credential entries may contain
a redacted/generated placeholder, never the credential value. File diffs redact
known credentials; arbitrary unknown secrets may still require manual review.

Ordinary calls without `dry_run` keep their existing behavior. Preview performs
the same validation, force/overwrite selection, cleanup selection, and default
Compose-file resolution. Execute a later ordinary call to recompute and apply
changes; generated credential placeholders are not literal future passwords.
