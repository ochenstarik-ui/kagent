# Changelog

Все заметные изменения KAgent фиксируются в этом файле.

Формат основан на Keep a Changelog. Проект следует Semantic Versioning после первого стабильного релиза.

## [Unreleased]

### Added

- Архитектурное решение Capability-first Reasoning Engine с бюджетным Router, режимами Economy/Balanced/Critical и оценкой по стоимости успешной задачи.
- Чистая monorepo-структура KAgent.
- Базовый Web-клиент.
- Каркас TypeScript Control Plane.
- Каркас Rust Gateway.
- Пакет versioned-контрактов.
- Docker Compose с PostgreSQL, NATS JetStream и MinIO.
- Архитектурные документы, ADR и threat model.
- Начальный тестовый и CI-каркас.
- Подключение ограничителя частоты запросов на gateway с настройкой через окружение.
- Job `python` в непрерывной интеграции.
- Модульные тесты control-plane и gateway.

### Changed

- Полное ТЗ приведено к разработке с чистого листа без этапа миграции legacy-кода.

### Fixed

- Ошибка компиляции в `get_request_id`.
- Падение control-plane при старте из-за незаявленной зависимости логгера.
- Неработающее хеширование паролей из-за `require` в ESM-модуле.
- Отсутствие `pnpm-lock.yaml`.
- Пакет control-plane, выпадавший из корневой проверки типов.
