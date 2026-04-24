# Migrate Test Suite From Unittest To Pytest

- Название: `migrate test suite from unittest to pytest`
- Slug: `2026-04-23-migrate-tests-to-pytest`
- Ответственный: `Codex`
- Создан: `2026-04-23`
- Обновлен: `2026-04-23 15:21`
- Общий статус: `done`

## Цель

Перевести тестовый контур `application-agent` с `unittest` на `pytest` так, чтобы:

- тесты запускались через единый `pytest` entrypoint;
- тестовый код больше не зависел от `unittest.TestCase` и `unittest.main()`;
- документация и project config явно описывали новый способ запуска;
- итоговая валидация проходила через `pytest`, а не через `python -m unittest ...`.

## Контекст

На `2026-04-23` тестовый набор в `./tooling/application-agent/tests` почти целиком написан в стиле `unittest`:

- все найденные test-модули используют `import unittest`;
- test classes наследуются от `unittest.TestCase`;
- в файлах присутствуют `self.assert*` и `self.assertRaisesRegex(...)`;
- внизу файлов есть `if __name__ == "__main__": unittest.main()`.

При этом явной pytest-настройки в репозитории пока нет:

- в `pyproject.toml` нет зависимостей или секций конфигурации для `pytest`;
- в текущем окружении команда `python -m pytest --version` завершается ошибкой `No module named pytest`.

Дополнительно проверено, что в текущем тестовом наборе не обнаружены усложняющие migration-паттерны уровня `setUp`, `tearDown`, `setUpClass`, `tearDownClass`, `subTest`, skip-декораторов или иных `unittest`-специфичных механизмов, которые потребовали бы отдельного redesign.

## Границы

### Входит в scope

- добавить в проект dependency/config contract для `pytest`;
- перевести test files в `tests/` с `unittest.TestCase` на pytest-style tests;
- заменить `self.assert*`/`assertRaisesRegex` на idiomatic `assert`/`pytest.raises`;
- убрать `unittest.main()` хвосты;
- обновить README и validation commands под `pytest`.

### Не входит в scope

- изменение production-кода вне необходимости для совместимости запуска тестов;
- внедрение сторонних pytest-плагинов, если они не нужны для базовой миграции;
- крупная реорганизация структуры `tests/` сверх необходимого для перехода;
- параллельная миграция на другой dependency manager или CI system.

## Допущения

- базового `pytest` достаточно, без обязательной зависимости на `pytest-mock`, `pytest-xdist` и другие плагины;
- текущая структура test-модулей совместима с поэтапной механической миграцией без переписывания тестовой логики;
- `sys.path.insert(...)` в тестах можно оставить, если после переключения на `pytest` не появится более чистый repo-native способ запуска.

## Риски и неизвестные

- часть тестов может неявно зависеть от особенностей lifecycle `unittest.TestCase`, даже без явных `setUp/tearDown`;
- после замены assert-стиля могут всплыть скрытые различия в текстах исключений и диагностике;
- если пользователь не установит `pytest` в рабочее окружение, я не смогу полноценно провалидировать финальную миграцию локальным запуском.

## Внешние точки касания

- нет

## Этапы

### M1. Baseline Inventory And Pytest Migration Contract

- Статус: `done`
- Цель:
  - зафиксировать текущий footprint `unittest` и определить минимальный безопасный объём миграции;
  - подтвердить, какие предварительные действия требуются вне репозитория.
- Артефакты:
  - dedicated plan;
  - inventory текущих test patterns;
  - список внешних prerequisites.
- Критерии приемки:
  - в плане явно отражено, что тесты сейчас основаны на `unittest.TestCase`;
  - зафиксировано отсутствие `pytest` в текущем окружении;
  - определено, что перед валидацией нужен установленный `pytest`.
- Команды валидации:
  - `rg -n "unittest|TestCase|assertRaises|assertEqual|pytest" tests pyproject.toml README.md`
  - `rg -n "setUpClass|tearDownClass|setUp\(|tearDown\(|subTest|skipTest|@unittest" tests`
  - `python -m pytest --version`
- Заметки / находки:
  - сложных `unittest` lifecycle hooks в `tests/` не найдено;
  - рабочий набор миграции выглядит как straightforward suite-wide refactor.

### M2. Project Pytest Contract

- Статус: `done`
- Цель:
  - добавить в проект минимально достаточный dependency/config contract для запуска тестов через `pytest`.
- Артефакты:
  - обновлённый `pyproject.toml`;
  - при необходимости README/test run instructions.
- Критерии приемки:
  - репозиторий явно декларирует использование `pytest`;
  - команда запуска тестов в документации и плане использует `pytest`;
  - не добавлены лишние плагины без необходимости.
- Команды валидации:
  - `python -m pytest --version`
  - `Get-Content -Raw pyproject.toml`
  - `rg -n "pytest" pyproject.toml README.md`
- Заметки / находки:
  - в `pyproject.toml` добавлены `project.optional-dependencies.dev = ["pytest>=9,<10"]`;
  - pytest-конфигурация закреплена в `pyproject.toml` через `testpaths = ["tests"]`;
  - для этого workspace дополнительно зафиксирован `addopts = "-p no:cacheprovider"`, чтобы повторные запуски не создавали проблемный pytest cache.

### M3. Test Suite Refactor From Unittest Style To Pytest Style

- Статус: `done`
- Цель:
  - переписать test modules на pytest-style functions/classes без `unittest.TestCase`.
- Артефакты:
  - обновлённые файлы в `tests/`;
  - удалённые `unittest.main()` блоки;
  - assert/exception checks в pytest-стиле.
- Критерии приемки:
  - в `tests/` больше нет импортов `unittest` и наследования от `unittest.TestCase`;
  - проверки исключений используют `pytest.raises`;
  - tests collect и исполняются через `pytest`.
- Команды валидации:
  - `rg -n "import unittest|unittest\\.main|TestCase|self\\.assert" tests`
  - `python -m pytest tests`
- Заметки / находки:
  - весь suite в `tests/` переведён на pytest-style classes/asserts;
  - наследование от `unittest.TestCase`, `self.assert*`, `assertRaisesRegex` и `unittest.main()` удалены;
  - для надёжной миграции без порчи non-ASCII текста test-файлы были пересобраны из `git`-версий через AST-трансформацию.

### M4. Docs Sync And Full Validation On Pytest

- Статус: `done`
- Цель:
  - синхронизировать docs и подтвердить, что весь suite стабильно проходит уже на `pytest`.
- Артефакты:
  - обновлённый `README.md`;
  - финальная validation запись в плане.
- Критерии приемки:
  - README описывает pytest-based test run;
  - полный тестовый прогон проходит через `pytest`;
  - план фиксирует итоговую validation baseline и остаточные риски.
- Команды валидации:
  - `python -m pytest tests`
  - `rg -n "unittest|pytest" README.md plans\\2026-04-23-migrate-tests-to-pytest.md`
- Заметки / находки:
  - `README.md` теперь явно показывает pytest-based test run через `python -m pytest tests`;
  - полный прогон проходит: `74 passed`;
  - от первой попытки запуска остались три каталога `pytest-cache-files-*`, которые не удалось удалить из-за `Access denied`; на новые прогоны это больше не влияет после отключения cacheprovider.

## Журнал решений

- `2026-04-23 15:10` — Migration будет делаться как реальный перевод тестового кода на pytest-style, а не как простой запуск существующих `unittest.TestCase` через pytest collector. — Причина: пользователь попросил перевести тестирование в проекте с `unittest` на `pytest`, а не просто сменить test runner. — Это означает изменение test code, config и docs.
- `2026-04-23 15:10` — Внешним prerequisite считаем установленный в окружении `pytest`. — Причина: сейчас его нет, а без него нельзя выполнить целевую валидацию. — До установки окружение остаётся blocker для M2-M4 validation.
- `2026-04-23 15:18` — Миграция тестов выполняется через структурную AST-трансформацию от исходных `git`-версий test-файлов, а не через повторные regex-замены по уже изменённым файлам. — Причина: первая пакетная правка через PowerShell повредила non-ASCII строки в test-литералах. — Это сохранило семантику тестов и позволило безопасно перевести suite на pytest-style без ручного восстановления каждой строки.
- `2026-04-23 15:20` — В pytest-конфигурации отключён built-in cacheprovider через `addopts = "-p no:cacheprovider"`. — Причина: в этом workspace первая попытка запуска создавала проблемные `pytest-cache-files-*` каталоги и warnings по доступу. — Это стабилизирует повторные прогоны и убирает шум из валидации.

## Журнал прогресса

- `2026-04-23 15:10` — Создан dedicated plan, собран baseline по `unittest` footprint и подтверждено отсутствие `pytest` в окружении (`python -m pytest --version` -> `No module named pytest`). — Статус: `blocked`.
- `2026-04-23 15:12` — Завершён M2: в `pyproject.toml` добавлен pytest dependency/config contract. — Валидация: `python -m pytest --version` -> `pytest 9.0.3`, `rg -n "pytest" pyproject.toml` показывает новый dev dependency и pytest config. — Статус: `in_progress`.
- `2026-04-23 15:18` — Завершён M3: все test-модули в `tests/` переписаны на pytest-style и больше не используют `unittest.TestCase`, `self.assert*` и `unittest.main()`. — Валидация: `rg -n "self\.assert|assertRaisesRegex|import unittest|unittest\.main|TestCase" tests` не находит совпадений. — Статус: `in_progress`.
- `2026-04-23 15:20` — Первый прогон `python -m pytest tests` прошёл успешно: `74 passed`; после этого в конфиг добавлено отключение cacheprovider для устранения warnings в этом workspace. — Статус: `in_progress`.
- `2026-04-23 15:21` — Завершён M4: `README.md` синхронизирован под pytest, повторный full run даёт `74 passed in 1.62s` без pytest cache warnings. — Остаток: в repo root остались недоступные для удаления каталоги `pytest-cache-files-*` от самой первой попытки запуска; `git status` по-прежнему предупреждает о них. — Статус: `done`.

## Текущее состояние

- Текущий milestone: `completed`
- Текущий статус: `done`
- Следующий шаг: `При необходимости отдельно решить судьбу оставшихся недоступных каталогов pytest-cache-files-* вне рамок этой миграции.`
- Активные блокеры:
  - нет
- Открытые вопросы:
  - нет

## Итог завершения

Поставлено:

- `pytest` зафиксирован как проектный test runner через `pyproject.toml`;
- весь suite в `tests/` переведён с `unittest`-style на pytest-style;
- `README.md` дополнен явной командой запуска `python -m pytest tests`.

Провалидировано:

- `python -m pytest --version` -> `pytest 9.0.3`
- `rg -n "self\.assert|assertRaisesRegex|import unittest|unittest\.main|TestCase" tests` -> без совпадений
- `python -m pytest tests` -> `74 passed in 1.62s`

Follow-up вне этого плана:

- при необходимости отдельно удалить или расследовать оставшиеся недоступные каталоги `pytest-cache-files-*`, созданные первой неудачной попыткой работы cacheprovider.

Остаточный риск:

- функционально миграция завершена, но рабочее дерево всё ещё получает warnings от `git status`, пока в repo root присутствуют недоступные `pytest-cache-files-*` каталоги.
