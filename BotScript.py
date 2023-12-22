import json
import discord
from discord.ext import commands
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


# Load the teams from the JSON file
with open('Teams.json', 'r') as teams_file:
    teams_data = json.load(teams_file)

# Create a dictionary to map team IDs to team names
teams = {int(team_id): team_name for team_id, team_name in teams_data.items()}

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

# Bot command to register guesses
@bot.command()
async def register(ctx):
    user_id = ctx.author.id
    if user_id in user_guesses:
        await ctx.send("You have already registered your guesses.")
        return

    await ctx.send("Please select teams in order from 1st to 16th place:")
    selected_teams = []

    for i in range(1, 17):
        await ctx.send(f"Select the {i} team:")
        try:
            response = await bot.wait_for('message', check=lambda m: m.author == ctx.author, timeout=60)
            team_id = int(response.content)
            if team_id < 1 or team_id > 4:
                await ctx.send("Invalid team ID. Please select a valid team ID (1-16).")
                return
            selected_teams.append(teams[team_id])
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond. Registration canceled.")
            return

    user_guesses[user_id] = selected_teams

    # Save user submissions to the JSON file
    with open(submits_file, 'w') as submits:
        json.dump(user_guesses, submits)

    await ctx.send(f"Registered your guesses: {', '.join(selected_teams)}")

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

