# Отчёт: фактическое состояние проекта на 2026-08-18

- **Задание:** `../inbox/2026-08-18-otchet-o-sostoyanii.md`
- **Агент:** claude
- **Дата:** 2026-08-18
- **Ветка / коммиты:** `claude/aktualizaciya-2026-08-18`

## Что сделано

Собрана фактическая картина репозитория. Ниже — только то, что подтверждено выводом
команды или ссылкой на прогон.

### Ветки и pull request

```
$ gh pr list --state open
(после слияния #35 — пусто)
```

`main` — `131c9b0`, коммит слияния #35. Открытых pull request нет.

На `origin` осталось 15 веток помимо `main`: `verification-state` (служебная, её пишет
непрерывная интеграция), два архива `archive/*`, восемь рабочих `wt/*`, две `fix/*`,
`integration/p13-2026-08-12` и `agent/agent-workspace-cockpit`. Все относятся к уже
влитой или закрытой работе.

### Непрерывная интеграция

Последние прогоны на `main` — success, красной сборки нет:

```
$ gh run list --branch main --limit 5
success  Merge pull request #35 ...           (2026-08-18)
success  Merge pull request #34 ...  31787117383  2026-08-14
success  Add full deployment smoke evidence (#31)  2026-08-13
success  Fix Gateway ConnectInfo bootstrap (#33)   2026-08-13
success  Fix Gateway container healthcheck runtime (#32)  2026-08-13
```

Локальные проверки, не требующие сборки:

```
$ python scripts/validate_repository.py
Repository validation passed: 9 required files present

$ python scripts/drift_check.py
DRIFT CHECK PASSED

$ python scripts/roadmap_status.py --check --no-run-commands
ROADMAP CHECK PASSED
```

### Расхождение зафиксированного и опубликованного статуса

```
docs/ci-results.json в main:   run 31519844840, commit 4e0a20d, 2026-08-11T17:54:02Z
docs/ci-results.json в verification-state: run 31787117383, commit 3538bd4, 2026-08-14T09:18:08Z
```

`docs/ROADMAP.md` в `main` порождён из первого файла, поэтому все ссылки на
доказательства в нём указывают на прогон от 2026-08-11, отставший на три успешных
прогона `main`.

**Это не дефект.** Так устроено намеренно: job `publish-verification-status` пишет
свежий статус в ветку `verification-state`, а не в `main` — решение принято в E13,
[PR #30](https://github.com/ochenstarik-ui/kagent/pull/30), «Publish verification state
without pull requests». Зафиксированная в `main` пара «`capabilities.json` +
`ci-results.json` + `ROADMAP.md`» внутренне согласована, что и подтверждает
`roadmap_status.py --check`. Актуальный статус читается из `verification-state`.

Стоит отдельной задачи одно: `README.md` отсылает к `docs/ROADMAP.md`, не предупреждая,
что это база, а не текущее состояние, и что смотреть надо `verification-state`.

### Состав agents/_salvage-2026-08-18

87 файлов, разобраны полностью — отдельный отчёт `2026-08-18-razbor-salvage.md`.

### Версия и заявленное состояние

`package.json` и `README.md` согласованы: `0.2.0-rc.1`, «Server Release Candidate».

## Как проверено

Каждое утверждение выше приведено вместе с командой и её выводом либо ссылкой на
прогон. Утверждений без артефакта в отчёте нет.

## Что не сделано

Полный локальный прогон критериев приёмки из `AGENTS.md` §6 невозможен на этой машине:

- `cargo test` не запускается ни одним установленным toolchain. Активный
  `stable-x86_64-pc-windows-gnu` падает на `error calling dlltool 'dlltool.exe': program
  not found`; `stable-x86_64-pc-windows-msvc` падает на линковке, потому что
  `link.exe` разрешается в coreutils `C:\Users\Ochenstarik\AppData\Local\hermes\git\usr\bin\link.exe`,
  а Visual Studio Build Tools не установлены (`vswhere.exe` отсутствует);
- `pnpm build` падает на `EPERM: operation not permitted, symlink` при сборке
  `next build` с `output: standalone`. Проверено отдельно: `mklink` возвращает
  «Недостаточно привилегий», то есть у учётной записи нет права создавать символические
  ссылки;
- `pnpm lint` падает — разбор в отчёте по зависимостям.

`cargo fmt --check` и `cargo clippy --all-targets -- -D warnings` проходят: они не линкуют.

## Замечено рядом

1. **Непрерывная интеграция не запускает `pnpm lint` и `pnpm format:check`.** Job `node`
   в `.github/workflows/ci.yml` выполняет `pnpm typecheck`, `pnpm test`, `pnpm build` —
   и всё. При этом `AGENTS.md` §6 и `Makefile` предъявляют исполнителю `pnpm check`,
   в который lint входит. Сейчас `pnpm check` красный на `main`, а сборка зелёная.
   Ровно тот случай, о котором предупреждает §6: проверка, которую никто не запускает,
   создаёт видимость зелёного. **Предлагаю отдельную задачу:** либо добавить `pnpm lint`
   и `pnpm format:check` в job `node`, либо убрать их из `pnpm check` и из `AGENTS.md`.
2. **`apps/web` объявляет несовместимую пару зависимостей** — разбор в отчёте по
   зависимостям, предложение отдельной задачи там же.
3. **15 веток на `origin` относятся к закрытой работе.** Предлагаю отдельную задачу:
   удалить слитые `wt/*` и `fix/*`, оставив `main`, `verification-state` и `archive/*`.
4. **`README.md` не отличает базовый `docs/ROADMAP.md` от актуального статуса в
   `verification-state`.** Предлагаю отдельную задачу на абзац в `README.md`.

## Вопросы к приёмке

Нет.
