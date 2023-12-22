import json
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

intents = discord.Intents.default()
intents.typing = True
intents.presences = False
intents.members = True

# Initialize the bot with intents
bot = commands.Bot(command_prefix='!', intents=intents)

# Load the teams from the JSON file
with open('Teams.json', 'r') as teams_file:
    teams_data = json.load(teams_file)

# Create a dictionary to map team IDs to team names
teams = {int(team_id): team_name for team_id, team_name in teams_data.items()}

# Initialize the list of available teams
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
    pass

# Command to set the registration channel
@bot.command()
@commands.has_permissions(administrator=True)
async def setregistrationchannel(ctx, channel: discord.TextChannel):
    # Store the channel ID in a JSON file or a database
    registration_channel_id = channel.id
    with open('registration_channel.json', 'w') as reg_file:
        json.dump({"channel_id": registration_channel_id}, reg_file)
    await ctx.send(f"Registration messages will now be sent to {channel.mention}")

# Slash command to register guesses
@bot.tree.command(name="register", description="Register your guesses")
async def register(interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_id in user_guesses:
        await interaction.response.send_message("You have already registered your guesses.")
        return

    # Create a temporary list to store available teams for this interaction
    temp_available_teams = available_teams.copy()

    # Create a list to store user's selections
    selected_teams = []

    # Iterate until the user has made 16 selections or no teams are left
    for i in range(1, 17):
        if not temp_available_teams:
            await interaction.followup.send("No teams left to choose from.")
            break

        # Create select menu options
        options = [
            discord.SelectOption(label=team, value=team) for team in temp_available_teams
        ]

        # Create a select menu
        select_menu = discord.ui.Select(placeholder=f"Select the {i} team", options=options, custom_id=f"team_selection_{i}")

        # Define the callback for the select menu
        async def select_callback(inter: discord.Interaction):
            selected_team = inter.data['values'][0]
            selected_teams.append(selected_team)
            temp_available_teams.remove(selected_team)
            await inter.response.defer()

        select_menu.callback = select_callback

        # Send the select menu
        view = discord.ui.View()
        view.add_item(select_menu)
        await interaction.followup.send("Available teams:", view=view, ephemeral=True)

        # Wait for user interaction with the select menu
        await bot.wait_for('interaction', check=lambda i: i.data.get('custom_id') == f"team_selection_{i}")

    user_guesses[user_id] = selected_teams

    # Save user submissions to the JSON file
    with open(submits_file, 'w') as submits:
        json.dump(user_guesses, submits)

    # Retrieve the registration channel ID from JSON
    with open('registration_channel.json', 'r') as reg_file:
        data = json.load(reg_file)
        registration_channel_id = data.get("channel_id")

    # Send the registration message to the designated channel
    registration_channel = bot.get_channel(registration_channel_id)
    if registration_channel:
        registration_message = f"{interaction.user.mention} has registered their guess:\n"
        for i, team in enumerate(selected_teams, start=1):
            registration_message += f"{i}. {team}\n"
        await registration_channel.send(registration_message)
    else:
        await interaction.followup.send("Registration channel not set. Please use !setregistrationchannel to configure it.")

# Hybrid command to display user's guesses
@bot.hybrid_command(name="myguesses")
async def myguesses(ctx):
    user_id = ctx.author.id
    if user_id in user_guesses:
        guesses = user_guesses[user_id]
        formatted_guesses = [f"{i+1}. {teams[team_id]}" for i, team_id in enumerate(guesses)]
        await ctx.send(f"{ctx.author.name}'s guesses:\n{', '.join(formatted_guesses)}")
    else:
        await ctx.send("You haven't registered your guesses yet.")

token = os.environ.get("bot-token")

# Run the bot
bot.run(token)
