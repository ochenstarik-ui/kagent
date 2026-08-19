## B4 repair after independent review

Оба blocking-пункта исправлены отдельным commit `901803633347120ef1358f720bf41e7ff739337d`.

1. **Package exports → source mapping**: при наличии `dist/index.js` entry point теперь выбирается как `packages/contracts/src/index.ts`; реэкспорты `artifact.ts`, `event.ts`, `ids.ts`, `task.ts` транзитивно достижимы. Из contracts недостижимым остаётся только `reasoning.ts`.
2. **Environment check scope**: обратная проверка `code-read but undocumented` удалена из B4. Она больше не добавляет семь посторонних находок.

Проверено после push:

```text
python -m pytest tests/unit/test_drift_check.py -q
9 passed

ruff check ...
All checks passed!

Два последовательных drift-прогона:
exit1=1 exit2=1
outputs=byte-identical
sha256=5a28c63f0729a581797f1676f8b1c7b91a9fe4828549b15615f902aa0d96c660

DRIFT CHECK FAILED
  - packages/contracts/src/reasoning.ts
  - services/auth/src/totp.py
  - services/control-plane/src/db.ts
  - services/nats/src/events.py
```

CI run: https://github.com/ochenstarik-ui/kagent/actions/runs/31318251911 — node/python/rust PASS.

PR не сливался. Прошу повторно проверить два исправленных пункта.
