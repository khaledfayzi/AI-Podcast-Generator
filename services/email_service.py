import requests
import os
from dotenv import load_dotenv

load_dotenv()

class EmailService:
    def __init__(self):
        """
        Setup für Mailgun. Die Keys müssen halt in der .env stehen.
        """
        self.api_key = os.getenv("MAILGUN_API_KEY")
        self.domain = os.getenv("MAILGUN_DOMAIN")
        self.sender_name = "Podcast Generator KI"
        
        if not self.api_key or not self.domain:
            print("Huston, wir haben ein Problem: MAILGUN Keys fehlen in der .env!")

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
        Wenn kein Key da ist, printen wir es einfach nur in die Konsole (Mock-Mode).
        """
        if not self.api_key or not self.domain:
            print(f"--- [DEBUG] Email an {to_email} mit Code {token} ---")
            return True

        url = f"https://api.mailgun.net/v3/{self.domain}/messages"
        # Sandbox Domains brauchen postmaster als Absender, sonst zickt Mailgun rum
        sender = f"postmaster@{self.domain}"
        
        try:
            response = requests.post(
                url,
                auth=("api", self.api_key),
                data={
                    "from": f"{self.sender_name} <{sender}>",
                    "to": to_email,
                    "subject": f"Dein Login-Code: {token}",
                    "text": f"Moin! Dein Code ist: {token}",
                    "html": self._get_html_template(token)
                }
            )
            
            if response.status_code == 200:
                return True
            else:
                print(f"Mailgun hat genervt: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"E-Mail senden ist abgeschmiert: {e}")
            return False