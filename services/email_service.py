import os
import requests
from dotenv import load_dotenv

load_dotenv()


class EmailService:
    def __init__(self):
        """
        Setup für Mailgun API.
        Die Zugangsdaten müssen in der .env stehen.
        """
        self.api_key = os.getenv("MAILGUN_API_KEY")
        self.domain = os.getenv("MAILGUN_DOMAIN")
        self.sender_email = os.getenv("SMTP_FROM_EMAIL", f"noreply@{self.domain}")
        self.sender_name = "Podcast Generator KI"
        self.api_url = f"https://api.eu.mailgun.net/v3/{self.domain}/messages"

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
        Verschickt die Mail über die Mailgun API.
        """
        if not self.api_key or not self.domain:
            print("Mailgun Fehler: API_KEY oder DOMAIN fehlt in der .env")
            return False

        try:
            response = requests.post(
                self.api_url,
                auth=("api", self.api_key),
                data={
                    "from": f"{self.sender_name} <{self.sender_email}>",
                    "to": [to_email],
                    "subject": f"Dein Login-Code: {token}",
                    "text": f"Moin! Dein Code ist: {token}",
                    "html": self._get_html_template(token),
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return True
            else:
                print(f"Mailgun Fehler: Status {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"Mailgun Fehler: E-Mail senden ist fehlgeschlagen: {e}")
            return False
