"""
HotServe — Email Utilities
Sends OTP emails for registration and password reset.
"""
 
from django.core.mail import send_mail
from django.conf import settings
 
 
def send_otp_email(email, otp_code, purpose):
    """Send a nicely formatted OTP email."""
 
    if purpose == 'registration':
        subject = "🔥 Verify your HotServe account"
        message = f"""
Welcome to HotServe!
 
Your email verification code is:
 
    {otp_code}
 
This code expires in {settings.OTP_EXPIRY_MINUTES} minutes.
 
If you didn't create a HotServe account, ignore this email.
 
— The HotServe Team
        """.strip()
 
        html_message = f"""
        <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;background:#0A0A0A;color:#F0F0F0;border-radius:16px;overflow:hidden;">
            <div style="background:linear-gradient(135deg,#FF4500,#FF8C00);padding:28px;text-align:center;">
                <div style="font-size:36px;">🔥</div>
                <div style="font-size:24px;font-weight:800;color:#fff;margin-top:8px;">HotServe</div>
            </div>
            <div style="padding:32px;">
                <h2 style="color:#F0F0F0;margin-bottom:8px;">Verify your email</h2>
                <p style="color:#888;font-size:14px;margin-bottom:28px;">Enter this code to complete your registration:</p>
                <div style="background:#1A1A1A;border:2px solid #FF4500;border-radius:12px;padding:24px;text-align:center;margin-bottom:24px;">
                    <div style="font-size:40px;font-weight:800;color:#FF6B35;letter-spacing:8px;">{otp_code}</div>
                </div>
                <p style="color:#888;font-size:12px;text-align:center;">Expires in {settings.OTP_EXPIRY_MINUTES} minutes. Do not share this code.</p>
            </div>
        </div>
        """
 
    elif purpose == 'password_reset':
        subject = "🔑 Reset your HotServe password"
        message = f"""
HotServe Password Reset
 
Your password reset code is:
 
    {otp_code}
 
This code expires in {settings.OTP_EXPIRY_MINUTES} minutes.
 
If you didn't request a password reset, ignore this email.
 
— The HotServe Team
        """.strip()
 
        html_message = f"""
        <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;background:#0A0A0A;color:#F0F0F0;border-radius:16px;overflow:hidden;">
            <div style="background:linear-gradient(135deg,#FF4500,#FF8C00);padding:28px;text-align:center;">
                <div style="font-size:36px;">🔥</div>
                <div style="font-size:24px;font-weight:800;color:#fff;margin-top:8px;">HotServe</div>
            </div>
            <div style="padding:32px;">
                <h2 style="color:#F0F0F0;margin-bottom:8px;">Reset your password</h2>
                <p style="color:#888;font-size:14px;margin-bottom:28px;">Use this code to reset your password:</p>
                <div style="background:#1A1A1A;border:2px solid #4A9EFF;border-radius:12px;padding:24px;text-align:center;margin-bottom:24px;">
                    <div style="font-size:40px;font-weight:800;color:#4A9EFF;letter-spacing:8px;">{otp_code}</div>
                </div>
                <p style="color:#888;font-size:12px;text-align:center;">Expires in {settings.OTP_EXPIRY_MINUTES} minutes. Do not share this code.</p>
            </div>
        </div>
        """
 
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Email send error: {e}")
        return False
 