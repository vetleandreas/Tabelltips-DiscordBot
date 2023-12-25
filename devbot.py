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
        await channel.send("Kamikazetiden er kommet!")


@tree.command(name="devsettkamikazekanal", description="Setter kanalen Kamikazetips kommer i.", guild=discord.Object(int(guildid)))
@commands.has_permissions(administrator=True)
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
    
@tree.command(name="devtest", description="A simple test command", guild=discord.Object(int(guildid)))
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("Jeg er kamikazetipseren, på vei i lufta til en polkagris nær deg.")

@tree.command(name="devkamikazetips", description="Registrer ditt kamikazetips", guild=discord.Object(int(guildid)))
async def kamikazetips(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id in user_guesses:
        await interaction.response.send_message("Du har allerede registrert ditt kamikazetips.")
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
        json.dump(user_guesses, submits)

    # Retrieve the registration channel ID for the current guild from JSON
    guild_id = interaction.guild_id
    registration_channel_id = None
    try:
        with open('registration_channel.json', 'r') as reg_file:
            registration_channels = json.load(reg_file)
            registration_channel_id = registration_channels.get(str(guild_id))
        print(registration_channel_id)
    except (FileNotFoundError, json.JSONDecodeError):
        pass  # Handle error or file not found

    user_id_str = int(interaction.user.id)
    print(user_id_str)
    print(user_guesses)
    print(f"Checking if user {user_id_str} is in user_guesses...")
    if user_id_str in user_guesses:
        print("User is in user_guesses, preparing registration message...")
     
        registration_message = f"{interaction.user.mention} har registrert sitt kamikazetips:\n"
        for i, team_name in enumerate(user_guesses[user_id], start=1):
            registration_message += f"{i}. {team_name}\n"  # team_name is already the name, not an ID

    
        # Send the registration message to the designated channel
        if registration_channel_id:
            registration_channel = bot.get_channel(registration_channel_id)
            if registration_channel:
                await registration_channel.send(registration_message)
            else:
                await interaction.followup.send("Kan ikke finne registreringskanalen. Vennligst sett den opp på nytt.")
        else:
            await interaction.followup.send("Registreringskanalen er ikke satt. Vennligst bruk settkamikazekanal for å konfigurere den.")
    else:
        print(f"{user_id_str} is not in {user_guesses}, sending no registration message...")
        await interaction.followup.send("Du har ikke registrert noen kamikazetips enda.")

@tree.command(name="devtipsetmitt", description="Se kamikazetipset ditt", guild=discord.Object(int(guildid)))
async def tipsetmitt(interaction: discord.Interaction):
    user_id = str(interaction.user.id)  # Ensure user_id is a string
    if user_id in user_guesses:
        team_names = user_guesses[user_id]
        formatted_guesses = [f"{i+1}. {team_name}" for i, team_name in enumerate(team_names)]
        await interaction.response.send_message(f"{interaction.user.mention}'s kamikazetips:\n{', '.join(formatted_guesses)}")
    else:
        await interaction.response.send_message("Du har ikke kamikazet inn noe tips enda.")

@tree.command(name='devglobalsync', description='Owner only')
@commands.has_permissions(administrator=True)  # Restrict this command to administrators
async def globalsync(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        synced_commands = await tree.sync()
        await interaction.followup.send(f"Synced {len(synced_commands)} commands globally.")
    except Exception as e:
        await interaction.followup.send(f"An error occurred while syncing globally: {e}")
    
 
@tree.command(name = "devlocalsync", description = "Synkroniser commands lokalt i serveren", guild=discord.Object(int(guildid)))
@commands.has_permissions(administrator=True)  # Restrict this command to administrators
async def localsync(interaction: discord.Interaction):
    guild_id = int(guildid)
    await interaction.response.defer()

    try:
        synced_commands = await tree.sync(guild=discord.Object(id=guild_id))
        await interaction.followup.send(f"Synced {len(synced_commands)} commands to the current server.")
    except Exception as e:
        await interaction.followup.send(f"An error occurred while syncing to the server: {e}")

token = os.environ.get("bot-token")

# Run the bot
bot.run(token)