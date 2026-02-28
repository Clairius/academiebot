import discord
from discord.ext import commands
import json
import os
import asyncio
import time
from datetime import datetime

# =========================
# CONFIG
# =========================

TOKEN = os.getenv("TOKEN")
FICHIER = "fiches.json"

COOLDOWN_DURATION = 3 * 60 * 60  # 3 heures
cooldowns = {}

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# SYSTEME JSON
# =========================

def charger_fiches():
    if not os.path.exists(FICHIER):
        return {}

    try:
        with open(FICHIER, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("⚠ JSON corrompu.")
        return {}

def sauvegarder_fiches(data):
    with open(FICHIER, "w") as f:
        json.dump(data, f, indent=4)

# =========================
# READY
# =========================

@bot.event
async def on_ready():
    print(f"Bot connecté en tant que {bot.user}")

# =========================
# FICHES JOUEURS
# =========================

@bot.command()
@commands.has_role("Staff")
async def majfiche(ctx, member: discord.Member, champ: str, *, valeur: str):

    fiches = charger_fiches()
    champs_valides = ["rang", "objectif", "poste", "points_forts", "points_faibles"]

    if str(member.id) not in fiches:
        await ctx.send("❌ Ce joueur n'a pas de fiche.")
        return

    if champ not in champs_valides:
        await ctx.send("❌ Champ invalide.")
        return

    fiches[str(member.id)][champ] = valeur
    fiches[str(member.id)]["maj"] = f"MAJ par {ctx.author.name} le {datetime.now().strftime('%d/%m/%Y %H:%M')}"

    sauvegarder_fiches(fiches)
    await ctx.send("✅ Fiche mise à jour.")

@bot.command()
async def voirfiche(ctx, member: discord.Member):

    fiches = charger_fiches()

    if str(member.id) not in fiches:
        await ctx.send("❌ Ce joueur n'a pas de fiche.")
        return

    if "Staff" not in [r.name for r in ctx.author.roles] and ctx.author != member:
        await ctx.send("❌ Accès refusé.")
        return

    data = fiches[str(member.id)]

    embed = discord.Embed(
        title=f"📊 Fiche - {member.name}",
        color=discord.Color.gold()
    )

    embed.add_field(name="👨‍🏫 Prof", value=data.get("prof", "Non défini"), inline=False)
    embed.add_field(name="🏅 Rang", value=data.get("rang", "Non défini"), inline=False)
    embed.add_field(name="🎯 Objectif", value=data.get("objectif", "Non défini"), inline=False)
    embed.add_field(name="🧭 Poste", value=data.get("poste", "Non défini"), inline=False)
    embed.add_field(name="💪 Points forts", value=data.get("points_forts", "Non défini"), inline=False)
    embed.add_field(name="⚠ Points faibles", value=data.get("points_faibles", "Non défini"), inline=False)
    embed.set_footer(text=data.get("maj", ""))

    await ctx.send(embed=embed)

# =========================
# PANEL FICHES EQUIPES
# =========================

class TeamSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Equipe 1", emoji="🛡"),
            discord.SelectOption(label="Equipe 2", emoji="⚔"),
            discord.SelectOption(label="Equipe 3", emoji="🏆")
        ]
        super().__init__(
            placeholder="Choisis une équipe...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        fiches = charger_fiches()

        if "equipes" not in fiches:
            await interaction.response.send_message("❌ Aucune équipe configurée.", ephemeral=True)
            return

        equipe_key = self.values[0].lower().replace(" ", "")

        if equipe_key not in fiches["equipes"]:
            await interaction.response.send_message("❌ Équipe introuvable.", ephemeral=True)
            return

        data = fiches["equipes"][equipe_key]

        joueurs_list = "\n".join(
            [f"{i+1}. {j}" for i, j in enumerate(data.get("joueurs", []))]
        ) or "Non défini"

        embed = discord.Embed(
            title=f"🏆 {data.get('nom', 'Equipe')}",
            color=discord.Color.blue()
        )

        embed.add_field(name="📅 Date de création", value=data.get("date_creation", "Non défini"), inline=False)
        embed.add_field(name="🎯 Objectif", value=data.get("objectif", "Non défini"), inline=False)
        embed.add_field(name="👨‍🏫 Coach", value=data.get("coach", "Non défini"), inline=False)
        embed.add_field(name="📋 Manager", value=data.get("manager", "Non défini"), inline=False)
        embed.add_field(name="👥 Joueurs", value=joueurs_list, inline=False)
        embed.add_field(name="ℹ Information sur l'équipe", value=data.get("info", "Non défini"), inline=False)
        embed.set_footer(text=data.get("maj", ""))

        await interaction.response.send_message(embed=embed)

class TeamView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TeamSelect())

@bot.command()
async def teampanel(ctx):

    fiches = charger_fiches()

    if "equipes" not in fiches:
        fiches["equipes"] = {
            "equipe1": {"nom":"Equipe 1","date_creation":"","objectif":"","coach":"","manager":"","joueurs":["","","","",""],"info":"","maj":""},
            "equipe2": {"nom":"Equipe 2","date_creation":"","objectif":"","coach":"","manager":"","joueurs":["","","","",""],"info":"","maj":""},
            "equipe3": {"nom":"Equipe 3","date_creation":"","objectif":"","coach":"","manager":"","joueurs":["","","","",""],"info":"","maj":""}
        }
        sauvegarder_fiches(fiches)

    embed = discord.Embed(
        title="🏆 Fiches des Équipes",
        description="Sélectionne une équipe pour voir sa fiche.",
        color=discord.Color.blue()
    )

    await ctx.send(embed=embed, view=TeamView())

# =========================
# TICKET SYSTEM
# =========================

class CloseTicketView(discord.ui.View):
    @discord.ui.button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.red)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

class ValidateInscriptionView(discord.ui.View):
    def __init__(self, member):
        super().__init__(timeout=None)
        self.member = member

    @discord.ui.button(label="📊 Accepter l'inscription", style=discord.ButtonStyle.green)
    async def validate(self, interaction: discord.Interaction, button: discord.ui.Button):

        if "Staff" not in [r.name for r in interaction.user.roles]:
            await interaction.response.send_message("❌ Réservé au Staff.", ephemeral=True)
            return

        fiches = charger_fiches()

        if str(self.member.id) not in fiches:
            fiches[str(self.member.id)] = {
                "prof": interaction.user.name,
                "rang": "",
                "objectif": "",
                "poste": "",
                "points_forts": "",
                "points_faibles": "",
                "maj": f"Validé par {interaction.user.name} le {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            }
            sauvegarder_fiches(fiches)

        try:
            await self.member.send("🎉 Ton inscription a été ACCEPTÉE !")
        except:
            pass

        await interaction.response.send_message(f"✅ Inscription acceptée pour {self.member.mention}")

        await interaction.channel.send("🔒 Fermeture du ticket dans 3 secondes...")
        await asyncio.sleep(3)
        await interaction.channel.delete()

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Demande Staff", emoji="👨‍🏫"),
            discord.SelectOption(label="Inscription Académique", emoji="📊")
        ]
        super().__init__(placeholder="Choisis le type de ticket...",
                         min_values=1,
                         max_values=1,
                         options=options)

    async def callback(self, interaction: discord.Interaction):

        guild = interaction.guild
        member = interaction.user
        staff_role = discord.utils.get(guild.roles, name="Staff")

        now = time.time()

        if member.id in cooldowns:
            remaining = cooldowns[member.id] - now
            if remaining > 0:
                hours = int(remaining // 3600)
                minutes = int((remaining % 3600) // 60)
                await interaction.response.send_message(
                    f"⏳ Tu dois attendre {hours}h {minutes}min avant une nouvelle inscription.",
                    ephemeral=True
                )
                return

        existing_channel = discord.utils.get(
            guild.text_channels,
            name=f"ticket-{member.id}"
        )

        if existing_channel:
            await interaction.response.send_message(
                "❌ Tu as déjà un ticket ouvert.",
                ephemeral=True
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True),
            staff_role: discord.PermissionOverwrite(view_channel=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        category = discord.utils.get(guild.categories, name="🎟 Tickets")
        if category is None:
            category = await guild.create_category("🎟 Tickets")

        channel = await guild.create_text_channel(
            f"ticket-{member.id}",
            category=category,
            overwrites=overwrites
        )

        if self.values[0] == "Inscription Académique":
            cooldowns[member.id] = now + COOLDOWN_DURATION

        if self.values[0] == "Demande Staff":
            await channel.send(
                f"👨‍🏫 Demande Staff\n\n{member.mention}, quelle est ta demande ?",
                view=CloseTicketView()
            )
        else:
            await channel.send(
                f"📊 Inscription Académique\n\n"
                f"• Rang actuel ?\n"
                f"• Poste principal ?\n"
                f"• Objectif ?\n"
                f"• Games/semaine ?",
                view=ValidateInscriptionView(member)
            )

        await interaction.response.send_message("✅ Ticket créé !", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

@bot.command()
async def ticketpanel(ctx):
    embed = discord.Embed(
        title="🎟 Support Académique",
        description="Merci de sélectionner le type de demande.",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed, view=TicketView())

# =========================
# LANCEMENT
# =========================

bot.run(TOKEN)