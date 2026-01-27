"""
Quick test script to verify Discord connection works.
"""

import asyncio
import os
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

if __name__ == "__main__":
    asyncio.run(main())
