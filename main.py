"""
Discord Self-Bot Alert System (Email + VoIP)

⚠️ WARNING: Using a user token (self-bot) violates Discord's Terms of Service.
   Your account may be suspended or banned. Use at your own risk.

Monitors specified Discord channels and sends alerts via:
- Email: One email per message (always)
- VoIP: One call per cooldown window (optional, prevents spam)
"""

import asyncio
import logging
import os
import shutil
import signal
import sys
import time
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

# VoIP Configuration (optional - set VOIP_ENABLED=true to activate)
VOIP_ENABLED = os.getenv("VOIP_ENABLED", "false").lower() == "true"
VOIP_SIP_USER = os.getenv("VOIP_SIP_USER", "")
VOIP_SIP_PASS = os.getenv("VOIP_SIP_PASS", "")
VOIP_SIP_DOMAIN = os.getenv("VOIP_SIP_DOMAIN", "sip.linphone.org")
VOIP_CALL_TARGET = os.getenv("VOIP_CALL_TARGET", "")  # SIP URI to call, e.g. sip:youruser@sip.linphone.org
VOIP_COOLDOWN_SECONDS = int(os.getenv("VOIP_COOLDOWN_SECONDS", "60"))  # Min seconds between calls
VOIP_CLI_PATH = os.getenv("VOIP_CLI_PATH", "baresip")  # Path to SIP CLI tool
VOIP_CALL_DURATION = int(os.getenv("VOIP_CALL_DURATION", "60"))  # How long to ring (seconds)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class VoipCaller:
    """
    Handles VoIP call alerts using baresip SIP CLI tool.
    
    Implements a cooldown/burst gate to prevent call spam when multiple
    messages arrive rapidly.
    """

    def __init__(
        self,
        cli_path: str,
        sip_user: str,
        sip_pass: str,
        sip_domain: str,
        call_target: str,
        cooldown_seconds: int,
        call_duration: int,
    ):
        self.cli_path = cli_path
        self.sip_user = sip_user
        self.sip_pass = sip_pass
        self.sip_domain = sip_domain
        self.call_target = call_target
        self.cooldown_seconds = cooldown_seconds
        self.call_duration = call_duration
        self._last_call_time: float = 0
        self._call_lock = asyncio.Lock()
        self._config_dir = os.path.expanduser("~/.baresip")

    def is_available(self) -> bool:
        """Check if the SIP CLI tool is installed and accessible."""
        return shutil.which(self.cli_path) is not None

    def _can_call(self) -> bool:
        """Check if cooldown has passed since last call."""
        return (time.time() - self._last_call_time) >= self.cooldown_seconds

    def _ensure_config(self) -> None:
        """Create baresip config directory and account file if needed."""
        os.makedirs(self._config_dir, exist_ok=True)
        
        # Account config - force UDP transport and disable SRTP
        accounts_file = os.path.join(self._config_dir, "accounts")
        account_line = f"<sip:{self.sip_user}@{self.sip_domain};transport=udp>;auth_pass={self.sip_pass};mediaenc=;"
        
        # Check if account already configured correctly
        if os.path.exists(accounts_file):
            with open(accounts_file, "r") as f:
                content = f.read()
                if self.sip_user in content and "transport=udp" in content:
                    return
        
        # Write account config
        with open(accounts_file, "w") as f:
            f.write(account_line + "\n")
        
        # Main config - force IPv4, set audio codecs
        config_file = os.path.join(self._config_dir, "config")
        config_content = """# Force IPv4
prefer_ipv6 no

# Audio settings  
audio_player coreaudio
audio_source coreaudio
audio_alert coreaudio

# Disable video
video_enable no
"""
        with open(config_file, "w") as f:
            f.write(config_content)
        
        logger.info(f"Created baresip config for {self.sip_user}@{self.sip_domain}")

    async def make_call(self) -> bool:
        """
        Attempt to place a VoIP call using baresip.
        
        Returns True if call was initiated, False otherwise.
        Respects cooldown to prevent spam.
        """
        # #region agent log
        import json
        def _debug_log(hyp_id, msg, data):
            with open("/Users/saadings/Desktop/discord-alerts/.cursor/debug.log", "a") as f:
                f.write(json.dumps({"hypothesisId": hyp_id, "location": "main.py:make_call", "message": msg, "data": data, "timestamp": time.time()}) + "\n")
        # #endregion
        
        async with self._call_lock:
            # Check cooldown
            if not self._can_call():
                remaining = self.cooldown_seconds - (time.time() - self._last_call_time)
                logger.debug(f"VoIP call skipped (cooldown: {remaining:.0f}s remaining)")
                return False

            # Ensure config exists
            self._ensure_config()
            
            # #region agent log
            # Log account config being used (Hypothesis E: config parse error)
            accounts_path = os.path.join(self._config_dir, "accounts")
            try:
                with open(accounts_path, "r") as f:
                    account_content = f.read()
                _debug_log("E", "Account config content", {"accounts_file": account_content.strip(), "call_target": self.call_target})
            except Exception as e:
                _debug_log("E", "Failed to read accounts", {"error": str(e)})
            # #endregion

            logger.info(f"Initiating VoIP call to {self.call_target}")

            try:
                # #region agent log
                _debug_log("D", "Starting baresip", {"cli_path": self.cli_path, "config_dir": self._config_dir, "wait_time": 3})
                # #endregion
                
                # Start baresip interactively (no -e flag, so it stays running)
                proc = await asyncio.create_subprocess_exec(
                    self.cli_path,
                    "-f", self._config_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    stdin=asyncio.subprocess.PIPE,
                )

                # Wait for baresip to initialize and register
                await asyncio.sleep(3)
                
                # #region agent log
                _debug_log("D", "After 3s wait, sending dial", {"call_target": self.call_target})
                # #endregion

                # Send dial command
                logger.info(f"Dialing {self.call_target}...")
                proc.stdin.write(f"/dial {self.call_target}\n".encode())
                await proc.stdin.drain()

                # Let it ring for the configured duration
                logger.info(f"Call initiated, ringing for {self.call_duration}s...")
                await asyncio.sleep(self.call_duration)

                # Send hangup and quit commands
                try:
                    proc.stdin.write(b"/hangup\n")
                    await proc.stdin.drain()
                    await asyncio.sleep(1)
                    proc.stdin.write(b"/quit\n")
                    await proc.stdin.drain()
                except Exception:
                    pass

                # Give it a moment to clean up, then force terminate
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    proc.terminate()
                    await asyncio.sleep(0.5)
                    if proc.returncode is None:
                        proc.kill()
                
                # #region agent log
                # Capture stdout/stderr for debugging (Hypothesis A,B,C: media negotiation)
                try:
                    stdout_data = await proc.stdout.read() if proc.stdout else b""
                    stderr_data = await proc.stderr.read() if proc.stderr else b""
                    _debug_log("ABC", "Baresip output after call", {
                        "stdout": stdout_data.decode('utf-8', errors='replace')[-2000:],
                        "stderr": stderr_data.decode('utf-8', errors='replace')[-2000:],
                        "returncode": proc.returncode
                    })
                except Exception as e:
                    _debug_log("ABC", "Failed to capture baresip output", {"error": str(e)})
                # #endregion

                # Update last call time
                self._last_call_time = time.time()
                logger.info(f"VoIP call completed (rang for {self.call_duration}s)")
                return True

            except FileNotFoundError:
                # #region agent log
                _debug_log("ERR", "CLI not found", {"cli_path": self.cli_path})
                # #endregion
                logger.error(f"CLI not found: {self.cli_path}")
                return False
            except Exception as e:
                # #region agent log
                _debug_log("ERR", "VoIP call exception", {"error": str(e), "type": type(e).__name__})
                # #endregion
                logger.error(f"VoIP call error: {e}")
                return False

    async def trigger_call_if_ready(self) -> bool:
        """
        Trigger a call if the cooldown has passed.
        
        This is the main entry point for the burst gate logic.
        Returns True if a call was made, False if skipped due to cooldown.
        """
        if not self._can_call():
            return False
        return await self.make_call()


class SelfBot(discord.Client):
    """Self-bot client that listens for messages in specified channels."""

    def __init__(
        self,
        channel_ids: list[int],
        voip_caller: VoipCaller | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.channel_ids = set(channel_ids)
        self.voip_caller = voip_caller
        self._shutdown_event = asyncio.Event()

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Monitoring {len(self.channel_ids)} channel(s): {self.channel_ids}")
        if self.voip_caller:
            logger.info(f"VoIP alerts enabled (cooldown: {self.voip_caller.cooldown_seconds}s)")

    async def on_message(self, message: discord.Message):
        # Filter: only process messages from monitored channels
        if message.channel.id not in self.channel_ids:
            return

        logger.info(
            f"New message in #{message.channel.name} by {message.author}: "
            f"{message.content[:50]}{'...' if len(message.content) > 50 else ''}"
        )

        # Send email and VoIP call simultaneously
        if self.voip_caller:
            # Run both email and call in parallel
            asyncio.create_task(self._send_alerts_simultaneously(message))
        else:
            # No VoIP, just send email
            await self.send_email_alert(message)

    async def _send_alerts_simultaneously(self, message: discord.Message):
        """Send email and make VoIP call at the same time."""
        try:
            # Run email and call concurrently
            await asyncio.gather(
                self.send_email_alert(message),
                self._trigger_voip_call(),
                return_exceptions=True,  # Don't let one failure stop the other
            )
        except Exception as e:
            logger.error(f"Error sending alerts: {e}")

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

        # Retry with exponential backoff: 3 attempts, delays of 1s, 2s, 4s
        max_attempts = 3
        backoff_delays = [1, 2, 4]  # seconds

        for attempt in range(1, max_attempts + 1):
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
                return  # Success, exit the retry loop
            except Exception as e:
                if attempt < max_attempts:
                    delay = backoff_delays[attempt - 1]
                    logger.warning(
                        f"Email send failed (attempt {attempt}/{max_attempts}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Failed to send email after {max_attempts} attempts: {e}"
                    )

    async def _trigger_voip_call(self):
        """Attempt to trigger a VoIP call (respects cooldown)."""
        try:
            called = await self.voip_caller.trigger_call_if_ready()
            if not called:
                logger.debug("VoIP call skipped (cooldown active)")
        except Exception as e:
            logger.error(f"VoIP call error: {e}")

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

    # Setup VoIP caller if enabled
    voip_caller = None
    if VOIP_ENABLED:
        if not all([VOIP_SIP_USER, VOIP_SIP_PASS, VOIP_CALL_TARGET]):
            logger.error("VoIP is enabled but configuration incomplete in .env")
            logger.error("Required: VOIP_SIP_USER, VOIP_SIP_PASS, VOIP_CALL_TARGET")
            sys.exit(1)

        voip_caller = VoipCaller(
            cli_path=VOIP_CLI_PATH,
            sip_user=VOIP_SIP_USER,
            sip_pass=VOIP_SIP_PASS,
            sip_domain=VOIP_SIP_DOMAIN,
            call_target=VOIP_CALL_TARGET,
            cooldown_seconds=VOIP_COOLDOWN_SECONDS,
            call_duration=VOIP_CALL_DURATION,
        )

        if not voip_caller.is_available():
            logger.warning(
                f"VoIP CLI tool '{VOIP_CLI_PATH}' not found. "
                "Calls will fail. Install linphone or set VOIP_CLI_PATH."
            )
        else:
            logger.info(f"VoIP caller initialized (CLI: {VOIP_CLI_PATH})")

    # Create client
    client = SelfBot(channel_ids=CHANNEL_IDS, voip_caller=voip_caller)

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
