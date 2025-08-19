import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.config import Config
from fastapi import BackgroundTasks
import logging

logger = logging.getLogger(__name__)

async def send_email(to_email: str, subject: str, body: str):
    """Базовая функция отправки email"""
    try:
        msg = MIMEMultipart()
        msg['From'] = Config.EMAIL_FROM
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        with smtplib.SMTP_SSL(Config.SMTP_HOST, Config.SMTP_PORT) as server:
            server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        raise

def send_verification_email_in_background(background_tasks: BackgroundTasks, to_email: str, token: str):
    """Добавляет задачу отправки письма в фоновые задачи"""
    verification_url = f"{Config.BASE_URL}/auth/verify-email?token={token}"
    
    subject = "Подтверждение электронной почты — Majestic RP"
    body = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: 'Roboto', Arial, sans-serif;
                line-height: 1.6;
                color: #1d1d1d;
                background-color: #f5f5f5;
                margin: 0;
                padding: 0;
            }}
            .wrapper {{
                max-width: 600px;
                margin: 40px auto;
                padding: 0 20px;
            }}
            .container {{
                background-color: #ffffff;
                border-radius: 12px;
                padding: 40px;
                box-shadow: 0 4px 24px rgba(0,0,0,0.08);
            }}
            .logo {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .logo img {{
                height: 40px;
            }}
            .header {{
                color: #e0015b;
                font-size: 28px;
                font-weight: bold;
                text-align: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 2px solid #f5f5f5;
            }}
            .content {{
                color: #5a5a5a;
                font-size: 16px;
                margin-bottom: 30px;
            }}
            .button-container {{
                text-align: center;
                margin: 35px 0;
            }}
            .button {{
                display: inline-block;
                padding: 15px 35px;
                background-color: #e0015b;
                color: #ffffff !important;
                text-decoration: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 16px;
                transition: background-color 0.3s;
            }}
            .button:hover {{
                background-color: #c0014b;
            }}
            .link-block {{
                background-color: #f5f5f5;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
                word-break: break-all;
                color: #2828b6;
                font-family: monospace;
                font-size: 14px;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 2px solid #f5f5f5;
                color: #707070;
                font-size: 14px;
            }}
            .highlight {{
                color: #e0015b;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="wrapper">
            <div class="container">
                <div class="logo">
                    <div class="header">Majestic RP</div>
                </div>
                
                <div class="content">
                    <p>Здравствуйте!</p>
                    
                    <p>Благодарим вас за регистрацию на портале по поддержке игроков по форму <span class="highlight">Majestic RP</span>. Мы рады приветствовать вас в нашем сообществе!</p>
                    
                    <p>Для активации вашего аккаунта и доступа ко всем функциям портала, пожалуйста, подтвердите ваш email-адрес.</p>
                    
                    <div class="button-container">
                        <a href="{verification_url}" class="button">Подтвердить email</a>
                    </div>
                    
                    <p>Если кнопка не работает, вы можете скопировать следующую ссылку и вставить её в адресную строку браузера:</p>
                    
                    <div class="link-block">
                        {verification_url}
                    </div>
                    
                    <div class="footer">
                        <p><strong>Важная информация:</strong></p>
                        <ul>
                            <li>Ссылка действительна в течение {Config.EMAIL_VERIFICATION_EXPIRE_MINUTES // 60} часов</li>
                            <li>Если вы не регистрировались на нашем портале, просто проигнорируйте это письмо</li>
                        </ul>
                        <p>С уважением,<br>Команда Majestic RP</p>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    background_tasks.add_task(send_email, to_email, subject, body)