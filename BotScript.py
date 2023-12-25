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

guildid = os.environ.get("guild-id")
channelid = os.environ.get("channel-id")

@bot.event
async def on_ready():
    global user_guesses
    try:
        with open('submits.json', 'r') as submits_file:
            user_guesses = json.load(submits_file)
    except FileNotFoundError:
        user_guesses = {}
    print(f"Logged in as {bot.user}!")
    print("Teams:", teams)
    print("User guesses:", user_guesses)
    # Sync commands to a specific guild for testing
    # Replace 'YOUR_GUILD_ID' with your server's ID as an integer
    await bot.wait_until_ready()
    await tree.sync()  # Syncs commands globally
    print(f"Logged in as {bot.user} and commands synced globally!")

  #For debugging på online/offline tider
    #  channel = bot.get_channel(int(channelid))
   # if channel:
    #    await channel.send("Kamikazetiden er kommet!")
        
@tree.command(name="settkamikazekanal", description="Setter kanalen Kamikazetips kommer i.")
@commands.has_permissions(administrator=True)
async def setregistrationchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    registration_channel_id = channel.id
    with open('registration_channel.json', 'w') as reg_file:
        json.dump({"channel_id": registration_channel_id}, reg_file)

    await interaction.response.send_message(f"Registreringer vil nå bli sendt til {channel.mention}")

    
@tree.command(name="test", description="Test for å se at botten skriver til serveren.")
@commands.has_permissions(administrator=True)
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("Jeg er kamikazetipseren, på vei i lufta til en polkagris nær deg.")
    
@tree.command(name="kamikazetips", description="Registrer ditt kamikazetips")
async def kamikazetips(interaction: discord.Interaction):
    global user_guesses

    user_id = str(interaction.user.id)
    if user_id not in user_guesses:
        user_guesses[user_id] = []

    await interaction.response.defer(ephemeral=True)

    temp_available_teams = available_teams.copy()
    selected_team_ids = []  # Store team IDs

    for i in range(1, 17):
        if not temp_available_teams:
            await interaction.followup.send("Ingen lag igjen å velge mellom.")
            break

        options = [discord.SelectOption(label=team_name, value=str(team_id)) 
                   for team_id, team_name in teams.items() if team_name in temp_available_teams]

        select_menu = discord.ui.Select(placeholder=f"Velg lag for {i}. plass:", options=options, custom_id=f"team_selection_{i}")

        view = discord.ui.View()
        view.add_item(select_menu)

        await interaction.edit_original_response(view=view)

        def check(m):
            return (m.user.id == user_id and 
                    m.data.get('custom_id') == f"team_selection_{i}")

        try:
            new_interaction = await bot.wait_for('interaction', check=check, timeout=15.0)
            await new_interaction.response.defer()
        except asyncio.TimeoutError:
            await interaction.followup.send("Du var superløk og brukte for lang tid. Prøv på nytt og tenk raskere >:(", ephemeral=True)
            return

        selected_team_id = int(new_interaction.data['values'][0])
        selected_team_name = teams[selected_team_id]
        selected_team_ids.append(selected_team_id)
        temp_available_teams.remove(selected_team_name)

    user_guesses[user_id] = selected_team_ids  # Update user_guesses with new registration

    # Save user submissions to the JSON file
    with open(submits_file, 'w') as submits:
        json.dump(user_guesses, submits)
        await interaction.followup.send("Ditt kamikazetips er registrert.", ephemeral=True)

    # Retrieve the registration channel ID from JSON
    with open('registration_channel.json', 'r') as reg_file:
        data = json.load(reg_file)
        registration_channel_id = data.get("channel_id")
    
    # Send the registration message to the designated channel
    registration_channel = bot.get_channel(registration_channel_id)
    if registration_channel:
        registration_message = f"{interaction.user.mention} har registrert sitt kamikazetips:\n"
        for i, team_id in enumerate(selected_team_ids, start=1):
            team_name = teams.get(team_id, "Unknown Team")
            registration_message += f"{i}. {team_name}\n"
        await registration_channel.send(registration_message)
    else:
        await interaction.followup.send("Registreringskanalen er ikke satt. Vennligst bruk !setregistrationchannel for å konfigurere den.")

@tree.command(name="simplekamikaze", description="Select and save one team")
async def simplekamikaze(interaction: discord.Interaction):
    # Load the teams (assuming teams_data is already loaded)
    teams = {int(team_id): team_name for team_id, team_name in teams_data.items()}

    options = [discord.SelectOption(label=team_name, value=str(team_id)) 
               for team_id, team_name in teams.items()]

    select_menu = discord.ui.Select(options=options)

    async def select_callback(interaction: discord.Interaction):
        selected_team_id = int(interaction.data['values'][0])
        selected_team_name = teams[selected_team_id]

        # Save the selection (for simplicity, printing to console here)
        print(f"User {interaction.user} selected team: {selected_team_name}")

        # Respond to the user
        await interaction.response.send_message(f"You selected {selected_team_name}", ephemeral=True)

    select_menu.callback = select_callback

    view = discord.ui.View()
    view.add_item(select_menu)

    await interaction.response.send_message("Select a team:", view=view, ephemeral=True)


@tree.command(name="kamikazetipsnummerto", description="Registrer ditt kamikazetips")
async def kamikazetipsnummerto(interaction: discord.Interaction):
    global user_guesses

    user_id = str(interaction.user.id)
    if user_id not in user_guesses:
        user_guesses[user_id] = []

    await interaction.response.defer(ephemeral=True)

    # Creating a dropdown for each placement
    for i in range(len(user_guesses[user_id]) + 1, 17):
        temp_available_teams = [team for team in available_teams if team not in [teams[tid] for tid in user_guesses[user_id]]]
        options = [discord.SelectOption(label=team, value=str(team_id))
                   for team_id, team in teams.items() if team in temp_available_teams]

        select_menu = discord.ui.Select(options=options, custom_id=f"team_select_{i}")

        async def select_callback(interaction: discord.Interaction, select_menu=select_menu, placement=i):
            selected_team_id = int(select_menu.values[0])
            user_guesses[user_id].append(selected_team_id)

            with open(submits_file, 'w') as submits:
                json.dump(user_guesses, submits)

            if len(user_guesses[user_id]) < 16:
                await interaction.response.send_message(f"Lag {teams[selected_team_id]} valgt for plass {placement}. Velg neste lag.", ephemeral=True)
                await kamikazetips(interaction)
            else:
                await finalize_kamikazetips(interaction)

        select_menu.callback = select_callback

        view = discord.ui.View()
        view.add_item(select_menu)
        await interaction.edit_original_response(content=f"Velg lag for plass {i}:", view=view)
        break

async def finalize_kamikazetips(interaction):
    # Retrieve the registration channel ID from JSON
    with open('registration_channel.json', 'r') as reg_file:
        data = json.load(reg_file)
        registration_channel_id = data.get("channel_id")

    registration_channel = bot.get_channel(registration_channel_id)
    if registration_channel:
        registration_message = f"{interaction.user.mention} har registrert sitt kamikazetips:\n"
        for i, team_id in enumerate(user_guesses[str(interaction.user.id)], start=1):
            team_name = teams.get(team_id, "Unknown Team")
            registration_message += f"{i}. {team_name}\n"
        await registration_channel.send(registration_message)
        await interaction.followup.send("Alle dine kamikazetips er registrert.", ephemeral=True)
    else:
        await interaction.followup.send("Registreringskanalen er ikke satt. Vennligst bruk !setregistrationchannel for å konfigurere den.", ephemeral=True)
          
@tree.command(name="tipsetmitt", description="Se kamikazetipset ditt")
async def tipsetmitt(interaction: discord.Interaction):
    user_id = str(interaction.user.id)  # Ensure user_id is a string
    if user_id in user_guesses:
        team_ids = user_guesses[user_id]
        formatted_guesses = [f"{i+1}. {teams.get(team_id, 'Unknown Team')}" for i, team_id in enumerate(team_ids)]
        await interaction.response.send_message(f"{interaction.user.mention}'s kamikazetips:\n{', '.join(formatted_guesses)}")
    else:
        await interaction.response.send_message("Du har ikke kamikazet inn noe tips enda.")

        
@tree.command(name='globalsync', description='Owner only')
@commands.has_permissions(administrator=True)  # Restrict this command to administrators
async def globalsync(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        synced_commands = await tree.sync()
        await interaction.followup.send(f"Synced {len(synced_commands)} commands globally.")
    except Exception as e:
        await interaction.followup.send(f"An error occurred while syncing globally: {e}")
    
@tree.command(name="localsync", description="Synkroniser commands lokalt i serveren")
@commands.has_permissions(administrator=True)
async def synccmd(interaction: discord.Interaction):
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
