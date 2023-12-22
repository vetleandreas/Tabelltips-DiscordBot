import json
import discord
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_components import create_select, create_select_option
from discord_slash.model import SlashMessage
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


intents = discord.Intents.default()
intents.typing = True
intents.presences = False
intents.members = True  # You might need this for member-related events

# Initialize the bot with intents
bot = commands.Bot(command_prefix='!', intents=intents)
slash = SlashCommand(bot, sync_commands=True)

# Load the teams from the JSON file
with open('Teams.json', 'r') as teams_file:
    teams_data = json.load(teams_file)

# Create a dictionary to map team IDs to team names
teams = {int(team_id): team_name for team_id, team_name in teams_data.items()}
available_teams = list(teams.values())

# Define a data structure to store user guesses
user_guesses = {}

# Define a JSON file to store user submissions
submits_file = 'submits.json'

# Load user submissions from the JSON file, if it exists
try:
    with open(submits_file, 'r') as submits:
        user_guesses = json.load(submits)
except FileNotFoundError:
    pass  # If the file doesn't exist yet, user_guesses will remain an empty dictionary

# Initialize the bot
bot = commands.Bot(command_prefix='!', intents=intents)


# Initialize the list of available teams
available_teams = list(teams.values())

# ... (other code)

@bot.command()
@commands.has_permissions(administrator=True)  # Add appropriate permission check
async def setregistrationchannel(ctx, channel: discord.TextChannel):
    # Store the channel ID in a JSON file or a database
    registration_channel_id = channel.id
    with open('registration_channel.json', 'w') as reg_file:
        json.dump({"channel_id": registration_channel_id}, reg_file)
    await ctx.send(f"Registration messages will now be sent to {channel.mention}")


@slash.slash(name="register", description="Register your guesses")
async def register(ctx: SlashContext):
    user_id = ctx.author.id
    if user_id in user_guesses:
        await ctx.send("You have already registered your guesses.")
        return

    # Create a list to store user's selections
    selected_teams = []

    # Iterate until the user has made 16 selections or no teams are left
    for i in range(1, 17):
        if not available_teams:
            await ctx.send("No teams left to choose from.")
            break

        # Create select menu options
        options = [
            create_select_option(team, value=team)
            for team in available_teams
        ]
        select = create_select(
            options, placeholder=f"Select the {i} team", custom_id=f"team_selection_{i}"
        )

        # Send the select menu
        await ctx.send(content="Available teams:", components=[select])

        # Wait for user interaction
        interaction = await bot.wait_for(
            "slash_component", check=lambda i: i.custom_id.startswith(f"team_selection_{i}")
        )

        # Get the selected team and add it to the list
        selected_team = interaction.component[0].value
        selected_teams.append(selected_team)
        available_teams.remove(selected_team)

    user_guesses[user_id] = selected_teams

    # Save user submissions to the JSON file (with team IDs/positions)
    with open(submits_file, 'w') as submits:
        json.dump(user_guesses, submits)

 # Retrieve the registration channel ID from JSON
    with open('registration_channel.json', 'r') as reg_file:
        data = json.load(reg_file)
        registration_channel_id = data.get("channel_id")

    # Send the registration message to the designated channel
    registration_channel = bot.get_channel(registration_channel_id)
    if registration_channel:
        registration_message = f"{ctx.author.mention} has registered their guess:\n"
        for i, team in enumerate(selected_teams, start=1):
            registration_message += f"{i}. {team}\n"
        await registration_channel.send(registration_message)
    else:
        await ctx.send("Registration channel not set. Please use !setregistrationchannel to configure it.")


# Bot command to display user's guesses
@bot.command()
async def myguesses(ctx):
    user_id = ctx.author.id
    if user_id in user_guesses:
        guesses = user_guesses[user_id]
        formatted_guesses = [f"{i+1}. Team {team}" for i, team in enumerate(guesses)]
        await ctx.send(f"{ctx.author.name} has guessed the following:\n{', '.join(formatted_guesses)}")
    else:
        await ctx.send("You haven't registered your guesses yet.")


token = os.environ.get("bot-token")

# Run the bot
bot.run(token)

