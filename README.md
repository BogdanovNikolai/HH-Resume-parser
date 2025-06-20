# Документация проекта

## Оглавление

- [app.py]#app_py
- [generate_docs.py]#generate_docs_py
- [main.py]#main_py
- [merge_files.py]#merge_files_py
- [progress.py]#progress_py
- [test.py]#test_py
- [config\config.py]#config\config_py
- [config\__init__.py]#config\__init___py
- [database\base.py]#database\base_py
- [database\models.py]#database\models_py
- [database\repository.py]#database\repository_py
- [database\session.py]#database\session_py
- [database\__init__.py]#database\__init___py
- [data_manager\exporters.py]#data_manager\exporters_py
- [data_manager\manager.py]#data_manager\manager_py
- [data_manager\merge_files.py]#data_manager\merge_files_py
- [data_manager\resume_processor.py]#data_manager\resume_processor_py
- [data_manager\search_engine.py]#data_manager\search_engine_py
- [data_manager\task_tracker.py]#data_manager\task_tracker_py
- [data_manager\__init__.py]#data_manager\__init___py
- [hh\api.py]#hh\api_py
- [hh\areas.py]#hh\areas_py
- [hh\save_areas.py]#hh\save_areas_py
- [postgres_client_bak\__init__.py]#postgres_client_bak\__init___py
- [redis_client\client.py]#redis_client\client_py
- [redis_client\__init__.py]#redis_client\__init___py
- [utils\ai_evaluator.py]#utils\ai_evaluator_py
- [utils\excel_writer.py]#utils\excel_writer_py
- [utils\token_executor.py]#utils\token_executor_py

---

## app.py
<a name='app_py'></a>
Модуль `app` содержит основное Flask-приложение для поиска, обработки и экспорта резюме из HeadHunter.

Endpoints:
    - /vacancy/<vacancy_id>/start — запуск задачи по поиску резюме по вакансии.
    - /progress/<task_id> — получение прогресса фоновой задачи.
    - /download/<task_id> — скачивание результатов задачи.
    - /vacancy/<vacancy_id>/export_new — экспорт новых откликов по вакансии.
    - /export (POST) — запуск поиска резюме по ключевым словам.
    - /vacancies — список вакансий компании.
    - / — главная страница с формой поиска.
    - /api/resume-limit — получение лимита на загрузку резюме.

Functions:
    start_task: запуск задачи поиска резюме по ID вакансии.
    get_task_progress: получение текущего прогресса задачи.
    download_file: скачивание файла с результатами задачи.
    export_new_responses: экспорт новых откликов по вакансии.
    export_resumes: запуск фоновой задачи поиска резюме по ключевым словам.
    vacancies: отображение списка вакансий компании.
    index: главная страница приложения.
    get_limit: получение лимита на загрузку резюме.

---

## generate_docs.py
<a name='generate_docs_py'></a>
Скрипт для генерации README.md на основе заголовочных докстрингов всех .py файлов в проекте.

Игнорируемые директории:
    - .venv
    - __pycache__
    - .git
    - .env
    - migrations (если есть)

---

## main.py
<a name='main_py'></a>
Файл `main.py` — точка входа в приложение.

Запускает Flask-приложение из модуля `app`.

Functions:
    Нет функций верхнего уровня.

---

## merge_files.py
<a name='merge_files_py'></a>
Нет описания.

---

## progress.py
<a name='progress_py'></a>
Нет описания.

---

## test.py
<a name='test_py'></a>
Нет описания.

---

## config\config.py
<a name='config\config_py'></a>
Модуль конфигурации проекта.

Содержит класс Config, предоставляющий доступ к настройкам приложения через переменные окружения.
Поддерживает конфигурацию Redis, PostgreSQL, API-ключей, логгирования, таймаутов и других параметров.

Classes:
    Config: основной класс конфигурации с атрибутами и методами для получения и проверки настроек.

Functions:
    Нет функций верхнего уровня. Все методы реализованы как @classmethod внутри класса Config.

---

## config\__init__.py
<a name='config\__init___py'></a>
Пакет конфигурации приложения.

Содержит инициализацию основного класса конфигурации и глобального логгера.
Экспортирует:
    - app_config: экземпляр класса Config с настройками приложения.
    - log: глобальный объект логгера.

---

## database\base.py
<a name='database\base_py'></a>
Модуль `base` содержит базовый класс для всех моделей SQLAlchemy.

Этот модуль используется Alembic для построения миграций. Все модели приложения должны наследоваться от Base.

Classes:
    Base: декларативная база SQLAlchemy, используемая для создания метаданных и миграций.

---

## database\models.py
<a name='database\models_py'></a>
Модуль `models` содержит SQLAlchemy-модели для работы с базой данных PostgreSQL.

Эти модели используются как для ORM-операций, так и для генерации миграций через Alembic.

Classes:
    Resume: модель для хранения данных о резюме.
    Task: модель для отслеживания фоновых задач и их прогресса.

---

## database\repository.py
<a name='database\repository_py'></a>
Модуль `repository` содержит класс DatabaseRepository — реализацию репозитория для работы с БД через SQLAlchemy.

Класс предоставляет методы для сохранения, загрузки и обновления данных о резюме и задачах.

Classes:
    DatabaseRepository: класс, предоставляющий CRUD-операции над данными.

---

## database\session.py
<a name='database\session_py'></a>
Модуль `session` содержит настройки подключения к PostgreSQL и фабрику сессий SQLAlchemy.

Этот модуль обеспечивает централизованный доступ к базе данных через движок (engine) и фабрику сессий.
Также предоставляет зависимость `get_db()` для интеграции вне Flask-приложений.

Provides:
    engine: движок SQLAlchemy для работы с PostgreSQL.
    SessionLocal: фабрика сессий.
    get_db(): генератор сессии БД для использования вне Flask.

---

## database\__init__.py
<a name='database\__init___py'></a>
Пакет `database` содержит всё, что связано с работой приложения с PostgreSQL через SQLAlchemy.

Модули:
    - base: базовый класс для всех моделей.
    - models: ORM-модели таблиц.
    - repository: реализация репозиториев для работы с данными.
    - session: настройки подключения к БД и фабрика сессий.

Exports:
    init_db: функция для инициализации таблиц в БД.

---

## data_manager\exporters.py
<a name='data_manager\exporters_py'></a>
Модуль `exporters` содержит класс Exporter для экспорта резюме в различные форматы:
- Excel (.xlsx) — основной формат для пользователя.
- JSON (.json) — для API и внутренних нужд.

Classes:
    Exporter: утилитный класс для сохранения данных в различных форматах.

Functions:
    Нет функций верхнего уровня.

---

## data_manager\manager.py
<a name='data_manager\manager_py'></a>
Модуль `manager` содержит основную логику работы с данными приложения.

Класс DataManager отвечает за:
- запуск фоновых задач по поиску резюме,
- обработку и оценку найденных резюме,
- взаимодействие с БД,
- экспорт результатов,
- отслеживание прогресса задач.

Classes:
    DataManager: основной класс, управляющий всей логикой обработки данных.

Functions:
    Нет функций верхнего уровня.

---

## data_manager\merge_files.py
<a name='data_manager\merge_files_py'></a>
Нет описания.

---

## data_manager\resume_processor.py
<a name='data_manager\resume_processor_py'></a>
Модуль `resume_processor` содержит класс ResumeProcessor — утилиту для обработки и форматирования
сырых данных о резюме, полученных из HeadHunter API.

Classes:
    ResumeProcessor: класс для преобразования и подготовки данных о резюме к дальнейшей обработке и хранению.

Functions:
    Нет функций верхнего уровня.

---

## data_manager\search_engine.py
<a name='data_manager\search_engine_py'></a>
Нет описания.

---

## data_manager\task_tracker.py
<a name='data_manager\task_tracker_py'></a>
Модуль `task_tracker` содержит класс TaskTracker — утилиту для отслеживания прогресса фоновых задач.

Класс использует Redis для хранения состояния задач:
- шаг выполнения
- статус задачи
- количество обработанных резюме
- имя выходного файла

Classes:
    TaskTracker: класс для управления и отслеживания прогресса задач.

Functions:
    Нет функций верхнего уровня.

---

## data_manager\__init__.py
<a name='data_manager\__init___py'></a>
Пакет `data_manager` содержит логику работы с данными приложения.

Основные компоненты:
    - DataManager: основной класс управления процессом поиска и обработки резюме.
    - ResumeProcessor: класс для форматирования и подготовки данных резюме.
    - SearchEngine: движок поиска резюме через HeadHunter API.
    - TaskTracker: отслеживание прогресса фоновых задач.
    - Exporter: экспорт результатов в Excel или JSON.

Exports:
    data_manager (DataManager): глобальный экземпляр менеджера данных.
    DataManager: класс для управления данными.
    ResumeProcessor: класс для обработки резюме.
    SearchEngine: класс поискового движка.
    TaskTracker: класс для отслеживания задач.
    Exporter: класс для экспорта данных.

---

## hh\api.py
<a name='hh\api_py'></a>
Нет описания.

---

## hh\areas.py
<a name='hh\areas_py'></a>
Нет описания.

---

## hh\save_areas.py
<a name='hh\save_areas_py'></a>
Нет описания.

---

## postgres_client_bak\__init__.py
<a name='postgres_client_bak\__init___py'></a>
Нет описания.

---

## redis_client\client.py
<a name='redis_client\client_py'></a>
Модуль `client` содержит реализацию клиента Redis для хранения прогресса фоновых задач.

Класс RedisClient предоставляет методы для:
- инициализации и подключения к Redis,
- сохранения и обновления прогресса задачи,
- получения и удаления данных о задаче.

Classes:
    RedisClient: клиент Redis для работы с данными прогресса задач.

---

## redis_client\__init__.py
<a name='redis_client\__init___py'></a>
Пакет `redis_client` предоставляет клиентский интерфейс для работы с Redis.

Содержит:
    - RedisClient: класс для взаимодействия с Redis.
    - redis_client: глобальный экземпляр клиента Redis.

Exports:
    redis_client: готовый к использованию экземпляр RedisClient.

---

## utils\ai_evaluator.py
<a name='utils\ai_evaluator_py'></a>
Модуль `ai_evaluator` содержит утилиты для оценки соответствия кандидата вакансии с помощью AI.

Функция `evaluate_candidate_match` использует API DeepSeek для анализа текста опыта работы кандидата
и описания вакансии, возвращая процент соответствия и краткое объяснение.

Functions:
    evaluate_candidate_match: оценивает соответствие кандидата вакансии через AI.

---

## utils\excel_writer.py
<a name='utils\excel_writer_py'></a>
Модуль `excel_writer` содержит утилиты для подготовки данных о резюме и сохранения их в формате Excel (.xlsx).

Основные возможности:
- безопасное извлечение вложенных данных через `safe_get`,
- подготовка данных о резюме для отображения,
- запись результатов в Excel с поддержкой AI-оценки соответствия.

Functions:
    safe_get: безопасно извлекает значение по цепочке ключей.
    prepare_resume_data: преобразует raw данные резюме в удобный формат.
    save_resumes_to_excel: сохраняет список резюме в Excel, с возможностью AI-анализа.

---

## utils\token_executor.py
<a name='utils\token_executor_py'></a>
Модуль `token_executor` содержит утилиты для выполнения функций с токенами доступа.

Основная функция:
    execute_with_token: выполняет переданную функцию с первым подходящим токеном из конфигурации.

---

