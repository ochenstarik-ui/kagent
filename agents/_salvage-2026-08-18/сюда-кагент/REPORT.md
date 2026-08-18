# KAgent E6–E10 Delivery Report

**Дата отчёта:** 2026-08-12  
**Repository:** https://github.com/ochenstarik-ui/kagent  
**Состояние поставки:** четыре PR реализованы и подтверждены зелёным CI; E8 реализована и reviewed, но честно заблокирована обнаруженным baseline deployment defect.  
**Merge:** ни один PR самостоятельно не merged; все перечисленные PR остаются `OPEN`.

## Итоговая таблица

| Задача | PR | Head SHA | CI | Статус |
|---|---|---|---|---|
| E6 — полный Python CI suite | [#21](https://github.com/ochenstarik-ui/kagent/pull/21) | `d9cc0bca102e11caad47f91e2c7b9453e489d5ec` | [31526297214](https://github.com/ochenstarik-ui/kagent/actions/runs/31526297214) | Implemented, reviewed, CI verified; OPEN |
| E10 — drift allowlist integrity | [#22](https://github.com/ochenstarik-ui/kagent/pull/22) | `65f7c9e1e5296ff827806fdfb4593d71a49f5f70` | [31527435722](https://github.com/ochenstarik-ui/kagent/actions/runs/31527435722) | Implemented, reviewed, CI verified; OPEN |
| E7 — visible verified status | [#23](https://github.com/ochenstarik-ui/kagent/pull/23) | `eaa0c84f61311b7136dc03da61341582370e5b0a` | [31533308789](https://github.com/ochenstarik-ui/kagent/actions/runs/31533308789) | Implemented, reviewed, CI verified; OPEN |
| E8 — deployment smoke | [#24](https://github.com/ochenstarik-ui/kagent/pull/24) | `096d7c544db342bbbdafca0cbc796e6612a57eb4` | [31538210543](https://github.com/ochenstarik-ui/kagent/actions/runs/31538210543) | Implemented and reviewed; runtime blocked by issue #25; CI not green |
| E9 — реальные replay eval cases | [#26](https://github.com/ochenstarik-ui/kagent/pull/26) | `8e0e607966a6461ce95e207d4108d166d9c0f77a` | [31541552195](https://github.com/ochenstarik-ui/kagent/actions/runs/31541552195) | Implemented, reviewed, CI verified; OPEN |

## Stack topology

```text
main
└── E6 / PR #21
    ├── E10 / PR #22
    └── E7 / PR #23
        ├── E8 / PR #24  (blocked by baseline deployment defect)
        └── E9 / PR #26  (green; does not inherit E8)
```

E9 намеренно основана на E7, а не на E8, чтобы её независимая проверка не наследовала известный красный deployment job.

## E6 — полный Python CI suite

### Выполнено

- Python CI переведён с selected-file allowlist на directory discovery:
  - `tests/unit`;
  - `services/reasoning-engine/tests/unit`;
  - `services/pipeline/tests/unit`.
- Stale `test_planner_returns_steps` адаптирован к текущему async API без изменения production-кода.
- Workflow выполняет точный `ruff check services scripts tests`.
- Ruff policy хранится в tracked `ruff.toml`.
- Добавлен regression guard против возврата named-file pytest allowlist, `--deselect`, скрытого `-k` и Ruff CLI overrides.
- Directory discovery доказан временным probe test, который был обнаружен collection и затем удалён.

### Результат

- Independent review: без blocking findings.
- Локально: `126 passed`; Ruff, drift, repository validation и diff check — PASS.
- GitHub Actions: все 7 jobs успешны.
- PR merge state на момент отчёта: `CLEAN`.

## E10 — drift allowlist integrity

### Выполнено

- Любой `conftest.py` считается pytest runner entrypoint.
- Playwright specs распознаются через literal `testDir`/`testMatch` в Playwright config и стандартный fallback pattern.
- Placeholder `follow_up_task` отклоняется.
- Максимальный allowlist lifetime ограничен 90 днями.
- `docs/known-drift.json` очищен до пустого списка.
- Обнаружение настоящих orphan modules сохранено.

### Результат

- Independent review: `APPROVE`, blocking findings отсутствуют.
- Focused suite: `23 passed`.
- Combined stacked suite: `114 passed`; Ruff, drift, repository validation, `unreachable=[]` и diff check — PASS.
- GitHub Actions: все 7 jobs успешны.
- PR merge state: `CLEAN`.

### Остаточное ограничение

Playwright parser намеренно не интерпретирует произвольный JavaScript: computed values, spreads и per-project dynamic `testMatch` требуют отдельного расширения контракта.

## E7 — visible verified status

### Выполнено

- Добавлен tracked evidence input `docs/ci-results.json` с main-run provenance.
- `docs/ROADMAP.md` генерируется детерминированно.
- Принимается только успешный `push` run ветки `main` с согласованным SHA.
- PR/branch, missing, malformed, failed, skipped, cancelled и mismatched-SHA evidence fail closed.
- Сохранены честные статусы `verified`, `partial`, `unverified`.
- Automation создаёт отдельную ветку/PR и не push в `main`, не force-push и не auto-merge.
- Mapping в `docs/capabilities.json` не расширялся ради красивого статуса.

### Результат

- Independent review: `APPROVE_WITH_NOTES`, code-level blockers отсутствуют.
- Focused suite: `31 passed`.
- Full local suite, Ruff, ROADMAP guard, drift, repository validation и diff check — PASS.
- GitHub Actions: node, rust, python, eval, NATS, integration и measurability — PASS; PR-only `publish-verification-status` корректно `SKIPPED`.
- PR merge state: `CLEAN`.

### Честный visible result

- 19 capability entries — `verified`.
- 4 — `partial`.
- Stage 0.9 остаётся `partial`: collector не может включить собственный результат в тот же run.
- Реальная least-privilege publication automation окончательно проверяется только после merge/main run.

## E8 — полный deployment smoke

### Реализовано

- Отдельный CI deployment job выполняет полный `docker compose up -d --build`.
- Bounded health readiness и обязательный cleanup.
- Gateway-only workflow: registration, login, tokens, project/task persistence, audit и observability.
- Проверка, что внутренние KAgent-сервисы не публикуют host ports.
- Активный fail-closed probe к Agent Runtime без service secret с ожидаемым `401`.
- Проверка и документация поведения PostgreSQL init scripts на non-empty volume.
- `docker compose ps` и полные container logs публикуются с `if: always()`.

### Проверки реализации

- Independent repair review: `APPROVE`, P0–P2 отсутствуют.
- Focused suite: `9 passed`.
- Full local unit suite: `119 passed`.
- Ruff, `py_compile`, repository validation, ROADMAP guard, post-commit drift и diff check — PASS.

### Runtime blocker

Настоящий GitHub Actions deployment job упал во время Control Plane image build:

```text
ERR_PNPM_WORKSPACE_PKG_NOT_FOUND
"@kagent/contracts@workspace:*" is in the dependencies
but no package named "@kagent/contracts" is present in the workspace
```

Причина: baseline `services/control-plane/Dockerfile` копирует только локальный service manifest и выполняет `pnpm install --prod`, не предоставляя image build корневую workspace-конфигурацию и пакет `@kagent/contracts`.

Ни один контейнер не был создан: diagnostics artifact содержит только заголовок `compose-ps`; compose log пуст, поскольку build завершился до запуска контейнеров.

Отдельный defect:

- [Issue #25 — Control Plane Docker image cannot resolve workspace dependency](https://github.com/ochenstarik-ui/kagent/issues/25)
- [Failed deployment job](https://github.com/ochenstarik-ui/kagent/actions/runs/31538210543/job/93934323865)

Dockerfile/Compose не исправлялись внутри E8: такое изменение было бы scope creep ради искусственного green smoke. E8 остаётся **implemented, runtime verification blocked** до отдельного исправления issue #25 и повторного CI run.

## E9 — реальные replay eval cases

### Выполнено

Оставлены ровно три runnable self-contained случая:

1. `bugfix_leaky_limiter`;
2. `feature_add_endpoint`;
3. `security_fix_header`.

Два пустых draft case удалены. Каждый активный case содержит:

- настоящий stdlib repository snapshot;
- task contract;
- tracked request/response cassette;
- case-owned verifier вне candidate snapshot;
- expected artifacts;
- adjacent-breaking mutation.

Case считается успешным только когда untouched snapshot не проходит, replay проходит, а mutation снова не проходит.

### Безопасность runner

- Нет provider fallback или внешнего provider path.
- Provider calls и replay tokens равны нулю.
- Subprocess использует env allowlist и `shell=False`.
- Tar extraction ограничивает размер, запрещает traversal, links/devices и unsupported members.
- Replay writes ограничены POSIX-relative paths.
- После review дополнительно закрыты Windows path escape и NTFS alternate-data-stream paths: backslash и colon отклоняются до преобразования в host `Path`.
- Документация честно отмечает: env scrubbing не является OS-level network sandbox.

### Измеренный результат

- 3/3 cases passed.
- Provider calls: `0`.
- Replay tokens spent: `0`.
- Average recorded cost: `$0.0053666667`.
- Average repair cycles: `0.6666666667`.
- `gate_passed=false`; release gate не включён.

### Результат поставки

- Independent initial review: `APPROVE_WITH_NOTES`, P0–P2 отсутствовали.
- Windows path finding исправлен через RED→GREEN regression test.
- Repair review: `APPROVE`, P0–P3 отсутствуют.
- Post-commit local suite: `118 passed`; Ruff, repository validation, schema, drift и clean-tree checks — PASS.
- GitHub Actions: все обязательные jobs успешны; PR-only publication job корректно skipped.
- PR merge state: `CLEAN`.

## Что остаётся сделать владельцу

1. Определить порядок merge stacked PR:
   - сначала E6 (#21);
   - затем E10 (#22) и E7 (#23) после обновления/перестановки base при необходимости;
   - затем E9 (#26).
2. Не merge E8 (#24) как полностью verified до исправления issue #25 и зелёного повторного deployment run.
3. После merge E7 проверить настоящий main-only publication run и tracked evidence PR.
4. Не считать открытые green PR эквивалентом merged state.

## Security and provenance

- Secrets, credentials, tokens и connection strings в отчёт не включены.
- Force-push, self-merge и auto-merge не выполнялись.
- Remote CI evidence привязано к точным PR head SHA, указанным в таблице.
