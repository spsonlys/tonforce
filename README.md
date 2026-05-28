# TonForce Blog Automation

Автоматическая сборка блога из Markdown-постов, созданных через Decap CMS (`tonforce.app/admin/`).

## Как это работает

1. Вы создаёте пост через админку `tonforce.app/admin/`
2. Decap CMS сохраняет пост как Markdown-файл в `blog/posts/`, `en/blog/posts/` или `ua/blog/posts/`
3. GitHub Actions автоматически:
   - Конвертирует Markdown → HTML по шаблону, идентичному существующим постам
   - Обновляет главную блога (`blog/index.html`) — добавляет карточку нового поста
   - Обновляет RSS-фид (`blog/rss.xml`)
   - Обновляет `sitemap.xml`
   - Коммитит сгенерированные файлы обратно в репо
4. Netlify пересобирает сайт → пост появляется на `tonforce.app/blog/`

Существующие 3 поста (`launch-tonforce-v4.html`, `how-tonforce-matrix-works.html`, `security-audit-results.html`) **остаются на месте** — их метаданные прописаны в `scripts/legacy_posts.json`.

## Установка

1. Скачать архив, распаковать
2. На GitHub в корне репо `spsonlys/tonforce` → **Add file → Upload files**
3. Перетащить **папки `.github/` и `scripts/`** (с сохранением структуры)
4. Commit changes

После коммита GitHub Action автоматически запустится **один раз** и пересоберёт все 3 индекса блога (RU/EN/UA), создаст RSS и обновит sitemap.

## Структура

```
.github/workflows/build-blog.yml    # GitHub Actions workflow
scripts/
  build_blog.py                     # Главный скрипт сборки
  legacy_posts.json                 # Метаданные 3 существующих постов
  templates/
    post.html.j2                    # Шаблон страницы поста
    blog_index.html.j2              # Шаблон главной блога
    rss.xml.j2                      # Шаблон RSS-фида
```

## Создание нового поста

1. Откройте `lively-marzipan-a12eb9.netlify.app/admin/` (или `tonforce.app/admin/` — но через netlify-домен работает стабильнее)
2. Выберите коллекцию: «📝 Посты (Русский)», «📝 Posts (English)» или «📝 Пости (Українська)»
3. Нажмите **Создать пост**
4. Заполните поля и нажмите **Опубликовать** (или сохраните как черновик)
5. Через 1–3 минуты пост появится на сайте

Если у поста стоит `Опубликовать: false` (или `published: false` в frontmatter), он не будет генерироваться в HTML.

## Frontmatter формат

Decap CMS автоматически создаёт правильный frontmatter:

```yaml
---
title: "Заголовок поста"
lead: "Краткое описание (1-2 предложения, появится на главной блога)"
date: 2026-05-28T00:00:00.000+03:00
category: "announcements"  # или: guides, security, case-studies, analytics, success-stories
cover_emoji: "🚀"
cover_image: "/images/blog/cover.png"  # опционально, заменяет emoji
read_time: 5
meta_description: "Описание для SEO (140-160 символов)"
published: true
---
```

Дальше — Markdown с заголовками H2/H3, списками, ссылками, цитатами и т.д.

## Маппинг категорий → лейблы

| Значение в frontmatter | RU | EN | UA |
|---|---|---|---|
| `announcements` | Анонс | Announcement | Анонс |
| `guides` | Гайд | Guide | Гайд |
| `security` | Безопасность | Security | Безпека |
| `case-studies` | Кейсы | Case studies | Кейси |
| `analytics` | Аналитика | Analytics | Аналітика |
| `success-stories` | Истории успеха | Success stories | Історії успіху |

## Ручной запуск

GitHub → ваш репозиторий → вкладка **Actions** → выберите workflow **«Build Blog»** → нажмите **Run workflow**.

Это полезно если нужно перегенерировать без коммита нового поста (например, после обновления `legacy_posts.json` или шаблонов).

## Локальный запуск

Если хотите тестировать локально (опционально):

```bash
pip install markdown jinja2 pyyaml
python scripts/build_blog.py
```

Скрипт сгенерирует все файлы прямо в репо.

## Изменение шаблонов

Если хотите поменять дизайн постов или главной блога — редактируйте файлы в `scripts/templates/*.j2`. Это Jinja2-шаблоны, синтаксис вида `{{ переменная }}` и `{% if ... %}`.

После любого изменения шаблонов GitHub Actions автоматически пересоберёт все посты при следующем коммите.
