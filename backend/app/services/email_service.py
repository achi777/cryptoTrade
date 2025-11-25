"""
Email Service - Handles all email communications.
"""

from flask import current_app, render_template_string
from flask_mail import Message
from app import mail


def send_email(to: str, subject: str, html_body: str):
    """Send an email"""
    try:
        msg = Message(
            subject=subject,
            recipients=[to],
            html=html_body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER')
        )
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f"Failed to send email to {to}: {e}")
        raise


def send_verification_email(email: str, token: str):
    """Send email verification link"""
    verification_url = f"{current_app.config.get('FRONTEND_URL', 'http://localhost:3000')}/verify-email?token={token}"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .button {{ display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Welcome to CryptoTrade!</h1>
            <p>Thank you for registering. Please verify your email address by clicking the button below:</p>
            <p style="text-align: center;">
                <a href="{verification_url}" class="button">Verify Email</a>
            </p>
            <p>Or copy and paste this link into your browser:</p>
            <p>{verification_url}</p>
            <p>This link will expire in 24 hours.</p>
            <div class="footer">
                <p>If you didn't create an account with CryptoTrade, please ignore this email.</p>
            </div>
        </div>
    </body>
    </html>
    """

    send_email(email, "Verify Your CryptoTrade Account", html)


def send_password_reset_email(email: str, token: str):
    """Send password reset link"""
    reset_url = f"{current_app.config.get('FRONTEND_URL', 'http://localhost:3000')}/reset-password?token={token}"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .button {{ display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Password Reset Request</h1>
            <p>We received a request to reset your password. Click the button below to create a new password:</p>
            <p style="text-align: center;">
                <a href="{reset_url}" class="button">Reset Password</a>
            </p>
            <p>Or copy and paste this link into your browser:</p>
            <p>{reset_url}</p>
            <p>This link will expire in 1 hour.</p>
            <div class="footer">
                <p>If you didn't request a password reset, please ignore this email or contact support if you have concerns.</p>
            </div>
        </div>
    </body>
    </html>
    """

    send_email(email, "Reset Your CryptoTrade Password", html)


def send_withdrawal_confirmation(email: str, currency: str, amount: str, address: str):
    """Send withdrawal request confirmation"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .details {{ background-color: #f5f5f5; padding: 15px; border-radius: 4px; margin: 20px 0; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Withdrawal Request Submitted</h1>
            <p>Your withdrawal request has been submitted and is being processed.</p>
            <div class="details">
                <p><strong>Currency:</strong> {currency}</p>
                <p><strong>Amount:</strong> {amount}</p>
                <p><strong>To Address:</strong> {address}</p>
            </div>
            <p>You will receive another email once the withdrawal is completed.</p>
            <div class="footer">
                <p>If you did not initiate this withdrawal, please contact support immediately.</p>
            </div>
        </div>
    </body>
    </html>
    """

    send_email(email, f"Withdrawal Request: {amount} {currency}", html)


def send_deposit_notification(email: str, currency: str, amount: str, tx_hash: str):
    """Send deposit received notification"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .details {{ background-color: #d4edda; padding: 15px; border-radius: 4px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Deposit Received!</h1>
            <p>Your deposit has been credited to your account.</p>
            <div class="details">
                <p><strong>Currency:</strong> {currency}</p>
                <p><strong>Amount:</strong> {amount}</p>
                <p><strong>Transaction Hash:</strong> {tx_hash}</p>
            </div>
            <p>Your funds are now available for trading.</p>
        </div>
    </body>
    </html>
    """

    send_email(email, f"Deposit Received: {amount} {currency}", html)


def send_login_notification(email: str, ip_address: str, device: str):
    """Send new login notification"""
    from datetime import datetime

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .details {{ background-color: #f5f5f5; padding: 15px; border-radius: 4px; margin: 20px 0; }}
            .warning {{ background-color: #fff3cd; padding: 15px; border-radius: 4px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>New Login Detected</h1>
            <p>A new login to your CryptoTrade account was detected:</p>
            <div class="details">
                <p><strong>Time:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                <p><strong>IP Address:</strong> {ip_address}</p>
                <p><strong>Device:</strong> {device}</p>
            </div>
            <div class="warning">
                <p>If this wasn't you, please secure your account immediately by changing your password and enabling 2FA.</p>
            </div>
        </div>
    </body>
    </html>
    """

    send_email(email, "New Login to Your CryptoTrade Account", html)


def send_kyc_approved(email: str, level: int):
    """Send KYC approval notification"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .success {{ background-color: #d4edda; padding: 15px; border-radius: 4px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>KYC Verification Approved!</h1>
            <div class="success">
                <p>Congratulations! Your KYC verification for Level {level} has been approved.</p>
            </div>
            <p>You now have access to higher withdrawal limits and additional features.</p>
        </div>
    </body>
    </html>
    """

    send_email(email, "KYC Verification Approved", html)


def send_kyc_rejected(email: str, reason: str):
    """Send KYC rejection notification"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .error {{ background-color: #f8d7da; padding: 15px; border-radius: 4px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>KYC Verification Update</h1>
            <p>Unfortunately, your KYC verification request was not approved.</p>
            <div class="error">
                <p><strong>Reason:</strong> {reason}</p>
            </div>
            <p>Please review the requirements and submit a new verification request.</p>
        </div>
    </body>
    </html>
    """

    send_email(email, "KYC Verification Update", html)
