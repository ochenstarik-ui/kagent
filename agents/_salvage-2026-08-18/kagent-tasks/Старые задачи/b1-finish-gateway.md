Правила работы — `AGENTS.md` в корне репозитория, копия в
`C:\Users\Ochenstarik\kagent-tasks\AGENTS.md`.

Рабочий каталог: `C:\Users\Ochenstarik\kagent\.worktrees\t_02a18136`
Ветка: `wt/kagent-090-green-trunk`, PR #3, вершина `5c86d8b`

## На чём остановились

В рабочем каталоге лежит **незакоммиченная** работа: откат HTTP-клиента с `reqwest` на
`hyper` выполнен, но не зафиксирован и не отправлен.

```
 M services/gateway/Cargo.toml     reqwest и обе секции target.cfg удалены,
                                   hyper, hyper-util, http-body-util, axum-extra возвращены
 M services/gateway/Cargo.lock     пересобран
 M services/gateway/src/main.rs    +37 −21, проксирование вернулось на
                                   hyper_util::client::legacy::Client
 M apps/web/next-env.d.ts          порождённый файл, в коммит не включать
 M apps/web/tsconfig.json          изменён сборкой Next.js, в коммит не включать
```

Пока это не закоммичено, любая чистка каталога уничтожает работу. Первый шаг — зафиксировать.

Остальное из постановки не сделано: параметры ограничителя частоты по-прежнему захардкожены,
заголовка `Retry-After` нет, тестов в `main.rs` по-прежнему два, `CHANGELOG.md` не тронут.

## 1. Зафиксировать откат

- проверить, что сборка проходит: `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`,
  `cargo test` с `--manifest-path services/gateway/Cargo.toml`;
- закоммитить **только** три файла gateway: `Cargo.toml`, `Cargo.lock`, `src/main.rs`;
- `apps/web/next-env.d.ts` и `apps/web/tsconfig.json` не коммитить: первый порождается
  Next.js, второй изменён им же. Вернуть их в исходное состояние;
- сообщение коммита: `revert(gateway): return HTTP client to hyper, drop reqwest`.

## 2. Параметры ограничителя частоты

Сейчас в `main.rs`:

```rust
let limiter = RateLimiter::new(60, 100);
```

- читать из окружения `GATEWAY_RATE_LIMIT_WINDOW_SECONDS` (по умолчанию 60) и
  `GATEWAY_RATE_LIMIT_MAX_REQUESTS` (по умолчанию 120);
- значения по умолчанию — константы рядом с объявлением структуры; при некорректном вводе
  использовать значение по умолчанию, а не падать;
- добавить обе переменные в `.env.example` рядом с прочими настройками gateway;
- в ответ `429` добавить заголовок `Retry-After` со значением остатка текущего окна в
  секундах.

## 3. Тесты gateway

В файле два теста, оба про разбор порта, оба существовали до этой ветки. Добавить:

`get_request_id`:

- заголовок отсутствует — возвращается сгенерированный UUID;
- заголовок пустой — возвращается сгенерированный UUID;
- заголовок задан — значение возвращается без изменений.

Ограничитель частоты:

- запрос в пределах лимита проходит;
- запрос сверх лимита получает `429` с заголовком `Retry-After`;
- после истечения окна счётчик сбрасывается;
- запись клиента с истёкшим окном вытесняется фоновой очисткой, карта не растёт
  неограниченно.

Тесты пишутся по описанному поведению, а не подгоняются под текущий код. Нашёл расхождение —
не правь тест, опиши в отчёте.

## 4. Changelog

В `CHANGELOG.md`, раздел `[Unreleased]`:

- в `Added` — ограничитель частоты запросов на gateway с настройкой через окружение; job
  `python` в непрерывной интеграции; модульные тесты control-plane и gateway;
- новый раздел `Fixed` — ошибка компиляции в `get_request_id`; падение control-plane при
  старте из-за незаявленной зависимости логгера; неработающее хеширование паролей из-за
  `require` в ESM-модуле; отсутствие `pnpm-lock.yaml`; пакет control-plane, выпадавший из
  корневой проверки типов.

Пункты roadmap не отмечать.

## Критерий приёмки

```bash
cargo fmt --manifest-path services/gateway/Cargo.toml --check
cargo clippy --manifest-path services/gateway/Cargo.toml --all-targets -- -D warnings
cargo test --manifest-path services/gateway/Cargo.toml
```

`cargo test` показывает не менее восьми тестов. Вывод приложить.

После пуша дождаться прогона на PR #3 и приложить ссылку на прогон, где зелёные все три
job: `node`, `rust`, `python`. Проверка засчитывается по выводу, не по рассуждению.

## Границы

Только `services/gateway/*`, `.env.example`, `CHANGELOG.md`. Ничего в control-plane, в
конфигурации CI и в остальной документации.

Если бюджет заканчивается — доведи текущий пункт, закоммить, опиши остаток, остановись.
Пункты 1–4 сдаются по отдельности.
