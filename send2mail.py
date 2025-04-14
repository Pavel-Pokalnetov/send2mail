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
from typing import Optional, List, Tuple


# Константы
ADMIN_MAIL = "noreply@example.com"
DEFAULT_LOGFILE = "send2mail.log"

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


# Пользовательские исключения
class EmailSenderError(Exception):
    """Базовое исключение для ошибок отправки email"""
    pass


class FileReadError(EmailSenderError):
    """Ошибка чтения файла"""
    pass


class AuthError(EmailSenderError):
    """Ошибка аутентификации"""
    pass


class SMTPError(EmailSenderError):
    """Ошибка SMTP"""
    pass


# Глобальная переменная для логгера
logger = logging.getLogger()


def validate_email(email: str) -> bool:
    """Проверяет валидность email адреса."""
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9].+$"
    return re.match(pattern, email) is not None


def validate_file_path(file_path: Path) -> bool:
    """Проверяет существование файла и доступность для чтения."""
    if not file_path.exists():
        logging.error(f"Файл не существует: {file_path}")
        return False
    if not file_path.is_file():
        logging.error(f"Указанный путь не является файлом: {file_path}")
        return False
    if not os.access(file_path, os.R_OK):
        logging.error(f"Нет прав на чтение файла: {file_path}")
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
        raise FileReadError(f"Ошибка чтения файла {file_path}: {str(e)}")


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
        logger.debug("MIME сообщение успешно создано")
        return message
    except Exception as e:
        logger.error(f"Ошибка при создании сообщения: {str(e)}", exc_info=True)
        raise EmailSenderError(f"Ошибка создания сообщения: {str(e)}")


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
                logger.info(f"Успешно добавлено вложение: {filename}")
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
    auth_file: Optional[argparse.FileType] = None,
) -> int:
    """Отправляет письмо через SMTP сервер.
    Возвращает код ошибки или EXIT_SUCCESS при успехе."""
    smtp_server = None
    try:
        logger.info(f"Подключение к SMTP серверу {server}:{port} (SSL: {use_ssl})")
        timeout_seconds = 5  # Таймаут в секундах
        if use_ssl:
            smtp_server = smtplib.SMTP_SSL(server, port, timeout=timeout_seconds)
        else:
            smtp_server = smtplib.SMTP(server, port, timeout=timeout_seconds)

        if auth or auth_file:
            if auth:
                username, password = auth.split(":")
                logger.debug("Используется аутентификация через аргументы")
            elif auth_file:
                username, password = read_auth_from_file(auth_file)

            try:
                smtp_server.login(username, password)
                logger.info("Успешная аутентификация на SMTP сервере")
            except smtplib.SMTPAuthenticationError as e:
                logger.error(f"Ошибка аутентификации: {str(e)}")
                return EXIT_SMTP_AUTH_ERROR
            except Exception as e:
                logger.error(f"Ошибка при аутентификации: {str(e)}", exc_info=True)
                return EXIT_SMTP_AUTH_ERROR

        smtp_server.send_message(message)
        logger.info(f"Письмо успешно отправлено от {sender} к {recipient}")
        return EXIT_SUCCESS

    except smtplib.SMTPConnectError as e:
        logger.error(f"Ошибка подключения к SMTP серверу: {str(e)}")
        return EXIT_SMTP_CONNECTION_ERROR
    except smtplib.SMTPHeloError as e:
        logger.error(f"Ошибка приветствия SMTP сервера: {str(e)}")
        return EXIT_SMTP_CONNECTION_ERROR
    except smtplib.SMTPDataError as e:
        logger.error(f"Ошибка данных SMTP: {str(e)}")
        return EXIT_SMTP_SEND_ERROR
    except smtplib.SMTPException as e:
        logger.error(f"Ошибка SMTP: {str(e)}", exc_info=True)
        return EXIT_SMTP_SEND_ERROR
    except Exception as e:
        logger.error(f"Неизвестная ошибка при отправке письма: {str(e)}", exc_info=True)
        return EXIT_UNKNOWN_ERROR
    finally:
        if smtp_server:
            try:
                smtp_server.quit()
            except Exception as e:
                logger.warning(f"Ошибка при закрытии SMTP соединения: {str(e)}")


def read_auth_from_file(auth_file):
    """Читает данные авторизации из файла"""
    try:
        data = auth_file.read().strip()
        username, password = data.split(":")
        logger.info("Данные аутентификации успешно прочитаны из файла")
        return username, password
    except ValueError:
        logger.error(
            "Неверный формат данных в файле авторизации. Ожидается 'username:password'."
        )
        raise AuthError("Неверный формат данных в файле авторизации")
    except Exception as e:
        logger.error(f"Ошибка при чтении файла авторизации: {str(e)}")
        raise AuthError(f"Ошибка чтения файла авторизации: {str(e)}")
    finally:
        auth_file.close()


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
        except FileReadError as e:
            logger.warning(f"Не удалось прочитать файл с текстом: {str(e)}")
        except Exception as e:
            logger.warning(f"Ошибка чтения файла с текстом: {str(e)}")

    if args.text:
        logger.info("Используется текст из аргумента --text")
        return add_signature(args.text, args.sender)

    logger.info("Используется автосгенерированный текст письма")
    return generate_default_email_body(file_paths, args.sender)


def parse_file_paths(
    file_paths_str: str, files_list_path: Optional[Path] = None
) -> Tuple[List[Path], int]:
    """Разбирает пути к файлам из строки или из файла со списком.
    Возвращает кортеж (список файлов, код ошибки)"""
    file_paths = []

    if files_list_path:
        if not validate_file_path(files_list_path):
            return [], EXIT_FILE_NOT_FOUND

        try:
            with files_list_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        path = Path(line)
                        if not validate_file_path(path):
                            return [], EXIT_FILE_NOT_FOUND
                        file_paths.append(path)
            logger.info(f"Прочитано {len(file_paths)} файлов из списка")
        except Exception as e:
            logger.error(f"Ошибка при чтении файла со списком: {str(e)}")
            return [], EXIT_FILE_READ_ERROR

        if not file_paths:
            logger.error("Файл со списком не содержит валидных файлов")
            return [], EXIT_NO_FILES

        return file_paths, EXIT_SUCCESS

    if not file_paths_str.strip():
        logger.error("Не указаны файлы для отправки")
        return [], EXIT_NO_FILES

    for file_path in file_paths_str.split(","):
        file_path = file_path.strip()
        if not file_path:
            continue

        path = Path(file_path)
        if not validate_file_path(path):
            return [], EXIT_FILE_NOT_FOUND
        file_paths.append(path)

    if not file_paths:
        logger.error("Не указаны валидные файлы для отправки")
        return [], EXIT_NO_FILES

    logger.info(f"Подготовлено {len(file_paths)} файлов для отправки")
    return file_paths, EXIT_SUCCESS


def setup_logging(log_file: Optional[str] = None) -> None:
    """Настраивает логирование."""
    handlers = [logging.StreamHandler()]

    if log_file is not None:  # Если параметр --log был передан (даже без значения)
        try:
            # Используем переданное имя файла или DEFAULT_LOGFILE, если имя не указано
            log_filename = log_file if log_file != "" else DEFAULT_LOGFILE
            handlers.append(logging.FileHandler(log_filename))
            logger.info(f"Логирование настроено, файл логов: {log_filename}")
        except Exception as e:
            logger.error(f"Ошибка настройки файлового логгера: {str(e)}")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )


def setup_arg_parser() -> argparse.ArgumentParser:
    """Настраивает парсер аргументов командной строки."""
    return_codes_help = """
Коды возврата:
  {EXIT_SUCCESS} - Успешное выполнение
  {EXIT_ARGUMENT_ERROR} - Ошибка в аргументах командной строки
  {EXIT_FILE_NOT_FOUND} - Файл не найден
  {EXIT_FILE_READ_ERROR} - Ошибка чтения файла
  {EXIT_ATTACHMENT_ERROR} - Ошибка прикрепления файлов
  {EXIT_SMTP_CONNECTION_ERROR} - Ошибка подключения к SMTP серверу
  {EXIT_SMTP_AUTH_ERROR} - Ошибка аутентификации на SMTP сервере
  {EXIT_SMTP_SEND_ERROR} - Ошибка отправки письма
  {EXIT_INVALID_EMAIL} - Невалидный email адрес
  {EXIT_NO_FILES} - Не указаны файлы для отправки
  {EXIT_UNKNOWN_ERROR} - Неизвестная ошибка
""".format(
        EXIT_SUCCESS=EXIT_SUCCESS,
        EXIT_ARGUMENT_ERROR=EXIT_ARGUMENT_ERROR,
        EXIT_FILE_NOT_FOUND=EXIT_FILE_NOT_FOUND,
        EXIT_FILE_READ_ERROR=EXIT_FILE_READ_ERROR,
        EXIT_ATTACHMENT_ERROR=EXIT_ATTACHMENT_ERROR,
        EXIT_SMTP_CONNECTION_ERROR=EXIT_SMTP_CONNECTION_ERROR,
        EXIT_SMTP_AUTH_ERROR=EXIT_SMTP_AUTH_ERROR,
        EXIT_SMTP_SEND_ERROR=EXIT_SMTP_SEND_ERROR,
        EXIT_INVALID_EMAIL=EXIT_INVALID_EMAIL,
        EXIT_NO_FILES=EXIT_NO_FILES,
        EXIT_UNKNOWN_ERROR=EXIT_UNKNOWN_ERROR,
    )

    parser = argparse.ArgumentParser(
        description="Утилита для отправки писем с вложениями.\n\n" + return_codes_help,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Группа для взаимно исключающих аргументов файлов
    files_group = parser.add_mutually_exclusive_group(required=True)
    files_group.add_argument("-a", "--files", help="Файлы для вложения (через запятую)")
    files_group.add_argument(
        "--files-list",
        type=Path,
        help="Файл со списком файлов для вложения (по одному на строку)",
    )

    # Остальные обязательные параметры
    parser.add_argument("-s", "--server", required=True, help="SMTP сервер")
    parser.add_argument(
        "-p", "--port", required=True, type=int, help="Порт SMTP сервера"
    )
    parser.add_argument("-t", "--to", required=True, help="Email получателя")
    parser.add_argument("-f", "--from", dest="sender", nargs="?",const=ADMIN_MAIL help="Email отправителя")
    parser.add_argument(
        "-j", "--subject", default="Письмо с вложениями", help="Тема письма"
    )
    parser.add_argument("-b", "--text", help="Текст письма")
    parser.add_argument("-bf", "--text-file", type=Path, help="Файл с текстом письма")
    parser.add_argument(
        "-uf",
        "--auth-file",
        type=argparse.FileType("r"),
        help="Файл с данными аутентификации (логин:пароль)",
    )
    parser.add_argument(
        "-u", "--auth", help="Данные аутентификации в формате логин:пароль"
    )
    parser.add_argument("-S", "--ssl", action="store_true", help="Использовать SSL")
    parser.add_argument(
        "-l",
        "--log",
        nargs="?",  # делает аргумент необязательным, но позволяет указать значение
        const=DEFAULT_LOGFILE,  # значение по умолчанию, если параметр указан без значения
        help=f"Файл для сохранения логов (по умолчанию: {DEFAULT_LOGFILE})",
    )
    return parser


def main() -> int:
    """Основная функция выполнения скрипта."""
    try:
        parser = setup_arg_parser()
        args = parser.parse_args()

        # Настройка логирования (делаем это в первую очередь)
        setup_logging(args.log)

        logger.info("Запуск скрипта отправки email")
        logger.debug(f"Аргументы командной строки: {args}")

        # Проверка конфликтующих аргументов
        if args.text and args.text_file:
            logger.error(
                "Ошибка: нельзя использовать одновременно --text и --text-file"
            )
            return EXIT_ARGUMENT_ERROR

        if args.auth and args.auth_file:
            logger.error(
                "Ошибка: нельзя использовать одновременно --auth и --auth-file"
            )
            return EXIT_ARGUMENT_ERROR

        # Валидация email
        if args.sender and not validate_email(args.sender):
            logger.error(f"Невалидный email отправителя: {args.sender}")
            return EXIT_INVALID_EMAIL

        if not validate_email(args.to):
            logger.error(f"Невалидный email получателя: {args.to}")
            return EXIT_INVALID_EMAIL

        # Получение списка файлов
        file_paths, error_code = parse_file_paths(
            args.files if hasattr(args, "files") else "",
            args.files_list if hasattr(args, "files_list") else None,
        )
        if error_code != EXIT_SUCCESS:
            return error_code

        # Подготовка текста письма
        try:
            body = get_email_body(args, file_paths)
            message = create_message(
                args.sender or ADMIN_MAIL, args.to, args.subject, body
            )
        except EmailSenderError as e:
            logger.error(f"Ошибка подготовки письма: {str(e)}")
            return EXIT_UNKNOWN_ERROR

        # Добавление вложений
        if not attach_files(message, file_paths):
            logger.error("Ошибка при добавлении одного или нескольких вложений")
            return EXIT_ATTACHMENT_ERROR

        # Отправка письма
        try:
            error_code = send_email(
                args.server,
                args.port,
                args.sender or ADMIN_MAIL,
                args.to,
                message,
                args.ssl,
                auth=args.auth,
                auth_file=args.auth_file,
            )
            if error_code != EXIT_SUCCESS:
                return error_code
        except AuthError as e:
            logger.error(f"Ошибка аутентификации: {str(e)}")
            return EXIT_SMTP_AUTH_ERROR
        except Exception as e:
            logger.error(f"Неизвестная ошибка при отправке: {str(e)}")
            return EXIT_UNKNOWN_ERROR

        logger.info("Скрипт успешно завершил работу")
        return EXIT_SUCCESS

    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}", exc_info=True)
        return EXIT_UNKNOWN_ERROR


if __name__ == "__main__":
    sys.exit(main())
