# DineIQ\Backend\services\email.py

# ---------------------------------------------------------
# Library and Packages Import
# ---------------------------------------------------------
import os
import socket
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class _IPv4SMTP_SSL(smtplib.SMTP_SSL):
    """
    Some hosts (Render included) resolve smtp.gmail.com to an IPv6 address
    they have no outbound route for, failing with
    "[Errno 101] Network is unreachable". Force IPv4 resolution instead.
    """
    def _get_socket(self, host, port, timeout):
        addr_info = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
        ip = addr_info[0][4][0]
        new_socket = socket.create_connection((ip, port), timeout, self.source_address)
        return self.context.wrap_socket(new_socket, server_hostname=host)

# ---------------------------------------------------------
# Load environment variables from .env file
# ---------------------------------------------------------
from dotenv import load_dotenv
load_dotenv()


# ---------------------------------------------------------
# Class definition for Gmail interactions
# ---------------------------------------------------------
class GmailClient:

    # -------------------------------------------------------------------
    # 🔧 SETUP: Gmail SMTP (App Password)
    # 
    # Instead of OAuth, we use an App Password which works reliably on servers.
    # 1. Go to Google Account -> Security -> 2-Step Verification
    # 2. Scrolls to bottom -> App Passwords
    # 3. Create new app name "DineIQ" -> Copy the 16-char password
    # 4. Update .env with:
    #    GMAIL_USER="your-email@gmail.com"
    #    GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
    # -------------------------------------------------------------------

    def __init__(self):
        """
        Initialize GmailClient with credentials from environment variables.
        """
        self.gmail_user = os.getenv("GMAIL_USER")
        self.gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")

    # -------------------------------------------------------------------
    # ✉️ Send Email
    # -------------------------------------------------------------------
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
    ):
        """
        Send a plain-text email using Gmail SMTP.
        """
        if not self.gmail_user or not self.gmail_app_password:
            print("❌ GMAIL_USER or GMAIL_APP_PASSWORD not set in .env")
            raise ValueError("Gmail credentials not configured.")

        # Create message container
        msg = MIMEMultipart()
        msg['From'] = self.gmail_user
        msg['To'] = to_email
        msg['Subject'] = subject

        # Attach body
        msg.attach(MIMEText(body, 'plain'))

        try:
            # Create secure SSL context
            context = ssl.create_default_context()
            
            # Connect to Gmail SMTP server
            with _IPv4SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(self.gmail_user, self.gmail_app_password)
                server.sendmail(self.gmail_user, to_email, msg.as_string())
                
            print(f"✅ Email sent to {to_email}")
            
        except Exception as e:
            print(f"🔥 Failed to send email: {e}")
            raise e

    # -------------------------------------------------------------------
    # 🔐 Send OTP (thin wrapper)
    # -------------------------------------------------------------------
    def send_otp_email(self, to_email: str, otp: str):
        self.send_email(
            to_email=to_email,
            subject="Your Login OTP",
            body=f"Your OTP is {otp}. Valid for 5 minutes.",
        )


# test hook
# if __name__ == "__main__":
#     self = GmailClient()
    
#     self.init_service()

#     self.send_otp_email(to_email="UmangHere@gmail.com", otp='123456')

    

