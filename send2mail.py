import sys
import os
import argparse
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path

# Константы
LETTER_SIGNATURE = """______________________________________________________________
Это письмо сформировано автоматически роботом отправки данных.
Отвечать на него не нужно, да и бесполезно."""

ADMIN_MAIL = "Email для связи с администратором: admin@example.com"

# Коды возврата
EXIT_SUCCESS = 0
EXIT_ARGUMENT_ERROR = 1
EXIT_FILE_NOT_FOUND = 2
EXIT_FILE_READ_ERROR = 3
EXIT_ATTACHMENT_ERROR = 4
EXIT_SMTP_CONNECTION_ERROR = 5
EXIT_SMTP_AUTH_ERROR = 6
EXIT_SMTP_SEND_ERROR = 7
EXIT_UNKNOWN_ERROR = 99

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("email_sender.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def validate_file_path(file_path: str) -> bool:
    """Проверяет существование файла и доступность для чтения.

    Args:
        file_path: Путь к файлу

    Returns:
        bool: True если файл доступен, False в противном случае
    """
    path = Path(file_path)
    if not path.exists():
        logger.error(f"Файл не существует: {file_path}")
        return False
    if not path.is_file():
        logger.error(f"Указанный путь не является файлом: {file_path}")
        return False
    if not os.access(file_path, os.R_OK):
        logger.error(f"Нет прав на чтение файла: {file_path}")
        return False
    return True


def read_text_file(file_path: str) -> str:
    """Чтение текста письма из файла.

    Args:
        file_path: Путь к файлу с текстом письма

    Returns:
        Содержимое файла в виде строки

    Raises:
        SystemExit: С кодом EXIT_FILE_READ_ERROR если файл не может быть прочитан
    """
    try:
        if not validate_file_path(file_path):
            raise IOError(f"Файл недоступен: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            logger.info(f"Успешно прочитан файл с текстом письма: {file_path}")
            return content
    except Exception as e:
        logger.error(f"Ошибка при чтении файла с текстом письма: {str(e)}")
        sys.exit(EXIT_FILE_READ_ERROR)


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

    Raises:
        SystemExit: С кодом EXIT_UNKNOWN_ERROR при ошибке создания сообщения
    """
    try:
        message = MIMEMultipart()
        message["From"] = sender
        message["To"] = recipient
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain", "utf-8"))
        logger.info("Создано MIME сообщение")
        return message
    except Exception as e:
        logger.error(f"Ошибка при создании сообщения: {str(e)}")
        sys.exit(EXIT_UNKNOWN_ERROR)


def attach_files(message: MIMEMultipart, file_paths: str) -> bool:
    """Добавляет вложения к письму.

    Args:
        message: Объект письма
        file_paths: Строка с путями к файлам, разделенными запятыми

    Returns:
        True если все вложения добавлены успешно, False в случае ошибки
    """
    success = True
    for file_path in file_paths.split(","):
        file_path = file_path.strip()
        try:
            if not validate_file_path(file_path):
                success = False
                continue

            with open(file_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
                part["Content-Disposition"] = (
                    f'attachment; filename="{os.path.basename(file_path)}"'
                )
                message.attach(part)
                logger.info(f"Успешно добавлено вложение: {file_path}")
        except Exception as e:
            logger.error(f"Ошибка при добавлении вложения {file_path}: {str(e)}")
            success = False
    return success


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

    Raises:
        SystemExit: С различными кодами ошибок в зависимости от типа ошибки SMTP
    """
    try:
        logger.info(f"Попытка подключения к SMTP серверу {server}:{port}")

        if use_ssl:
            server = smtplib.SMTP_SSL(server, port)
        else:
            server = smtplib.SMTP(server, port)

        if auth:
            try:
                username, password = auth.split(":")
                server.login(username, password)
                logger.info("Успешная аутентификация на SMTP сервере")
            except smtplib.SMTPAuthenticationError:
                logger.error("Ошибка аутентификации на SMTP сервере")
                sys.exit(EXIT_SMTP_AUTH_ERROR)
            except Exception as e:
                logger.error(f"Ошибка при аутентификации: {str(e)}")
                sys.exit(EXIT_SMTP_AUTH_ERROR)

        server.send_message(message)
        server.quit()
        logger.info("Письмо успешно отправлено")
        return True
    except smtplib.SMTPConnectError:
        logger.error("Ошибка подключения к SMTP серверу")
        sys.exit(EXIT_SMTP_CONNECTION_ERROR)
    except smtplib.SMTPException:
        logger.error("Ошибка при отправке письма через SMTP")
        sys.exit(EXIT_SMTP_SEND_ERROR)
    except Exception as e:
        logger.error(f"Неизвестная ошибка при отправке письма: {str(e)}")
        sys.exit(EXIT_UNKNOWN_ERROR)


def generate_default_email_body(file_paths: str) -> str:
    """Генерирует текст письма по умолчанию."""
    files = file_paths.split(",")
    body = "Вам отправлены файлы:\n" + "\n".join(
        f"{i+1}. {os.path.basename(f.strip())}" for i, f in enumerate(files)
    )
    body += f"\n{LETTER_SIGNATURE}\n{ADMIN_MAIL}"
    logger.info("Сгенерирован текст письма по умолчанию")
    return body


def get_email_body(args: argparse.Namespace) -> str:
    """Определяет текст письма согласно приоритетам:
    1. Файл с текстом (--text-file)
    2. Текст из аргумента (--text)
    3. Автосгенерированный текст

    Args:
        args: Аргументы командной строки

    Returns:
        Текст письма
    """
    if args.text_file:
        try:
            return read_text_file(args.text_file)
        except SystemExit:
            logger.warning(
                "Не удалось прочитать файл с текстом, пробуем другие варианты"
            )
            raise
        except Exception:
            logger.warning(
                "Не удалось прочитать файл с текстом, пробуем другие варианты"
            )

    if args.text:
        logger.info("Используется текст из аргумента --text")
        return args.text

    logger.info("Используется автосгенерированный текст письма")
    return generate_default_email_body(args.files)


def setup_arg_parser() -> argparse.ArgumentParser:
    """Настраивает парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description="""Утилита для отправки писем с вложениями.

Коды возврата:
  0 - Успешное выполнение
  1 - Ошибка аргументов командной строки
  2 - Файл не найден
  3 - Ошибка чтения файла
  4 - Ошибка добавления вложения
  5 - Ошибка подключения к SMTP серверу
  6 - Ошибка аутентификации на SMTP сервере
  7 - Ошибка отправки письма
 99 - Неизвестная ошибка""",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # Обязательные параметры
    parser.add_argument("--server", required=True, help="SMTP сервер")
    parser.add_argument("--port", required=True, type=int, help="Порт SMTP сервера")
    parser.add_argument(
        "--from", default="noreply@example.com", dest="sender", help="Email отправителя"
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


def main() -> int:
    """Основная функция выполнения скрипта."""
    try:
        parser = setup_arg_parser()
        args = parser.parse_args()

        # Проверка конфликтующих параметров
        if args.text and args.text_file:
            logger.error(
                "Ошибка: нельзя использовать одновременно --text и --text-file"
            )
            return EXIT_ARGUMENT_ERROR

        # Проверка существования файлов вложений
        for file_path in args.files.split(","):
            file_path = file_path.strip()
            if not file_path:
                continue
            if not validate_file_path(file_path):
                return EXIT_FILE_NOT_FOUND

        # Получение текста письма согласно приоритетам
        try:
            args.text = get_email_body(args)
        except SystemExit as e:
            return e.code
        except Exception:
            args.text = generate_default_email_body(args.files)

        # Создание и настройка письма
        message = create_message(args.sender, args.to, args.subject, args.text)

        # Добавление вложений
        if not attach_files(message, args.files):
            return EXIT_ATTACHMENT_ERROR

        # Отправка письма
        if send_email(
            args.server, args.port, args.sender, args.to, message, args.ssl, args.auth
        ):
            logger.info("Письмо успешно отправлено!")
            return EXIT_SUCCESS
        return EXIT_SMTP_SEND_ERROR

    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}")
        return EXIT_UNKNOWN_ERROR


if __name__ == "__main__":
    sys.exit(main())
