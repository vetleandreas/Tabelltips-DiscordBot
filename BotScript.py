import json
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

intents = discord.Intents.all()
bot = discord.Client(command_prefix='!', intents=intents)
bot1 = commands.Bot(command_prefix='!', intents=intents)
tree = app_commands.CommandTree(bot)

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

guildid = os.environ.get("guild-id")
channelid = os.environ.get("channel-id")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")
    # Sync commands to a specific guild for testing
    # Replace 'YOUR_GUILD_ID' with your server's ID as an integer
    await tree.sync(guild=discord.Object(id=int(guildid)))
    channel = bot.get_channel(int(channelid))
    if channel:
        await channel.send("Bot online!")

# Command to set the registration channel
@bot1.hybrid_command()
@commands.has_permissions(administrator=True)
async def setregistrationchannel(ctx, channel: discord.TextChannel):
    # Store the channel ID in a JSON file or a database
    registration_channel_id = channel.id
    with open('registration_channel.json', 'w') as reg_file:
        json.dump({"channel_id": registration_channel_id}, reg_file)
    await ctx.send(f"Registration messages will now be sent to {channel.mention}")
    
@tree.command(name="test", description="A simple test command", guild=discord.Object(int(guildid)))
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("Test command works!")

@tree.command(name="kamikazetips", description="Register your guesses", guild=discord.Object(int(guildid)))
async def kamikazetips(interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_id in user_guesses:
        # Send initial response if the user has already registered
        await interaction.response.send_message("You have already registered your guesses.")
        return
    else:
        # Defer the interaction if processing takes time
        await interaction.response.defer()

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
@bot1.hybrid_command(name="myguesses")
async def myguesses(ctx):
    user_id = ctx.author.id
    if user_id in user_guesses:
        guesses = user_guesses[user_id]
        formatted_guesses = [f"{i+1}. {teams[team_id]}" for i, team_id in enumerate(guesses)]
        await ctx.send(f"{ctx.author.name}'s guesses:\n{', '.join(formatted_guesses)}")
    else:
        await ctx.send("You haven't registered your guesses yet.")
        
@bot1.hybrid_command(name='sync', description='Owner only')
async def sync(interaction: discord.Interaction):
    await bot.tree.sync()
    print('Command tree synced.')
        
@tree.command()
@commands.has_permissions(administrator=True)  # Restrict this command to administrators
async def synccmd(ctx):
    guild_id = int(guildid)  # Replace with your guild's ID
    try:
        synced_commands = await bot.tree.sync(guild=discord.Object(id=guild_id))
        await ctx.send(f"Synced {len(synced_commands)} commands to the current server.")
    except Exception as e:
        await ctx.send(f"An error occurred while syncing: {e}")

@bot1.hybrid_command(name = "localsync", description = "My first application Command", guild=discord.Object(int(guildid))) #Add the guild ids in which the slash command will appear. If it should be in all, remove the argument, but note that it will take some time (up to an hour) to register the command if it's for all guilds.
async def localsync(ctx: commands.Context):         
    await tree.sync(guild=discord.Object(id=int(guildid)))
    await ctx.send("Localsync done")
    print("Commands local synced")
    
token = os.environ.get("bot-token")

# Run the bot
bot.run(token)
