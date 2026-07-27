import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import sys
import os

def check_brevo_detailed():
    print("🔍 Investigating Brevo SMTP for autosemana@gmail.com...")
    
    # Credentials from config
    smtp_server = "smtp-relay.brevo.com"
    smtp_port = 587
    smtp_user = "951480002@smtp-brevo.com"
    api_key = "YOUR_BREVO_SMTP_KEY"
    sender_email = "info@fgjmedios.com"
    recipient = "autosemana@gmail.com"
    
    try:
        print(f"Connecting to {smtp_server}:{smtp_port}...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.set_debuglevel(1) # Enable debug output to see SMTP conversation
        server.starttls()
        print("Logging in...")
        server.login(smtp_user, api_key)
        
        print(f"Sending test email from {sender_email} to {recipient}...")
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient
        msg['Subject'] = "🔍 Debug Brevo: Prueba de Conectividad"
        msg.attach(MIMEText("Esta es una prueba de depuración para verificar por qué no llegan los correos. Si recibes esto, el flujo SMTP básico funciona.", 'plain'))
        
        server.send_message(msg)
        server.quit()
        print("\n✅ SMTP session finished successfully.")
        
    except Exception as e:
        print(f"\n❌ ERROR during SMTP session: {e}")

if __name__ == "__main__":
    check_brevo_detailed()
