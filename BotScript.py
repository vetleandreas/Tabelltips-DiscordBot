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
adminid = os.environ.get("admin-id")

@bot.event
async def on_ready():
    global user_guesses  # Ensure you are modifying the global variable
    print(f"Logged in as {bot.user}!")

    # Load user guesses from submits.json
    try:
        with open(submits_file, 'r') as submits:
            user_guesses = json.load(submits)
            print("User guesses loaded:", user_guesses)

    except FileNotFoundError:
        print("submits.json not found. Starting with empty user guesses.")
        user_guesses = {}

    # Sync commands to a specific guild for testing
    await tree.sync(guild=discord.Object(id=int(guildid)))

@tree.command(name="settabelltipskanal", description="Setter kanalen Tabelltips kommer i.")
@commands.has_permissions(manage_guild=True)
async def setregistrationchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = interaction.guild_id  # Get the guild ID
    registration_channel_id = channel.id

    # Load existing registration channels
    try:
        with open('registration_channel.json', 'r') as reg_file:
            registration_channels = json.load(reg_file)
    except (FileNotFoundError, json.JSONDecodeError):
        registration_channels = {}

    # Update the registration channel for the current guild
    registration_channels[str(guild_id)] = registration_channel_id

    # Save the updated registration channels
    with open('registration_channel.json', 'w') as reg_file:
        json.dump(registration_channels, reg_file)

    await interaction.response.send_message(f"Registreringer vil nå bli sendt til {channel.mention}")
    
@tree.command(name="test", description="Tester at boten er oppe - returnerer en melding.")
@commands.has_permissions(manage_guild=True)
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("Jeg lagrer tabelltipset ditt i hjernen min, men du må bruke din egen for å komme fram til det rette svaret - så fremt du har en. Tiden vil vise..")

@tree.command(name="tabelltips", description="Registrer ditt tabelltips med denne kommandoen. Klarer du se inn i fremtiden?")
async def tabelltips(interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_id in user_guesses:
        await interaction.response.send_message("Du har allerede registrert ditt tabelltips.")
        return
    else:
        await interaction.response.defer(ephemeral=True)

    temp_available_teams = available_teams.copy()
    selected_teams = []

    for i in range(1, 17):
        if not temp_available_teams:
            await interaction.followup.send("Ingen lag igjen å velge mellom.")
            break

        options = [discord.SelectOption(label=team, value=team) for team in temp_available_teams]

        select_menu = discord.ui.Select(placeholder=f"Velg lag for {i}. plass:", options=options, custom_id=f"team_selection_{i}")

        view = discord.ui.View()
        view.add_item(select_menu)

        select_message = await interaction.followup.send(f"Velg lag for {i}. plass:", view=view, ephemeral=True)

        def check(m):
            return (m.user.id == user_id and 
                    m.message.id == select_message.id and 
                    m.data.get('custom_id') == f"team_selection_{i}")

        try:
            new_interaction = await bot.wait_for('interaction', check=check, timeout=120.0)  # 2 minutes timeout
        except asyncio.TimeoutError:
            await interaction.followup.send("Du var løk og brukte for lang tid. Prøv på nytt og tenk raskere >:( ", ephemeral=True)
            return

        selected_team = new_interaction.data['values'][0]
        selected_teams.append(selected_team)
        temp_available_teams.remove(selected_team)

        # Acknowledge the selection
        await new_interaction.response.send_message(f"Du valgte {selected_team} for {i}.plass.", ephemeral=True)

    user_guesses[user_id] = selected_teams
    # Save user submissions to the JSON file
    with open(submits_file, 'w') as submits:
        json.dump(user_guesses, submits, indent=4)


    # Retrieve the registration channel ID for the current guild from JSON
    guild_id = interaction.guild.id  # Get the current guild ID
    registration_channel_id = None
    with open('registration_channel.json', 'r') as reg_file:
        registration_channels = json.load(reg_file)
        registration_channel_id = registration_channels.get(str(guild_id))  # Fetch the channel ID for this guild
    
    # Send the registration message to the designated channel
    registration_channel = bot.get_channel(registration_channel_id)
    if registration_channel:
        registration_message = f"{interaction.user.mention} har registrert sitt tabelltips:\n"
        for i, team in enumerate(selected_teams, start=1):
            registration_message += f"{i}. {team}\n"
        await registration_channel.send(registration_message)
    else:
        await interaction.followup.send("Registreringen må konfigureres. Administrator må kjøre /settabelltipskanal.")
   
@tree.command(name="tipsetmitt", description="Se tabelltipset ditt")
async def tipsetmitt(interaction: discord.Interaction):
    user_id = interaction.user.id  # Ensure it's a string
    if user_id in user_guesses:
        team_names = user_guesses[user_id]
        formatted_guesses = [f"{i+1}. {team_name}\n" for i, team_name in enumerate(team_names)]
        await interaction.response.send_message(f"{interaction.user.mention}'s tabelltips:\n{''.join(formatted_guesses)}")
    else:
        await interaction.response.send_message("Du har ikke registrert noen tips enda.")

@tree.command(name='globalsync', description='Global sync kun for bot-eier.')
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