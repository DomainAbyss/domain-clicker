#!/usr/bin/env python3
"""
GT Auto Ads — Post all 6 ads to Lost Nemo at once.
Run: python gt_ads.py
Token read from same file as other GT scripts.
"""

import asyncio, os, sys

# Get token from file
TOKEN_FILE = os.path.expanduser("~/.hermes/scripts/gt_scraper.py")
with open(TOKEN_FILE) as f:
    for line in f:
        if line.strip().startswith("DISCORD_TOKEN"):
            exec(line.strip())
            break

# Channel IDs (hardcoded from Lost Nemo)
CHANNELS = {
    "grow4good": 967097602153791528,
    "farms": 846678280928624650,
    "farmables": 846678373635457024,
    "crime": 742546954503848006,
    "clash": 762435449909542942,
    "neck": 944660041636659271,
}

ADS = {
    "grow4good": (
        "SELL AT DSJ7\n"
        "-FISHING SUPPLY CRATE 16 <:WL:880251447470596157>\n"
        "-SURGERY SUPPLY CRATE 22 <:WL:880251447470596157>\n"
        "SELL AT DSJ7"
    ),
    "farms": "SELL R VENUS DF 35 DL have 1 DM",
    "farmables": "SELL R VENUS DF 35 DL have 1 DM",
    "crime": (
        "GO DSJ7\n"
        "SELL CRIME WAVE 10 <:WL:880251447470596157>\n"
        "SELL HENCHMAN 4 <:WL:880251447470596157>\n"
        "GO DSJ7"
    ),
    "clash": (
        "in DSJ7\n\n"
        "Magic Magnet : 3 :DL~1:\n"
        "Steampunk wings: 2 :DL~1: 50 :WL~1:\n"
        "Eagle Spirit : 3 :DL~1:\n"
        "Forged Iron Skin: 70 :WL~1:\n\n"
        "In DSJ7"
    ),
    "neck": (
        "In DSJ7\n\n"
        "Serpent Shoulders : 5 :DL~1:\n\n"
        "In DSJ7"
    ),
}

try:
    import discord
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "discord.py-self", "-q"])
    import discord


async def send_all():
    print("=" * 50)
    print("  GT AUTO ADS — 6 channels")
    print("=" * 50)

    for name, ch_id in CHANNELS.items():
        msg = ADS[name]

        class Sender(discord.Client):
            async def on_ready(self2):
                ch = self2.get_channel(ch_id) or await self2.fetch_channel(ch_id)
                await ch.send(msg)
                print(f"  ✅ {name}")
                await self2.close()

        try:
            client = Sender()
            await client.start(DISCORD_TOKEN)
        except Exception as e:
            print(f"  ❌ {name}: {e}")

    print("=" * 50)
    print("  Done!")


if __name__ == "__main__":
    asyncio.run(send_all())
