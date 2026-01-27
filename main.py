"""
Discord Self-Bot Alert Emailer

⚠️ WARNING: Using a user token (self-bot) violates Discord's Terms of Service.
   Your account may be suspended or banned. Use at your own risk.

Monitors specified Discord channels and sends email alerts for new messages.
"""

import asyncio
import logging
import os
import signal
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import aiosmtplib
import discord
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
CHANNEL_IDS = [
    int(cid.strip())
    for cid in os.getenv("CHANNEL_IDS", "").split(",")
    if cid.strip()
]
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class SelfBot(discord.Client):
    """Self-bot client that listens for messages in specified channels."""

    def __init__(self, channel_ids: list[int], **kwargs):
        super().__init__(**kwargs)
        self.channel_ids = set(channel_ids)
        self._shutdown_event = asyncio.Event()

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Monitoring {len(self.channel_ids)} channel(s): {self.channel_ids}")

    async def on_message(self, message: discord.Message):
        # Filter: only process messages from monitored channels
        if message.channel.id not in self.channel_ids:
            return

        logger.info(
            f"New message in #{message.channel.name} by {message.author}: "
            f"{message.content[:50]}{'...' if len(message.content) > 50 else ''}"
        )

        # Send email alert
        await self.send_email_alert(message)

    async def send_email_alert(self, message: discord.Message):
        """Format and send an email alert for the given message."""
        # Build message link
        guild_id = message.guild.id if message.guild else "@me"
        message_link = f"https://discord.com/channels/{guild_id}/{message.channel.id}/{message.id}"

        # Email subject
        channel_name = getattr(message.channel, "name", "DM")
        subject = f"🔔 Discord Alert: #{channel_name}"

        # Email body (HTML)
        html_body = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #5865F2; margin-bottom: 20px;">New Discord Message</h2>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr>
                    <td style="padding: 8px 0; color: #666; width: 100px;">Channel</td>
                    <td style="padding: 8px 0; font-weight: 500;">#{channel_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Author</td>
                    <td style="padding: 8px 0; font-weight: 500;">{message.author.display_name} (@{message.author.name})</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Time</td>
                    <td style="padding: 8px 0;">{message.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                </tr>
            </table>
            <div style="background: #f4f4f5; border-left: 4px solid #5865F2; padding: 15px; margin-bottom: 20px; white-space: pre-wrap; word-wrap: break-word;">
                {message.content or '<em style="color: #999;">No text content (may contain embeds/attachments)</em>'}
            </div>
            <a href="{message_link}" style="display: inline-block; background: #5865F2; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">
                Open in Discord
            </a>
        </div>
        """

        # Plain text fallback
        plain_body = f"""
New Discord Message

Channel: #{channel_name}
Author: {message.author.display_name} (@{message.author.name})
Time: {message.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

Message:
{message.content or '[No text content]'}

Link: {message_link}
        """.strip()

        # Build email
        email = MIMEMultipart("alternative")
        email["Subject"] = subject
        email["From"] = EMAIL_FROM
        email["To"] = EMAIL_TO
        email.attach(MIMEText(plain_body, "plain"))
        email.attach(MIMEText(html_body, "html"))

        try:
            await aiosmtplib.send(
                email,
                hostname=SMTP_HOST,
                port=SMTP_PORT,
                username=SMTP_USER,
                password=SMTP_PASS,
                start_tls=True,
            )
            logger.info(f"Email alert sent to {EMAIL_TO}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")

    async def shutdown(self):
        """Gracefully shut down the bot."""
        logger.info("Shutting down...")
        self._shutdown_event.set()
        await self.close()


async def main():
    # Validate configuration
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN is not set in .env")
        sys.exit(1)
    if not CHANNEL_IDS:
        logger.error("CHANNEL_IDS is not set in .env")
        sys.exit(1)
    if not all([SMTP_USER, SMTP_PASS, EMAIL_FROM, EMAIL_TO]):
        logger.error("SMTP/Email configuration incomplete in .env")
        sys.exit(1)

    # Create client
    client = SelfBot(channel_ids=CHANNEL_IDS)

    # Handle graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler():
        asyncio.create_task(client.shutdown())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    # Start the bot
    logger.info("Starting Discord self-bot listener...")
    try:
        await client.start(DISCORD_TOKEN)
    except discord.LoginFailure:
        logger.error("Invalid Discord token. Please check your DISCORD_TOKEN in .env")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
