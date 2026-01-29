import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid

from dotenv import load_dotenv

load_dotenv()


class EmailService:
    def __init__(self):
        """
        Setup für SMTP (eigener Mailserver).
        Die Zugangsdaten müssen in der .env stehen.
        """
        self.smtp_server = os.getenv("SMTP_SERVER", "mailserver")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "user@example.com")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "password")
        self.sender_email = os.getenv("SMTP_FROM_EMAIL", "noreply@example.com")
        self.sender_name = "Podcast Generator KI"

    def _get_html_template(self, token):
        """
        Ein richtiges HTML-Template, damit das professionell aussieht (Material Design Style).
        """
        return f"""
        <html>
            <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background-color: #f4f4f4; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                    <div style="background: #6200ee; padding: 20px; text-align: center; color: white;">
                        <h1 style="margin: 0; font-size: 24px;">Podcast Generator KI</h1>
                    </div>
                    <div style="padding: 30px; text-align: center;">
                        <h2 style="color: #6200ee;">Dein Login-Code</h2>
                        <p>Moin!</p>
                        <p>Hier ist dein Code, um dich einzuloggen. Er ist <b>15 Minuten</b> lang gültig.</p>

                        <div style="margin: 30px 0; padding: 20px; background: #f0f0f0; border-radius: 4px; font-family: monospace; font-size: 32px; letter-spacing: 5px; font-weight: bold; color: #333;">
                            {token}
                        </div>

                        <p style="font-size: 14px; color: #666;">
                            Wenn du das nicht warst, kannst du die Mail einfach löschen.
                        </p>
                    </div>
                    <div style="background: #f9f9f9; padding: 15px; text-align: center; font-size: 12px; color: #999; border-top: 1px solid #eeeeee;">
                        &copy; 2026 Podcast Generator Projekt-Team
                    </div>
                </div>
            </body>
        </html>
        """

    def send_login_token(self, to_email, token):
        """
        Verschickt die Mail über den konfigurierten SMTP Server.
        """
        # Erstelle die Nachricht
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Dein Login-Code: {token}"
        msg["From"] = f"{self.sender_name} <{self.sender_email}>"
        msg["To"] = to_email
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()

        text = f"Moin! Dein Code ist: {token}"
        html = self._get_html_template(token)

        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")

        msg.attach(part1)
        msg.attach(part2)

        try:
            # Verbindung zum SMTP Server herstellen
            # Bei Port 465 SSL nutzen
            if self.smtp_port == 465:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    self.smtp_server, self.smtp_port, context=context
                ) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.sendmail(self.sender_email, to_email, msg.as_string())
            else:
                # Bei Port 587 oder 25
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.set_debuglevel(1)

                    if self.smtp_port != 25:
                        server.starttls()
                        server.login(self.smtp_user, self.smtp_password)

                    # Bei Port 25 senden wir einfach ohne Login (Server muss das erlauben)
                    server.sendmail(self.sender_email, to_email, msg.as_string())

            return True

        except Exception as e:
            print(f"SMTP Fehler: E-Mail senden ist abgeschmiert: {e}")
            return False
