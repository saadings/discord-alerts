"""
Quick test script to verify Discord connection works.
Also includes unit tests for email retry logic.
"""

import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch, MagicMock

import discord
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")

class TestBot(discord.Client):
    async def on_ready(self):
        print(f"✅ Successfully logged in as: {self.user} (ID: {self.user.id})")
        print(f"📊 Connected to {len(self.guilds)} server(s):")
        for guild in self.guilds:
            print(f"   • {guild.name}")
        print("\n🎧 Listening for messages... (Press Ctrl+C to stop)")
        print("-" * 50)

    async def on_message(self, message: discord.Message):
        # Skip own messages
        if message.author.id == self.user.id:
            return
        
        channel_name = getattr(message.channel, "name", "DM")
        print(f"📨 [{channel_name}] {message.author.display_name}: {message.content[:100]}")
        print(f"   Channel ID: {message.channel.id}")

async def main():
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN not set in .env")
        return
    
    print("🔄 Connecting to Discord...")
    client = TestBot()
    
    try:
        await client.start(DISCORD_TOKEN)
    except discord.LoginFailure:
        print("❌ Invalid token! Please check your DISCORD_TOKEN in .env")
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        await client.close()

class TestEmailRetry(unittest.TestCase):
    """Unit tests for email retry/backoff logic."""

    def setUp(self):
        # Import here to avoid circular issues
        from main import SelfBot
        self.SelfBot = SelfBot

    @patch("main.aiosmtplib.send")
    def test_email_succeeds_first_attempt(self, mock_send):
        """Email sends successfully on first attempt."""
        mock_send.return_value = None  # Success

        client = self.SelfBot(channel_ids=[123])
        message = self._create_mock_message()

        asyncio.run(client.send_email_alert(message))

        self.assertEqual(mock_send.call_count, 1)

    @patch("main.aiosmtplib.send")
    @patch("main.asyncio.sleep", new_callable=AsyncMock)
    def test_email_retries_on_failure(self, mock_sleep, mock_send):
        """Email retries with backoff after failures."""
        # Fail twice, then succeed
        mock_send.side_effect = [Exception("fail1"), Exception("fail2"), None]

        client = self.SelfBot(channel_ids=[123])
        message = self._create_mock_message()

        asyncio.run(client.send_email_alert(message))

        self.assertEqual(mock_send.call_count, 3)
        # Should have slept with backoff delays (1s, 2s)
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)

    @patch("main.aiosmtplib.send")
    @patch("main.asyncio.sleep", new_callable=AsyncMock)
    def test_email_fails_after_max_retries(self, mock_sleep, mock_send):
        """Email logs error after all retries exhausted."""
        # Fail all 3 attempts
        mock_send.side_effect = Exception("always fails")

        client = self.SelfBot(channel_ids=[123])
        message = self._create_mock_message()

        # Should not raise, just log error
        asyncio.run(client.send_email_alert(message))

        self.assertEqual(mock_send.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    def _create_mock_message(self):
        """Create a mock Discord message for testing."""
        message = MagicMock()
        message.guild = MagicMock()
        message.guild.id = 999
        message.channel = MagicMock()
        message.channel.id = 123
        message.channel.name = "test-channel"
        message.id = 456
        message.author = MagicMock()
        message.author.display_name = "TestUser"
        message.author.name = "testuser"
        message.content = "Test message content"
        message.created_at = MagicMock()
        message.created_at.strftime = MagicMock(return_value="2026-01-28 12:00:00 UTC")
        return message


if __name__ == "__main__":
    # Run unit tests if called with --test flag
    import sys
    if "--test" in sys.argv:
        sys.argv.remove("--test")
        unittest.main()
    else:
        asyncio.run(main())
