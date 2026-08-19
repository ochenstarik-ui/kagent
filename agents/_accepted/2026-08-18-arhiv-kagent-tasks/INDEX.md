# Архив постановок kagent-tasks

Разбор папки `agents/_salvage-2026-08-18/`, перенесённой с диска коммитом `997495f`.
Дата разбора: 2026-08-18. Задание: `agents/claude/inbox/2026-08-18-razbor-salvage.md`.

Папка `kagent-tasks` жила вне репозитория и раскладывалась по собственной схеме
(`Старые задачи/`, `Поглощённые/`, `Отложенные/`, `Справочное/`). При переносе
раскладку определяли по префиксу имени файла, а не по папке, поэтому выполненные
постановки попали в `inbox/` агентов, а активные — в `done/`. Здесь это исправлено.

Вердикт по каждой постановке опирается на артефакт: слитый pull request и зелёный
прогон непрерывной интеграции. Классификация «поглощено» и «отложено» взята из
`справочное/README-poglosjennye.md` и `отложенные-этапы/README.md` — документов,
написанных при постановке задач.

## Закрытая работа

| Папка | Постановки | Артефакт |
|---|---|---|
| `0.9.0-green-trunk-pr03/` | 0.9.0, A1–A7, A9; поглощена A8 | [PR #3](https://github.com/ochenstarik-ui/kagent/pull/3) |
| `0.9.1-measurability-pr04-pr06/` | 0.9.1, B1, B2, B4; поглощены B3, B5 | [PR #4](https://github.com/ochenstarik-ui/kagent/pull/4), [PR #6](https://github.com/ochenstarik-ui/kagent/pull/6) |
| `c1-c5-control-plane-pr07-pr10/` | C1, C2, C3, C4, C5 | [PR #7](https://github.com/ochenstarik-ui/kagent/pull/7), [PR #8](https://github.com/ochenstarik-ui/kagent/pull/8), [PR #9](https://github.com/ochenstarik-ui/kagent/pull/9), [PR #10](https://github.com/ochenstarik-ui/kagent/pull/10) |
| `d1-e1-e4-runtime-perimeter-pr11-pr15/` | D1, E1, E2, E3, E4 | [PR #11](https://github.com/ochenstarik-ui/kagent/pull/11), [PR #14](https://github.com/ochenstarik-ui/kagent/pull/14), [PR #15](https://github.com/ochenstarik-ui/kagent/pull/15) |
| `p1-p9-d4-d5-vertical-pr17/` | P1, P2, P3, P8, P9, D4, D5; поглощены P4, D2, D3 | [PR #17](https://github.com/ochenstarik-ui/kagent/pull/17) |
| `p10-p12-runtime-web-pr18/` | P10, P11, P12; поглощены P5, P6, P7 | [PR #18](https://github.com/ochenstarik-ui/kagent/pull/18) |
| `e6-e10-pr21-pr27/` | E6, E7, E9, E10; поглощена E5 | [PR #21](https://github.com/ochenstarik-ui/kagent/pull/21), [PR #22](https://github.com/ochenstarik-ui/kagent/pull/22), [PR #23](https://github.com/ochenstarik-ui/kagent/pull/23), [PR #26](https://github.com/ochenstarik-ui/kagent/pull/26), [PR #27](https://github.com/ochenstarik-ui/kagent/pull/27) |
| `e11-image-build-gate-pr29/` | E11 | [PR #29](https://github.com/ochenstarik-ui/kagent/pull/29) |
| `e13-verification-state-pr30/` | E13 | [PR #30](https://github.com/ochenstarik-ui/kagent/pull/30) |
| `e8-deployment-smoke-pr31/` | E8 | [PR #31](https://github.com/ochenstarik-ui/kagent/pull/31) |
| `p13-p14-server-ready-pr34/` | P13, P14 | [PR #34](https://github.com/ochenstarik-ui/kagent/pull/34) |

Подпапки `отчёт*/` — отчёты исполнителей с доказательствами (`TEST_EVIDENCE.md`,
`CI_CHECKS.txt`, `SHA256SUMS`), пришедшие тем же переносом с диска.

Отдельная оговорка по P13: собственный [PR #20](https://github.com/ochenstarik-ui/kagent/pull/20)
закрыт неслитым, но предмет постановки в `main` присутствует — `apps/web/e2e/dashboard.spec.ts`,
`apps/web/playwright.config.ts` и зелёный job `e2e`. Работа дошла до `main` другим путём,
поэтому постановка отнесена к закрытым.

## Вытесненные

`вытесненные/hermes-e12-budget-ledger.md` — бюджетный ledger. Слитого pull request нет:
предмет перенесён в активную постановку `hermes-e15-budget-ledger-and-cache.md`.
В таблице поглощённых постановок эта строка отсутствовала, вердикт восстановлен по
`справочное/README-kagent-tasks.md`, где E15 описана как «линия A: бюджетный ledger».

## Справочное

`справочное/` — то, что заданиями не является: правила работы старой папки, протокол
воркера Hermes, аудит от 2026-08-10, разбор закрытого PR #1 и переписка агентов по
задачам B4, C3, C5.

## Куда ушла незакрытая работа

| Что | Куда |
|---|---|
| Этапы 0.9.2–0.9.5, ни разу не выполнявшиеся | `agents/hermes/inbox/отложенные-этапы/` |
| E14 — программа закрытия отложенных этапов | `agents/hermes/inbox/hermes-e14-program-deferred-stages.md` |
| E15 — бюджетный ledger и кэш | `agents/hermes/inbox/hermes-e15-budget-ledger-and-cache.md` |
| E16 — план распараллеливания | `agents/hermes/inbox/hermes-e16-parallel-tracks.md` |
| X1 — разбор закрытого PR #1 | `agents/antigravity/inbox/antigravity-x1-analyze-pr1.md` |
