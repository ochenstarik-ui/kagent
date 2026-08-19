# Отчёт: обновить зависимости

- **Задание:** `../inbox/2026-08-18-obnovlenie-zavisimostey.md`
- **Агент:** claude
- **Дата:** 2026-08-18
- **Ветка / коммиты:** `claude/zavisimosti-2026-08-18`, `5d7f8a5`

Изменения зависимостей вынесены в отдельную ветку и отдельный pull request; эта пара
«задание — отчёт» лежит в ветке `claude/aktualizaciya-2026-08-18`, чтобы pull request
с зависимостями содержал только лок-файлы и `package.json`.

## Что сделано

Подняты версии существующих зависимостей в пределах мажорных. Новых зависимостей не
добавлено, библиотеки не заменены.

**Node.** Все пять — в пределах уже объявленных диапазонов `^`, лицензии не менялись,
поскольку не менялись сами пакеты:

| Пакет | Было | Стало | Лицензия |
|---|---|---|---|
| `fastify` | 5.11.2 | 5.12.0 | MIT |
| `pg` | 8.22.0 | 8.23.0 | MIT |
| `@types/pg` (dev) | 8.20.3 | 8.23.1 | MIT |
| `tsx` (dev) | 4.23.5 | 4.23.12 | MIT |
| `eslint-config-next` (dev) | 16.3.0 | 16.3.1 | MIT |

**Rust.** 13 патч-версий в `services/gateway/Cargo.lock`: `futures-*` 0.3.33 → 0.3.34,
`http-body-util` 0.1.4 → 0.1.5, `js-sys` 0.3.103 → 0.3.104, `regex-automata` 0.4.17 →
0.4.18, `uuid` 1.24.0 → 1.24.1, `wasm-bindgen*` 0.2.126 → 0.2.127. Прямых зависимостей
в `Cargo.toml` не менялось.

**Побочный эффект `pnpm update`.** Команда подняла нижние границы диапазонов в трёх
`package.json` до фактически зафиксированных версий: например `fastify` `^5.0.0` →
`^5.12.0`, `typescript` `^5.6.0` → `^5.9.3`, `@types/node` `^22.0.0` → `^22.20.1`.
Мажорные версии те же; объявленный минимум теперь совпадает с тем, что реально
установлено. Если такое сужение диапазонов нежелательно, `package.json` откатываются
без отката лок-файла.

## Как проверено

Сначала снят базовый уровень **до** изменений, на неизменном лок-файле
(`git diff --stat pnpm-lock.yaml` — пусто):

```
format:check  PASS
lint          FAIL   ← падало до моих изменений
typecheck     PASS
```

После обновления:

```
$ pnpm format:check
Scope: 3 of 4 workspace projects        (без ошибок)

$ pnpm typecheck
packages/contracts typecheck: Done
apps/web typecheck: Done
services/control-plane typecheck: Done

$ pnpm test
packages/contracts: tests 10, pass 10, fail 0
services/control-plane (vitest 2.1.9): Test Files 4 passed | 2 skipped (6)
                                       Tests 16 passed | 9 skipped (25)

$ cargo fmt --manifest-path services/gateway/Cargo.toml --check
(без вывода, код возврата 0)

$ cargo clippy --manifest-path services/gateway/Cargo.toml --all-targets -- -D warnings
Finished `dev` profile [unoptimized + debuginfo] target(s) in 1m 12s
```

## Что не сделано

**Три команды из критерия приёмки локально не запускались или не прошли. Ни одна из
причин не связана с обновлением.**

1. **`pnpm lint` — падает, падал и до обновления.** Причина найдена: `apps/web`
   объявляет `eslint: ^10.8.1`, а плагины, которые тянет `eslint-config-next` 16.x,
   поддерживают eslint не выше 9:

   ```
   apps/web
   └─┬ eslint-config-next 16.3.1
     ├─┬ eslint-plugin-import 2.32.0
     │ └── ✕ unmet peer eslint@"... || ^9": found 10.8.1
     ├─┬ eslint-plugin-jsx-a11y 6.10.2
     │ └── ✕ unmet peer eslint@"... || ^9": found 10.8.1
     └─┬ eslint-plugin-react 7.37.5
       └── ✕ unmet peer eslint@"... || ^9.7": found 10.8.1
   ```

   Само падение выглядит так:

   ```
   apps/web lint: `next lint` is deprecated and will be removed in Next.js 16.
   apps/web lint: Invalid Options:
   apps/web lint: - Unknown options: useEslintrc, extensions, resolvePluginsRelativeTo, ...
   apps/web lint: Failed
   ```

   Починка не входит в границы задачи: это либо понижение `eslint` до `^9` — то есть
   решение по зависимости, требующее обоснования по §4, либо переход с `next lint` на
   ESLint CLI с flat config — то есть правка кода. **Предлагаю отдельную задачу.**

2. **`pnpm build` — не проверялось.** `next build` с `output: standalone` падает на
   `EPERM: operation not permitted, symlink`. Проверено отдельно: `mklink` возвращает
   «Недостаточно привилегий для выполнения этой операции» — у учётной записи нет права
   создавать символические ссылки. К версиям пакетов отношения не имеет; в
   непрерывной интеграции на ubuntu команда выполняется.

3. **`cargo test` — не проверялось.** Не запускается ни одним установленным toolchain:
   активный `stable-x86_64-pc-windows-gnu` падает на `error calling dlltool
   'dlltool.exe': program not found`, а `stable-x86_64-pc-windows-msvc` — на линковке,
   потому что `link.exe` разрешается в coreutils из состава git
   (`...\hermes\git\usr\bin\link.exe`), а Visual Studio Build Tools не установлены.
   `cargo clippy --all-targets` при этом проходит: он проверяет и тестовые цели, но не
   линкует.

**Подтверждение прогоном.** [PR #37](https://github.com/ochenstarik-ui/kagent/pull/37),
прогон [32238188346](https://github.com/ochenstarik-ui/kagent/actions/runs/32238188346):
32 проверки `pass`, 2 `skipping`, красных нет. Тем самым `pnpm build` и `cargo test`,
не запускавшиеся локально, подтверждены на ubuntu.

`pnpm lint` остаётся неподтверждённым и красным: непрерывная интеграция его не
запускает. Зелёный прогон этого не закрывает — и ровно поэтому дефект дожил до сегодня.

## Замечено рядом

1. **Непрерывная интеграция не запускает `pnpm lint` и `pnpm format:check`** — job `node`
   выполняет только `pnpm typecheck`, `pnpm test`, `pnpm build`. Поэтому дефект из
   пункта 1 жил в `main` незамеченным при зелёной сборке. Предложение отдельной задачи —
   в отчёте о состоянии.
2. **`apps/web` держит `next: ^15.5.23` и `eslint-config-next: ^16.3.1`** — мажорные
   версии разъехались. Пакет конфигурации на поколение старше самого Next.
3. **Мажорные подъёмы, оставшиеся несделанными** (в границы задачи не входят, каждый
   требует правки кода и отдельного решения):

   | Пакет | Текущая | Доступная |
   |---|---|---|
   | `typescript` | 5.9.3 | 7.0.2 |
   | `vitest` | 2.1.9 | 4.1.10 |
   | `next` | 15.5.22 | 16.3.1 |
   | `fast-jwt` | 5.0.6 | 6.3.2 |
   | `nanoid` | 5.1.16 | 6.0.1 |
   | `@types/node` | 22.20.1 / 24.13.3 | 26.2.0 |

   Отдельно отмечу `@types/node`: рабочее пространство держит три разные мажорные
   версии (22 в `contracts` и `control-plane`, 24 в `web`), при `engines.node >= 22`.

## Вопросы к приёмке

Сужение диапазонов в `package.json` (побочный эффект `pnpm update`) — оставить или
откатить, сохранив только лок-файлы?
