import sys
import os
import argparse
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


LETTERSIHNATURE = """______________________________________________________________
Это письмо сформировано автоматически роботом отправки данных.
Отвечать на него не нужно, да и бесполезно."""

ADMINMAIL = 'Email для связи с администратором: admin@slenergo.ru'

def main():
    parser = argparse.ArgumentParser(description='Утилита для отправки писем с вложениями')
    
    # Обязательные параметры
    parser.add_argument('--server', required=True, help='SMTP сервер')
    parser.add_argument('--port', required=True, type=int, help='Порт SMTP сервера')
    parser.add_argument('--from', default='noreply@slenergo.ru', dest='sender', help='Email отправителя')
    parser.add_argument('--to', required=True, help='Email получателя')
    parser.add_argument('--files', required=True, help='Файлы для вложения (через запятую)')
    
    # Необязательные параметры
    parser.add_argument('--subject', default='Вам отправлен файл(ы)', help='Тема письма')
    parser.add_argument('--text', help='Текст письма')
    parser.add_argument('--auth', help='Логин и пароль (user:pass)')
    parser.add_argument('--ssl', action='store_true', help='Использовать SSL/TLS')
    
    args = parser.parse_args()

    # Генерация текста письма по умолчанию
    if not args.text:
        files = args.files.split(',')
        args.text = "Вам отправлены файлы:\n" + "\n".join(
            f"{i+1}. {os.path.basename(f)}" for i, f in enumerate(files))

    # Добавление подписи в письмо
        args.text += f"""\n{LETTERSIHNATURE}\n{ADMINMAIL}"""
    
    
    
    # Создание письма
    message= MIMEMultipart()
    message['From'] = args.sender
    message['To'] = args.to
    message['Subject'] = args.subject
    
    # Добавление текста
    message.attach(MIMEText(args.text, 'plain', 'utf-8'))
    
    # Добавление вложений
    for file_path in args.files.split(','):
        try:
            with open(file_path.strip(), 'rb') as f:
                part = MIMEApplication(
                    f.read(),
                    Name=os.path.basename(file_path))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                message.attach(part)
        except Exception as e:
            print(f"Ошибка при добавлении вложения {file_path}: {str(e)}")
            return 1
    
    # Отправка письма
    try:
        if args.ssl:
            server = smtplib.SMTP_SSL(args.server, args.port)
        else:
            server = smtplib.SMTP(args.server, args.port)
        
        if args.auth:
            username, password = args.auth.split(':')
            server.login(username, password)
        
        server.send_message(message)
        server.quit()
        print("Письмо успешно отправлено!")
        return 0
    except Exception as e:
        print(f"Ошибка при отправке письма: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())