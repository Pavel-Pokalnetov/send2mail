import sys
import os
import argparse
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


# Константы
LETTER_SIGNATURE = """______________________________________________________________
Это письмо сформировано автоматически роботом отправки данных.
Отвечать на него не нужно, да и бесполезно."""

ADMIN_MAIL = "Email для связи с администратором: admin@example.com"


def read_text_file(file_path: str) -> str:
    """Чтение текста письма из файла.

    Args:
        file_path: Путь к файлу с текстом письма

    Returns:
        Содержимое файла в виде строки

    Raises:
        SystemExit: Если файл не может быть прочитан
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Ошибка при чтении файла с текстом письма: {str(e)}")
        sys.exit(1)


def create_message(
    sender: str, recipient: str, subject: str, body: str
) -> MIMEMultipart:
    """Создает объект письма с указанными параметрами.

    Args:
        sender: Email отправителя
        recipient: Email получателя
        subject: Тема письма
        body: Текст письма

    Returns:
        Объект MIMEMultipart с заполненными заголовками
    """
    message = MIMEMultipart()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))
    return message


def attach_files(message: MIMEMultipart, file_paths: str) -> bool:
    """Добавляет вложения к письму.

    Args:
        message: Объект письма
        file_paths: Строка с путями к файлам, разделенными запятыми

    Returns:
        True если все вложения добавлены успешно, False в случае ошибки
    """
    for file_path in file_paths.split(","):
        try:
            with open(file_path.strip(), "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
                part["Content-Disposition"] = (
                    f'attachment; filename="{os.path.basename(file_path)}"'
                )
                message.attach(part)
        except Exception as e:
            print(f"Ошибка при добавлении вложения {file_path}: {str(e)}")
            return False
    return True


def send_email(
    server: str,
    port: int,
    sender: str,
    recipient: str,
    message: MIMEMultipart,
    use_ssl: bool,
    auth: str = None,
) -> bool:
    """Отправляет письмо через SMTP сервер.

    Args:
        server: SMTP сервер
        port: Порт SMTP сервера
        sender: Email отправителя
        recipient: Email получателя
        message: Объект письма
        use_ssl: Использовать SSL/TLS
        auth: Данные аутентификации в формате "user:pass" (опционально)

    Returns:
        True если письмо отправлено успешно, False в случае ошибки
    """
    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(server, port)
        else:
            server = smtplib.SMTP(server, port)

        if auth:
            username, password = auth.split(":")
            server.login(username, password)

        server.send_message(message)
        server.quit()
        return True
    except Exception as e:
        print(f"Ошибка при отправке письма: {str(e)}")
        return False


def setup_arg_parser() -> argparse.ArgumentParser:
    """Настраивает парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description="Утилита для отправки писем с вложениями"
    )

    # Обязательные параметры
    parser.add_argument("--server", required=True, help="SMTP сервер")
    parser.add_argument("--port", required=True, type=int, help="Порт SMTP сервера")
    parser.add_argument(
        "--from", default="noreply@slenergo.ru", dest="sender", help="Email отправителя"
    )
    parser.add_argument("--to", required=True, help="Email получателя")
    parser.add_argument(
        "--files", required=True, help="Файлы для вложения (через запятую)"
    )

    # Необязательные параметры
    parser.add_argument(
        "--subject", default="Вам отправлен файл(ы)", help="Тема письма"
    )
    parser.add_argument("--text", help="Текст письма (не использовать с --text-file)")
    parser.add_argument(
        "--text-file", help="Файл с текстом письма (не использовать с --text)"
    )
    parser.add_argument("--auth", help="Логин и пароль (user:pass)")
    parser.add_argument("--ssl", action="store_true", help="Использовать SSL/TLS")

    return parser


def generate_default_email_body(file_paths: str) -> str:
    """Генерирует текст письма по умолчанию."""
    files = file_paths.split(",")
    body = "Вам отправлены файлы:\n" + "\n".join(
        f"{i+1}. {os.path.basename(f)}" for i, f in enumerate(files)
    )
    body += f"\n{LETTER_SIGNATURE}\n{ADMIN_MAIL}"
    return body


def main() -> int:
    """Основная функция выполнения скрипта."""
    parser = setup_arg_parser()
    args = parser.parse_args()

    # Проверка конфликтующих параметров
    if args.text and args.text_file:
        print("Ошибка: нельзя использовать одновременно --text и --text-file")
        return 1

    # Получение текста письма
    if args.text_file:
        args.text = read_text_file(args.text_file)
    elif not args.text:
        args.text = generate_default_email_body(args.files)

    # Создание и настройка письма
    message = create_message(args.sender, args.to, args.subject, args.text)

    # Добавление вложений
    if not attach_files(message, args.files):
        return 1

    # Отправка письма
    if send_email(
        args.server, args.port, args.sender, args.to, message, args.ssl, args.auth
    ):
        print("Письмо успешно отправлено!")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
