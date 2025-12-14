import discord
from discord import app_commands
from discord.app_commands import checks
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import calendar
import asyncio  # Import asyncio for sleep

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
    try:
        synced_commands = await tree.sync()
        print(f"Synced {len(synced_commands)} commands globally.")
    except Exception as e:
        print(f"An error occurred while syncing globally: {e}")
    print(f"Bot connected as {bot.user}")


@tree.command(name="åretsmemes", description="Årlig meme leaderboard")
@checks.has_permissions(administrator=True)  # Built-in check for admin permissions
async def kekw_leaderboard(interaction: discord.Interaction):
    """Generate a leaderboard for the top messages with :VKek: reactions in the last month in a specific channel."""
    await interaction.response.defer()  # Acknowledge the interaction early

    # Define the specific channel ID
    channel_id = 1157043422436266075  # Replace with your channel ID
    channel = bot.get_channel(channel_id)

    if channel is None:
        await interaction.followup.send(f"Could not find the specified channel (ID: {channel_id}).")
        return

    # Define the time range (year 2024)
    start_of_year = datetime(2024, 1, 1)
    start_of_next_year = datetime(2025, 1, 1)

    leaderboard = []
    target_emoji = discord.PartialEmoji(name="VKek", id=1086686017555271721)  # Custom emoji name and ID

    # Scan through messages in the specified time range
    async for message in channel.history(after=start_of_year, before=start_of_next_year, limit=None):
        await asyncio.sleep(0.1)  # Add a small delay to prevent rate limiting
        if message.reactions:
            for reaction in message.reactions:
                if reaction.emoji == target_emoji:
                    leaderboard.append((message, reaction.count))

    # Sort by reaction count (descending) and limit to top 10
    leaderboard = sorted(leaderboard, key=lambda x: x[1], reverse=True)[:10]

    # Generate the response
    if not leaderboard:
        await interaction.followup.send("No :VKek: reactions were found in the specified time range.")
        return

    response = "**Fugtige Memes Leaderboard**\n"
    for i, (message, count) in enumerate(leaderboard, start=1):
        message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
        response += f"{i}. plass: {message_link} - {count} :VKek: fra <@{message.author.id}>\n"

    await interaction.followup.send(response)


@tree.command(name="månedensmemes", description="Generate a leaderboard of messages with :VKek: reactions in a specific channel")
@commands.has_permissions(administrator=True)
@app_commands.describe(
    month="Month number (1-12), defaults to current month",
    year="Year number, defaults to current year"
)
async def månedensmemes(interaction: discord.Interaction, month: int = None, year: int = None):
    await interaction.response.defer()  # Acknowledge early to prevent timeout

    # Default to current month/year if not provided
    now = datetime.utcnow()
    if month is None:
        month = now.month
    if year is None:
        year = now.year

    # Calculate start and end of the selected month
    try:
        start_of_month = datetime(year, month, 1)
        # Find the number of days in the month
        days_in_month = calendar.monthrange(year, month)[1]
        start_of_next_month = start_of_month + timedelta(days=days_in_month)
    except ValueError:
        await interaction.followup.send(f"Invalid month/year combination: {month}/{year}")
        return

    channel_id = 1157043422436266075
    channel = bot.get_channel(channel_id)

    if channel is None:
        await interaction.followup.send(f"Could not find the specified channel (ID: {channel_id}).")
        return

    leaderboard = []
    target_emoji = discord.PartialEmoji(name="VKek", id=1086686017555271721)

    async for message in channel.history(after=start_of_month, before=start_of_next_month, limit=1000):
        for reaction in message.reactions:
            if reaction.emoji == target_emoji:
                leaderboard.append((message, reaction.count))

    leaderboard = sorted(leaderboard, key=lambda x: x[1], reverse=True)[:10]

    if not leaderboard:
        await interaction.followup.send(f"No :VKek: reactions were found for {month:02d}/{year}.")
        return

    response = f"**Fugtige Memes Leaderboard for {month:02d}/{year}**\n"
    for i, (message, count) in enumerate(leaderboard, start=1):
        message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
        response += f"{i}. plass: {message_link} - {count} :VKek: fra <@{message.author.id}> \n"

    await interaction.followup.send(response)


@tree.command(
    name="quarter_top_reactions",
    description="Find the top messages by total reactions in a given quarter"
)
@commands.has_permissions(administrator=True)
@app_commands.describe(
    channel="The channel to search",
    year="Year number (e.g. 2024), defaults to current year",
    quarter="Quarter number (1-4), defaults to current quarter"
)
async def quarter_top_reactions(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    year: int = None,
    quarter: int = None
):
    await interaction.response.defer()

    # Default to current year/quarter if not given
    now = datetime.utcnow()
    if year is None:
        year = now.year
    if quarter is None:
        quarter = (now.month - 1) // 3 + 1

    # Validate quarter
    if quarter not in (1, 2, 3, 4):
        await interaction.followup.send("Quarter must be 1, 2, 3, or 4.")
        return

    # Calculate start and end of quarter
    start_month = (quarter - 1) * 3 + 1
    start_of_quarter = datetime(year, start_month, 1)
    end_month = start_month + 2
    days_in_end_month = calendar.monthrange(year, end_month)[1]
    end_of_quarter = datetime(year, end_month, days_in_end_month, 23, 59, 59)

    leaderboard = []

    # Pull messages in that time range
    async for message in channel.history(after=start_of_quarter, before=end_of_quarter, limit=None):
        total_reactions = sum(reaction.count for reaction in message.reactions)
        if total_reactions > 0:
            leaderboard.append((message, total_reactions))

    # Sort and get top 20
    leaderboard = sorted(leaderboard, key=lambda x: x[1], reverse=True)[:10]

    if not leaderboard:
        await interaction.followup.send(f"No reactions were found in {year} Q{quarter}.")
        return

    # Build leaderboard message
    response = f"**Topp 20 mld i {year} Q{quarter}**\n"
    for i, (message, count) in enumerate(leaderboard, start=1):
        message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
        response += f"{i}. {message_link} - {count} emojis (av <@{message.author.id}>)\n"

    await interaction.followup.send(response)


@tree.command(name='globalsync', description='Global sync meme kun for bot-eier.')
@checks.has_permissions(administrator=True)  # Built-in check for admin permissions
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