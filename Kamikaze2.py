import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
import sqlite3
import json
from dotenv import load_dotenv

# ------------------ LOAD ENVIRONMENT ------------------
load_dotenv()
guildid = int(os.environ.get("guild-id"))
adminid = int(os.environ.get("admin-id"))
token = os.environ.get("bot-token")

# ------------------ BOT SETUP ------------------
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "submits.db")
TEAMS_PATH = os.path.join(BASE_DIR, "Teams.json")
REG_CHANNEL_FILE = os.path.join(BASE_DIR, "registration_channel.json")

# ------------------ LOAD TEAMS ------------------
with open(TEAMS_PATH, "r") as f:
    teams_data = json.load(f)
teams = {int(team_id): team_name for team_id, team_name in teams_data.items()}
available_teams = list(teams.values())

# ------------------ DATABASE FUNCTIONS ------------------
def get_connection():
    return sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)

def init_db():
    with get_connection() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            user_id INTEGER PRIMARY KEY,
            last_submit TIMESTAMP NOT NULL,
            guess TEXT
        )
        """)
        conn.commit()

def get_submission(user_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT guess FROM submissions WHERE user_id = ?", (user_id,)).fetchone()
        return json.loads(row[0]) if row else None

def save_submission(user_id: int, guess_list):
    guess_json = json.dumps(guess_list)
    with get_connection() as conn:
        conn.execute("""
        INSERT INTO submissions (user_id, last_submit, guess)
        VALUES (?, CURRENT_TIMESTAMP, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET
            last_submit = excluded.last_submit,
            guess = excluded.guess
        """, (user_id, guess_json))
        conn.commit()

# ------------------ BOT EVENTS ------------------
@bot.event
async def on_ready():
    init_db()
    print(f"Logged in as {bot.user}!")
    await tree.sync(guild=discord.Object(id=guildid))

# ------------------ COMMANDS ------------------
@tree.command(name="settkamikazekanal", description="Setter kanalen Kamikazetips kommer i.")
@commands.has_permissions(manage_guild=True)
async def setregistrationchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = interaction.guild_id
    try:
        with open(REG_CHANNEL_FILE, 'r') as f:
            registration_channels = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        registration_channels = {}

    registration_channels[str(guild_id)] = channel.id

    with open(REG_CHANNEL_FILE, 'w') as f:
        json.dump(registration_channels, f)

    await interaction.response.send_message(f"Registreringer vil nå bli sendt til {channel.mention}")

@tree.command(name="test", description="Tester at boten er oppe - returnerer en melding.")
@commands.has_permissions(manage_guild=True)
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("Jeg er kamikazetipseren, på vei i lufta til en polkagris nær deg.")

class TeamSelect(discord.ui.Select):
    def __init__(self, user_id):
        options = [discord.SelectOption(label=team, value=team) for team in available_teams]
        super().__init__(placeholder="Velg 16 lag i riktig rekkefølge",
                         options=options,
                         min_values=16,
                         max_values=16,
                         custom_id="team_selection")
        self.user_id = user_id
        self.selected_teams = None

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Dette er ikke din registrering.", ephemeral=True)
            return

        self.selected_teams = self.values[:16]      # make sure only 16

        save_submission(self.user_id, self.selected_teams)
        await interaction.response.send_message("Tipset ditt er registrert ✅", ephemeral=True)

        # registration channel
        try:
            with open(REG_CHANNEL_FILE, 'r') as f:
                registration_channels = json.load(f)
                reg_channel_id = registration_channels.get(str(interaction.guild.id))
        except (FileNotFoundError, json.JSONDecodeError):
            reg_channel_id = None

        reg_channel = bot.get_channel(reg_channel_id) if reg_channel_id else None
        if reg_channel:
            msg = f"{interaction.user.mention} har registrert sitt kamikazetips:\n"
            for i, team in enumerate(self.selected_teams, start=1):
                msg += f"{i}. {team}\n"
            await reg_channel.send(msg)
        else:
            await interaction.followup.send(
                "Registreringen må konfigureres. Administrator må kjøre /settkamikazekanal."
            )


@tree.command(name="kamikazetips", description="Registrer ditt kamikazetips")
async def kamikazetips(interaction: discord.Interaction):
    user_id = interaction.user.id
    if get_submission(user_id):
        await interaction.response.send_message("Du har allerede registrert ditt kamikazetips.")
        return

    await interaction.response.defer(ephemeral=True)

    view = discord.ui.View()
    view.add_item(TeamSelect(user_id))
    await interaction.followup.send(
        "Velg 16 lag i riktig rekkefølge:",
        view=view,
        ephemeral=True
    )


@tree.command(name="tipsetmitt", description="Se kamikazetipset ditt")
async def tipsetmitt(interaction: discord.Interaction):
    user_id = interaction.user.id
    guesses = get_submission(user_id)
    if guesses:
        formatted = "\n".join(f"{i+1}. {team}" for i, team in enumerate(guesses))
        await interaction.response.send_message(f"{interaction.user.mention}'s kamikazetips:\n{formatted}")
    else:
        await interaction.response.send_message("Du har ikke kamikazet inn noe tips enda.")

@tree.command(name='globalsync', description='Global sync kun for bot-eier.')
async def globalsync(interaction: discord.Interaction):
    if interaction.user.id != adminid:
        await interaction.response.send_message("Du er ikke bot-eier.")
        return
    await interaction.response.defer()
    try:
        synced_commands = await tree.sync()
        await interaction.followup.send(f"Synced {len(synced_commands)} commands globally.")
    except Exception as e:
        await interaction.followup.send(f"An error occurred while syncing globally: {e}")

# ------------------ RUN BOT ------------------
bot.run(token)
