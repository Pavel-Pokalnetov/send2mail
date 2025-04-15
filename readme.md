# Send2Mail - Консольная утилита для отправки писем с вложениями.

![Python 3.6+](https://img.shields.io/badge/python-3.6%2B-blue?logo=python)
![Windows](https://img.shields.io/badge/Windows-0078D6?logo=windows&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-FCC624?logo=linux&logoColor=black)

Утилита `send2mail.py` предназначена для отправки электронных писем с вложениями через SMTP сервер. Поддерживает аутентификацию, SSL, гибкую настройку текста письма и логирование.

## Возможности

- Отправка писем с одним или несколькими вложениями
- Поддержка SMTP серверов с аутентификацией и без
- Возможность использования SSL/TLS
- Гибкое формирование текста письма:
  - Прямое указание текста в аргументах
  - Чтение из файла
  - Автогенерация с перечнем вложений
- Логирование работы (в файл и/или консоль)
- Проверка валидности email адресов
- Подробные коды возврата для диагностики ошибок

## Требования

- Python 3.6 или новее
- Установленные модули из стандартной библиотеки Python:
  - `smtplib`
  - `email`
  - `argparse`
  - `logging`
  - `pathlib`
  - `re`

## Установка

1. Склонируйте репозиторий:
   ```bash
   git clone https://github.com/Pavel-Pokalnetov/send2mail.git
   cd send2mail
   ```

2. Убедитесь, что у вас установлен Python 3.6+:
   ```bash
   python --version
   ```

## Использование

### Базовый синтаксис

```bash
python send2mail.py -s SMTP_СЕРВЕР -p ПОРТ -t ПОЛУЧАТЕЛЬ -a ФАЙЛЫ [ОПЦИИ]
```

### Обязательные параметры

| Параметр            | Описание                                                  |
|---------------------|-----------------------------------------------------------|
| `-s`, `--server`    | Адрес SMTP сервера                                        |
| `-p`, `--port`      | Порт SMTP сервера                                         |
| `-t`, `--to`        | Email адрес получателя                                    |
| `-a`, `--files`     | Файлы для вложения (через запятую) **или**                |
| `--files-list`      | Файл со списком файлов для вложения (по одному на строку) |

### Основные опции

| Опция                   | Описание                                                                                   |
|-------------------------|--------------------------------------------------------------------------------------------|
| `-f`, `--from`          | Email отправителя (по умолчанию: admin@example.com), изменяется в константе ADMIN_MAIL     |
| `-j`, `--subject`       | Тема письма (по умолчанию: "Письмо с вложениями")                                          |
| `-b`, `--text`          | Текст письма                                                                               |
| `-bf`, `--text-file`    | Файл с текстом письма                                                                      |
| `-u`, `--auth`          | Данные аутентификации в формате "логин:пароль"                                             |
| `-uf`, `--auth-file`    | Файл с данными аутентификации (логин:пароль)                                               |
| `-S`, `--ssl`           | Использовать SSL                                                                           |
| `-l`, `--log`           | Сохранять логи в файл (по умолчанию: send2mail.log) изменяется в константе DEFAULT_LOGFILE |

### Примеры использования

1. Простая отправка с автогенерируемым текстом:
   ```bash
   python send2mail.py -s smtp.example.com -p 587 -t recipient@example.com -a file1.pdf,file2.jpg
   ```

2. Отправка с указанием темы и текста:
   ```bash
   python send2mail.py -s smtp.example.com -p 587 -t recipient@example.com -a document.docx -j "Ваши документы" -b "Привет! Отправляю запрошенные файлы."
   ```

3. Отправка с аутентификацией и SSL:
   ```bash
   # передача данных авторизации в командной строке
   python send2mail.py -s smtp.gmail.com -p 465 -t recipient@example.com -a report.pdf -u username:password -S

   # передача данных авторизации в файле auth.txt
   python send2mail.py -s smtp.gmail.com -p 465 -t recipient@example.com -a report.pdf -uf auth.txt -S

   # содержимое файла auth.txt
   username
   password
   ```

4. Использование файла со списком вложений и файла с текстом:
   ```bash
   python send2mail.py -s smtp.example.com -p 25 -t recipient@example.com --files-list files.dat --text-file message.txt 

   # содержимое файла files.dat
   filename_01
   filename_02
   ...
   filename_NN

   # файл message.txt содержит текст для помещения в тело письма

   ```

5. Сохранение логов в указанный файл:
   ```bash
   python send2mail.py -s smtp.example.com -p 587 -t recipient@example.com -a data.csv --log mylog.txt
   ```

## Коды возврата

Программа возвращает следующие коды:

| Код    | Описание                                |
|--------|-----------------------------------------|
| 0      | Успешное выполнение                     |
| 1      | Ошибка в аргументах командной строки    |
| 2      | Файл не найден                          |
| 3      | Ошибка чтения файла                     |
| 4      | Ошибка прикрепления файлов              |
| 5      | Ошибка подключения к SMTP серверу       |
| 6      | Ошибка аутентификации на SMTP сервере   |
| 7      | Ошибка отправки письма                  |
| 8      | Невалидный email адрес                  |
| 9      | Не указаны файлы для отправки           |
| 99     | Неизвестная ошибка                      |

## Логирование

По умолчанию логи выводятся в консоль. Для сохранения логов в файл используйте опцию `-l` или `--log`:

```bash
python send2mail.py ... --log  # сохранит логи в send2mail.log
python send2mail.py ... --log custom.log  # сохранит логи в custom.log
```

Формат логов:
```
2023-01-01 12:00:00 - root - INFO - Сообщение
2023-01-01 12:00:01 - root - ERROR - Ошибка
```

## Безопасность

1. Для защиты учетных данных рекомендуется использовать файл аутентификации (`--auth-file`) вместо передачи логина и пароля в командной строке.
2. Убедитесь, что файлы с учетными данными имеют соответствующие права доступа.
3. Используйте SSL (`-S`) для шифрования соединения с SMTP сервером.

## Лицензия

Этот проект распространяется под лицензией MIT. См. файл [LICENSE](LICENSE.md) для получения дополнительной информации.

## Поддержка и контакты

Если у вас возникли вопросы или проблемы, создайте issue в репозитории проекта.
Или обращайтесь к автору [redx@mail.ru](mailto:redx@mail.ru)

