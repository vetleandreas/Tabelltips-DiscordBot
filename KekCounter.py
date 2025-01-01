import json
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables from .env file
load_dotenv()

intents = discord.Intents.all()
bot = discord.Client(command_prefix='!', intents=intents)
bot1 = commands.Bot(command_prefix='!', intents=intents)
tree = app_commands.CommandTree(bot)

adminid = os.environ.get("admin-id")

# Sync commands for the bot
@bot.event
async def on_ready():
    await bot.tree.sync()  # Sync the application commands
    print(f"Bot connected as {bot.user}")

@bot.tree.command(name="Månedensmemes", description="Generate a leaderboard of messages with :kekw: reactions in a specific channel")
async def kekw_leaderboard(interaction: discord.Interaction, channel_id: int):
    """Generate a leaderboard for the top messages with :kekw: reactions in the last month in a specific channel."""
    # Channel object
    channel = bot.get_channel(channel_id)
    if channel is None:
        await interaction.response.send_message(f"Could not find a channel with ID {channel_id}.")
        return

    # Define the time range (last month)
    now = datetime.utcnow()
    start_of_month = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
    end_of_last_month = start_of_month + timedelta(days=31) - timedelta(days=now.day)

    leaderboard = []
    target_emoji = discord.PartialEmoji(name="kekw")  # Custom emoji name

    # Scan through messages in the specified time range
    async for message in channel.history(after=start_of_month, before=end_of_last_month, limit=None):
        if message.reactions:
            for reaction in message.reactions:
                if reaction.emoji == target_emoji:
                    leaderboard.append((message, reaction.count))

    # Sort by reaction count (descending) and limit to top 10
    leaderboard = sorted(leaderboard, key=lambda x: x[1], reverse=True)[:10]

    # Generate the response
    if not leaderboard:
        await interaction.response.send_message("No :kekw: reactions were found in the specified time range.")
        return

    response = "**:kekw: Leaderboard for last month:**\n"
    for i, (message, count) in enumerate(leaderboard, start=1):
        message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
        response += f"{i}. [Message Link]({message_link}) av <@{message.author.id}> med {count} :kekw:\n"

    await interaction.response.send_message(response)

@tree.command(name='globalsync', description='Global sync meme kun for bot-eier.')
async def globalsync(interaction: discord.Interaction):
    if int(interaction.user.id) != int(adminid):
        await interaction.response.send_message("Du er ikke bot-eier.")
        return

    await interaction.response.defer()
    try:
        synced_commands = await tree.sync()
        await interaction.followup.send(f"Synced {len(synced_commands)} commands globally.")
    except Exception as e:
        await interaction.followup.send(f"An error occurred while syncing globally: {e}")

token = os.environ.get("bot-token")

# Run the bot
bot.run(token)