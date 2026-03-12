# 🧴 Parfum Pinterest Auto-Poster

Автоматическая публикация парфюмерии в Pinterest с ссылкой на Telegram-канал.

## 📋 Что делает система

1. **Парсит** товары с dnkparfum.ru
2. **Генерирует** RSS ленту с изображениями
3. **Сортирует** по 6 тематическим доскам
4. **Публикует** пины через IFTTT
5. **Автоматизирует** всё через GitHub Actions

## 🔐 GitHub Secrets (настроено)

| Secret | Назначение |
|--------|-----------|
| `BOARD_MONTALE` | Доска Montale |
| `BOARD_NISHEVAYA` | Доска Нишевая парфюмерия |
| `BOARD_STOYKIE` | Доска Стойкие ароматы |
| `BOARD_VOSTOCHNIE` | Доска Восточные ароматы |
| `BOARD_XERJOFF` | Доска Xerjoff |
| `BOARD_ZIMNIE` | Доска Зимние ароматы |
| `PINTEREST_EMAIL` | Email от Pinterest |
| `PINTEREST_PASSWORD` | Пароль от Pinterest |
| `TELEGRAM_CHANNEL` | Ссылка на ТГ-канал |

## 🚀 Быстрый старт

### 1. Включите GitHub Pages

Settings → Pages → Source: Deploy from a branch → Branch: **main**, Folder: **root**

RSS будет доступна по: `https://yourusername.github.io/parfum-pinterest-auto/rss/feed.xml`

### 2. Настройте IFTTT (6 апплетов)

Создайте **отдельный апплет для каждой доски**:

| Апплет | If This | Then That | Board |
|--------|---------|-----------|-------|
| 1 | RSS Feed | Pinterest | BOARD_MONTALE |
| 2 | RSS Feed | Pinterest | BOARD_NISHEVAYA |
| 3 | RSS Feed | Pinterest | BOARD_STOYKIE |
| 4 | RSS Feed | Pinterest | BOARD_VOSTOCHNIE |
| 5 | RSS Feed | Pinterest | BOARD_XERJOFF |
| 6 | RSS Feed | Pinterest | BOARD_ZIMNIE |

**Настройка каждого апплета:**
1.  Зайдите на [ifttt.com/create](https://ifttt.com/create)
2.  **If This** → **RSS Feed** → вставьте URL вашей RSS
3.  **Then That** → **Pinterest** → подключите аккаунт → выберите доску из списка
4.  Заполните поля:
    ```
    Image: {{EntryImage}}
    Title: {{EntryTitle}}
    Description: {{EntryContent}}
    Link: {{EntryUrl}}
    ```
5.  Сохраните и включите

### 3. Запустите вручную

Actions → Auto Publish Parfum to Pinterest → Run workflow

## 📁 Структура
