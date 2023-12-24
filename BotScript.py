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
    await tree.sync(guild=discord.Object(id=int(guildid)))
    channel = bot.get_channel(int(channelid))
    if channel:
        await channel.send("Kamikazetiden er kommet!")
        
@tree.command(name="settkamikazekanal", description="Setter kanalen Kamikazetips kommer i.", guild=discord.Object(int(guildid)))
@commands.has_permissions(administrator=True)
async def setregistrationchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    registration_channel_id = channel.id
    with open('registration_channel.json', 'w') as reg_file:
        json.dump({"channel_id": registration_channel_id}, reg_file)

    await interaction.response.send_message(f"Registreringer vil nå bli sendt til {channel.mention}")

    
@tree.command(name="test", description="A simple test command", guild=discord.Object(int(guildid)))
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("Jeg er kamikazetipseren, på vei i lufta til en polkagris nær deg.")

@tree.command(name="kamikazetips", description="Registrer ditt kamikazetips", guild=discord.Object(int(guildid)))
async def kamikazetips(interaction: discord.Interaction):
    global user_guesses  # Ensure user_guesses is accessible

    user_id = str(interaction.user.id)  # Convert user ID to string for consistency
    if user_id in user_guesses:
        await interaction.response.send_message("Du har allerede registrert ditt kamikazetips.")
        return
    else:
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

        select_message = await interaction.followup.send(f"Velg lag for {i}. plass:", view=view, ephemeral=True)

        def check(m):
            return (m.user.id == user_id and 
                    m.message.id == select_message.id and 
                    m.data.get('custom_id') == f"team_selection_{i}")

        try:
            new_interaction = await bot.wait_for('interaction', check=check, timeout=120.0)
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

@tree.command(name="tipsetmitt", description="Se kamikazetipset ditt", guild=discord.Object(int(guildid)))
async def tipsetmitt(interaction: discord.Interaction):
    user_id = str(interaction.user.id)  # Ensure user_id is a string
    if user_id in user_guesses:
        team_ids = user_guesses[user_id]
        formatted_guesses = [f"{i+1}. {teams.get(team_id, 'Unknown Team')}" for i, team_id in enumerate(team_ids)]
        await interaction.response.send_message(f"{interaction.user.name}'s guesses:\n{', '.join(formatted_guesses)}")
    else:
        await interaction.response.send_message("Du har ikke kamikazet inn noe tips enda.")

        
@tree.command(name='globalsync', description='Owner only')
@commands.has_permissions(administrator=True)  # Restrict this command to administrators
async def globalsync(interaction: discord.Interaction):
    await bot.tree.sync()
    print('Command tree synced.')
        
@tree.command(name='localglobalsync', description='Owner only')
@commands.has_permissions(administrator=True)  # Restrict this command to administrators
async def localglobalsync(interaction: discord.Interaction):
    await bot.tree.sync()
    print('Command tree synced.')    
    
@tree.command(name="localsync", description="Synkroniser commands lokalt i serveren", guild=discord.Object(int(guildid)))
@commands.has_permissions(administrator=True)
async def synccmd(interaction: discord.Interaction):
    guild_id = int(guildid)
    await interaction.response.defer()

    try:
        synced_commands = await tree.sync(guild=discord.Object(id=guild_id))
        await interaction.followup.send(f"Synced {len(synced_commands)} commands to the current server.")
    except Exception as e:
        await interaction.followup.send(f"An error occurred while syncing: {e}")



#@tree.command(name = "localsync", description = "local synkronisering", guild=discord.Object(int(guildid))) #Add the guild ids in which the slash command will appear. If it should be in all, remove the argument, but note that it will take some time (up to an hour) to register the command if it's for all guilds.
#@commands.has_permissions(administrator=True)  # Restrict this command to administrators
#async def localsync(ctx: commands.Context):         
  #  await tree.sync(guild=discord.Object(id=int(guildid)))
 #   await ctx.send("Localsync done")
#    print("Commands local synced")
    
token = os.environ.get("bot-token")

# Run the bot
bot.run(token)
