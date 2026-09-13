# telegram-tech-publisher

Автономная петля: опрашивает релизы GitHub, пишет пост голосом канала через LLM и сама публикует
его в один Telegram-канал по расписанию. Влита в `main` 25.05 (PR #7).

## Команды

Пакетный менеджер — **uv**, не pip/poetry: всё запускается через `uv run`, зависимости правятся
в `pyproject.toml` + `uv.lock`.

- `make dev` — `uv sync` и `.env` из примера.
- `make lint` — ruff check + ruff format --check.
- `make typecheck` — mypy strict по `src`.
- `make sec` — bandit, только high (`-ll`).
- `make test` — pytest с покрытием.
- `make smoke-github`, `make smoke-telegram` — ходят НАРУЖУ: первая дёргает GitHub API, вторая
  реально шлёт сообщение в `TELEGRAM_TEST_CHANNEL_ID`. Не запускать «просто посмотреть».
- Петля (на актуальном `main`): `uv run telegram-tech-publisher dry-run|status|tick|validate|daemon`.
  Безопасны только `dry-run` и `status`; `tick`, `validate` и `daemon` ПУБЛИКУЮТ в боевой
  `TELEGRAM_CHANNEL_ID`, а `daemon` ещё и блокирующий.

## Как проверить, что не сломал

Ровно то, что гоняет CI, в этом порядке: `make lint`, `make typecheck`, `make sec`, `make test`.
Порог покрытия — 80% (`--cov-fail-under=80`), ниже — CI красный.

CI фильтрует маркеры (`-m "not integration and not real_llm"`), а `make test` — нет: локально он
тянет `tests/integration` (нужен Postgres) и падает там, где CI зелёный. Сверка один в один:
`uv run pytest -v --cov=src --cov-fail-under=80 -m "not integration and not real_llm"`.

Smoke-цели и команды петли в проверку не входят — они выходят наружу.

## Env

`.env` (шаблон — `.env.example`). Обязательны, дефолтов нет, без любого из них падает ЛЮБАЯ команда
CLI, включая безобидный `status`: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID` (боевой канал петли),
`TELEGRAM_TEST_CHANNEL_ID` (канал для smoke), `GITHUB_TOKEN`.

`DRAFTER_BACKEND` по умолчанию `claude_code`: драфтер пишет пост через локальный бинарь `claude`
(подписка, OAuth), `ANTHROPIC_API_KEY` не нужен и не используется. Бэкенд `anthropic` — платный
путь на api.anthropic.com, включать только по прямой просьбе владельца; `mock` — для тестов.

## Грабли

- Дедупликация публикаций живёт в SQLite в `STATE_DIR` (`~/.local/share/telegram-tech-publisher`).
  Потерял файл — петля заново опубликует старые релизы. `DATABASE_URL` и alembic это НЕ они: это
  параллельный мульти-тенантный путь iter-30+, петля им не пользуется.
- Публикатор экранирует MarkdownV2 во всём тексте целиком, уже после драфтера. Любая разметка от
  LLM уезжает в канал литералами (`\*`, `\_`). Драфт обязан быть простым текстом.
- Слишком длинный драфт не режется: тик уходит в `failed`, кандидат остаётся неопубликованным
  и будет выбран на следующем тике.
- Бэкенд `claude_code` не отдаёт счётчики токенов — в состоянии они пишутся нулями. Нули в
  `status` НЕ доказывают, что LLM не звали.
- Рабочая копия может отставать от `main` на несколько PR: в отставшем дереве нет `cli.py`, и тогда
  smoke-цели падают с ModuleNotFoundError, а целей петли в Makefile ещё нет. Перед работой —
  `git fetch origin main` и сверить `git log --oneline origin/main -1`.

## Этикет репозитория

- Коммиты — conventional commits. Проходят только типы: `feat`, `fix`, `docs`, `style`, `refactor`,
  `perf`, `test`, `build`, `ci`, `chore`, `revert`. Тема ≤ 100 символов (ошибка), строки тела ≤ 100
  (предупреждение), футеры по длине не проверяются. Правило `subject-case` отключено намеренно —
  `TelegramPublisher`, `MarkdownV2`, `ADR-0003` в теме законны.
- commitlint гоняется только на pull_request: прямой коммит в `main` не проверяется вовсе, поэтому
  любые изменения — через PR.
- Ни в ветках, ни в коммитах, ни в PR не упоминать Claude: никаких `Co-Authored-By` и
  «Generated with Claude Code».
- Не коммитить и не пушить без прямой просьбы владельца.
