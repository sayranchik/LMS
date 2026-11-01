# Система управління навчанням (LMS)

Django-проєкт: курси → модулі → уроки → завдання → оцінки, три ролі (студент, викладач, адміністратор).

## Запуск

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations accounts courses assignments
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
python manage.py test        # автотести
```

Суперкористувач має роль адміністратора LMS. Викладачів та додаткових адміністраторів
призначають в `/admin/` (поле «Роль»). Реєстрація на сайті завжди створює студента.

## Права доступу

| Дія | Студент | Викладач | Адміністратор |
|---|---|---|---|
| Перегляд курсів і уроків | + | + | + |
| Створення/редагування/видалення курсів, модулів, уроків | − | − | + |
| Здача завдань | + | − | − |
| Створення завдань | − | + | + |
| Виставлення оцінок | − | + | + (також редагування всіх) |
| Перегляд оцінок | свої | усі | усі |

## Структура

- `accounts` — модель `User` з полем `role`, реєстрація, вхід, профіль
- `courses` — `Course`, `Module`, `Lesson` (текст, зображення, відео), `Announcement`, `Event`, головна сторінка
- `assignments` — `Assignment`, `Submission` (відповідь, файл, оцінка, коментар)
- `templates/` — Bootstrap 5 (CDN), адаптивна верстка

Оголошення та події наповнюються через `/admin/`. Сертифікати не реалізовано (необов'язкова вимога).

## GitFlow

Гілки: `main` (релізи), `develop` (інтеграція), `feature/*`, `release/*`, `hotfix/*`.

```bash
git init && git add . && git commit -m "Initial LMS skeleton"
git branch -M main && git checkout -b develop
git checkout -b feature/backend-models develop   # робота над функціоналом
# після завершення: Pull Request feature/* -> develop, далі release/* -> main
```
