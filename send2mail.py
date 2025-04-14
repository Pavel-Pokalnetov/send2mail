import sys
import os
import argparse
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
import re
from typing import Optional, List

# Константы
ADMIN_MAIL = "admin@example.com"
LOGFILE = "email_sender.log"

# Коды возврата
EXIT_SUCCESS = 0
EXIT_ARGUMENT_ERROR = 1
EXIT_FILE_NOT_FOUND = 2
EXIT_FILE_READ_ERROR = 3
EXIT_ATTACHMENT_ERROR = 4
EXIT_SMTP_CONNECTION_ERROR = 5
EXIT_SMTP_AUTH_ERROR = 6
EXIT_SMTP_SEND_ERROR = 7
EXIT_INVALID_EMAIL = 8
EXIT_NO_FILES = 9
EXIT_UNKNOWN_ERROR = 99

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOGFILE), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def validate_email(email: str) -> bool:
    """Проверяет валидность email адреса."""
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) is not None


def validate_file_path(file_path: Path) -> bool:
    """Проверяет существование файла и доступность для чтения."""
    if not file_path.exists():
        logger.error(f"Файл не существует: {file_path}")
        return False
    if not file_path.is_file():
        logger.error(f"Указанный путь не является файлом: {file_path}")
        return False
    if not os.access(file_path, os.R_OK):
        logger.error(f"Нет прав на чтение файла: {file_path}")
        return False
    return True


def read_text_file(file_path: Path) -> str:
    """Чтение текста письма из файла."""
    try:
        with file_path.open("r", encoding="utf-8") as f:
            content = f.read()
            logger.info(f"Успешно прочитан файл с текстом письма: {file_path}")
            return content
    except Exception as e:
        logger.error(f"Ошибка при чтении файла с текстом письма: {str(e)}")
        sys.exit(EXIT_FILE_READ_ERROR)


def add_signature(body: str, sender: Optional[str] = None) -> str:
    """Добавляет подпись к тексту письма."""
    signature = "\n\nЭто письмо отправлено автоматически. Отвечать на него не нужно."

    if sender:
        signature += f"\nОбратный адрес для связи: {sender}"
    else:
        signature += f"\nОбратный адрес для связи: {ADMIN_MAIL}"

    return body + signature


def create_message(
    sender: str, recipient: str, subject: str, body: str
) -> MIMEMultipart:
    """Создает объект письма с указанными параметрами."""
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


def attach_files(message: MIMEMultipart, file_paths: List[Path]) -> bool:
    """Добавляет вложения к письму."""
    success = True
    for file_path in file_paths:
        try:
            with file_path.open("rb") as f:
                filename = file_path.name
                part = MIMEApplication(f.read(), Name=filename)
                part["Content-Disposition"] = f'attachment; filename="{filename}"'
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
    auth: Optional[str] = None,
) -> None:
    """Отправляет письмо через SMTP сервер."""
    smtp_server = None
    try:
        logger.info(f"Попытка подключения к SMTP серверу {server}:{port}")

        if use_ssl:
            smtp_server = smtplib.SMTP_SSL(server, port)
        else:
            smtp_server = smtplib.SMTP(server, port)

        if auth:
            username, password = auth.split(":")
            try:
                smtp_server.login(username, password)
                logger.info("Успешная аутентификация на SMTP сервере")
            except smtplib.SMTPAuthenticationError:
                logger.error("Ошибка аутентификации на SMTP сервере")
                sys.exit(EXIT_SMTP_AUTH_ERROR)
            except Exception as e:
                logger.error(f"Ошибка при аутентификации: {str(e)}")
                sys.exit(EXIT_SMTP_AUTH_ERROR)

        smtp_server.send_message(message)
        logger.info("Письмо успешно отправлено")
    except smtplib.SMTPConnectError:
        logger.error("Ошибка подключения к SMTP серверу")
        sys.exit(EXIT_SMTP_CONNECTION_ERROR)
    except smtplib.SMTPHeloError:
        logger.error("Ошибка приветствия SMTP сервера")
        sys.exit(EXIT_SMTP_CONNECTION_ERROR)
    except smtplib.SMTPDataError:
        logger.error("Ошибка данных SMTP")
        sys.exit(EXIT_SMTP_SEND_ERROR)
    except smtplib.SMTPException as e:
        logger.error(f"Ошибка SMTP: {str(e)}")
        sys.exit(EXIT_SMTP_SEND_ERROR)
    except Exception as e:
        logger.error(f"Неизвестная ошибка при отправке письма: {str(e)}")
        sys.exit(EXIT_UNKNOWN_ERROR)
    finally:
        if smtp_server:
            try:
                smtp_server.quit()
            except Exception:
                pass


def generate_default_email_body(
    file_paths: List[Path], sender: Optional[str] = None
) -> str:
    """Генерирует текст письма по умолчанию."""
    body = "Вам отправлены файлы:\n" + "\n".join(
        f"{i+1}. {f.name}" for i, f in enumerate(file_paths)
    )
    return add_signature(body, sender)


def get_email_body(args: argparse.Namespace, file_paths: List[Path]) -> str:
    """Определяет текст письма согласно приоритетам."""
    if args.text_file:
        try:
            body = read_text_file(args.text_file)
            return add_signature(body, args.sender)
        except SystemExit:
            logger.warning(
                "Не удалось прочитать файл с текстом, используется текст из аргумента или по умолчанию"
            )
        except Exception as e:
            logger.warning(
                f"Не удалось прочитать файл с текстом: {str(e)}, используется текст из аргумента или по умолчанию"
            )

    if args.text:
        logger.info("Используется текст из аргумента --text")
        return add_signature(args.text, args.sender)

    logger.info("Используется автосгенерированный текст письма")
    return generate_default_email_body(file_paths, args.sender)


def parse_file_paths(file_paths_str: str) -> List[Path]:
    """Разбирает строку с путями к файлам."""
    if not file_paths_str.strip():
        logger.error("Не указаны файлы для отправки")
        sys.exit(EXIT_NO_FILES)

    file_paths = []
    for file_path in file_paths_str.split(","):
        file_path = file_path.strip()
        if not file_path:
            continue

        path = Path(file_path)
        if not validate_file_path(path):
            sys.exit(EXIT_FILE_NOT_FOUND)
        file_paths.append(path)

    if not file_paths:
        logger.error("Не указаны валидные файлы для отправки")
        sys.exit(EXIT_NO_FILES)

    return file_paths


def setup_arg_parser() -> argparse.ArgumentParser:
    """Настраивает парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description="""Утилита для отправки писем с вложениями.""",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # Обязательные параметры
    parser.add_argument("-s", "--server", required=True, help="SMTP сервер")
    parser.add_argument(
        "-p", "--port", required=True, type=int, help="Порт SMTP сервера"
    )
    parser.add_argument("-t", "--to", required=True, help="Email получателя")
    parser.add_argument(
        "-a", "--files", required=True, help="Файлы для вложения (через запятую)"
    )

    # Необязательные параметры
    parser.add_argument("-f", "--from", dest="sender", help="Email отправителя")
    parser.add_argument(
        "-j", "--subject", default="Вам отправлен файл(ы)", help="Тема письма"
    )
    parser.add_argument(
        "-x", "--text", help="Текст письма (не использовать с --text-file)"
    )
    parser.add_argument(
        "-F",
        "--text-file",
        type=Path,
        help="Файл с текстом письма (не использовать с --text)",
    )
    parser.add_argument("-u", "--auth", help="Логин и пароль (user:pass)")
    parser.add_argument("-S", "--ssl", action="store_true", help="Использовать SSL/TLS")

    return parser


def main() -> int:
    """Основная функция выполнения скрипта."""
    try:
        parser = setup_arg_parser()
        args = parser.parse_args()

        if args.text and args.text_file:
            logger.error(
                "Ошибка: нельзя использовать одновременно --text и --text-file"
            )
            return EXIT_ARGUMENT_ERROR

        if args.sender and not validate_email(args.sender):
            logger.error(f"Невалидный email отправителя: {args.sender}")
            return EXIT_INVALID_EMAIL

        if not validate_email(args.to):
            logger.error(f"Невалидный email получателя: {args.to}")
            return EXIT_INVALID_EMAIL

        file_paths = parse_file_paths(args.files)
        body = get_email_body(args, file_paths)
        message = create_message(args.sender or ADMIN_MAIL, args.to, args.subject, body)

        if not attach_files(message, file_paths):
            return EXIT_ATTACHMENT_ERROR

        send_email(
            args.server,
            args.port,
            args.sender or ADMIN_MAIL,
            args.to,
            message,
            args.ssl,
            args.auth,
        )
        return EXIT_SUCCESS

    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}")
        return EXIT_UNKNOWN_ERROR


if __name__ == "__main__":
    sys.exit(main())
