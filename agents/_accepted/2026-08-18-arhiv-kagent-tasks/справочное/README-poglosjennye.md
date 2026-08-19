# Поглощённые постановки

Эти задания **не выполнялись как таковые**: их предмет закрыла другая работа. Лежат
отдельно от выполненных, чтобы «сделано» означало ровно сделанное.

| Файл | Чем поглощено |
|---|---|
| `a8-revert-http-client.md` | целиком вошло в `a9-close-0.9.0.md` |
| `b3-measurability-wire-ci.md` | переписано как `b5`, затем выполнено в PR #6 |
| `b5-wire-measurability-ci.md` | выполнено в PR #6 вместе с переписанной проверкой дрейфа |
| `antigravity-p4-rework-vertical.md` | доработка вертикали вошла в PR #17 |
| `antigravity-p5-single-workspace-git-contract.md` | не принята, вытеснена `p8` |
| `antigravity-p6-model-loop-correctness.md` | не принята, вытеснена `p9` |
| `antigravity-p7-e2e-delivery.md` | не принята, вытеснена `p10` |
| `antigravity-d2-persist-totp-state.md` | не принята, переписана как `d4` |
| `antigravity-d3-totp-recovery-codes.md` | не принята, переписана как `d5` |
| `hermes-e5-python-test-collection-baseline.md` | предмет исчез: файл удалён чужой задачей, остаток покрыт `e6` |

Половина этого списка — цена двух ошибок в управлении очередью: параллельный запуск задач с
предусловием и вход в чужую область. Оба правила теперь записаны в `AGENTS.md`.
