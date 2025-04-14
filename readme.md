
# Email Sender Utility

Утилита для отправки писем с вложениями через SMTP сервер

## Возможности

- Отправка писем с одним или несколькими вложениями
- Поддержка SSL/TLS для безопасного соединения
- Аутентификация на SMTP сервере
- Гибкие варианты указания текста письма:
  - Непосредственно в командной строке
  - Через файл с текстом
  - Автоматическая генерация списка вложений
- Настраиваемые параметры письма (тема, отправитель, получатель)

## Требования

- Python 3.6+
- Установленные стандартные библиотеки Python:
  - `smtplib`
  - `email`

## Установка

1. Склонируйте репозиторий:
   ```bash
   git clone https://github.com/Pavel-Pokalnetov/send2mail.git
   cd send2mail
   ```

2. (Опционально) Создайте виртуальное окружение:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/MacOS
   venv\Scripts\activate     # Windows
   ```

## Использование

### Базовый синтаксис

```bash
python email_sender.py --server SMTP_SERVER --port PORT --to RECIPIENT --files FILE1,FILE2 [OPTIONS]
```

### Обязательные параметры

| Параметр  | Описание                  |
|-----------|---------------------------|
| `--server`| Адрес SMTP сервера        |
| `--port`  | Порт SMTP сервера         |
| `--to`    | Email получателя          |
| `--files` | Пути к файлам (через запятую) |

### Дополнительные параметры

| Параметр      | Описание                                  | По умолчанию                     |
|---------------|-------------------------------------------|-----------------------------------|
| `--from`      | Email отправителя                         | `Адрес администратора`             |
| `--subject`   | Тема письма                               | `"Вам отправлен файл(ы)"`         |
| `--text`      | Текст письма                              | Автогенерация списка файлов       |
| `--text-file` | Файл с текстом письма                     | -                                 |
| `--auth`      | Аутентификация (формат `user:password`)   | -                                 |
| `--ssl`       | Использовать SSL/TLS                      | False                             |

### Примеры использования

1. Простая отправка с автогенерируемым текстом:
   ```bash
   python email_sender.py --server smtp.example.com --port 587 --to recipient@example.com --files file1.pdf,file2.jpg
   ```

2. Отправка с кастомным текстом и темой:
   ```bash
   python email_sender.py --server smtp.example.com --port 465 --to recipient@example.com --files data.xlsx --subject "Ваши данные" --text "Привет, вот запрошенные данные." --ssl
   ```

3. Отправка с аутентификацией и текстом из файла:
   ```bash
   python email_sender.py --server smtp.example.com --port 587 --to recipient@example.com --files report.pdf --text-file message.txt --auth user:password
   ```

## Логирование ошибок

При возникновении ошибок утилита выводит сообщения в консоль с описанием проблемы:

- Ошибки чтения файлов
- Проблемы с подключением к SMTP серверу
- Ошибки аутентификации
- Проблемы с отправкой письма

## Лицензия

Этот проект распространяется под лицензией MIT. См. файл [LICENSE](/license.md) для получения дополнительной информации.

## Контакты

По вопросам и предложениям обращайтесь:
- Email: redx@mail.ru
- GitHub: [Pavel-Pokalnetov](https://github.com/Pavel-Pokalnetov)
