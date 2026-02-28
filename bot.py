import discord
from discord.ext import commands
import json
import os
import asyncio
from datetime import datetime

# =========================
# CONFIG
# =========================

TOKEN = os.getenv("TOKEN")
FICHIER = "fiches.json"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# JSON SYSTEM
# =========================

def charger_fiches():
    if not os.path.exists(FICHIER):
        return {}
    try:
        with open(FICHIER, "r") as f:
            return json.load(f)
    except:
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
    champs_valides = [
        "rang", "objectif", "poste",
        "points_forts", "points_faibles"
    ]

    if str(member.id) not in fiches:
        fiches[str(member.id)] = {}

    if champ not in champs_valides:
        await ctx.send("❌ Champ invalide.")
        return

    fiches[str(member.id)][champ] = valeur
    fiches[str(member.id)]["maj"] = datetime.now().strftime("%d/%m/%Y %H:%M")

    sauvegarder_fiches(fiches)
    await ctx.send("✅ Fiche mise à jour.")

@bot.command()
async def voirfiche(ctx, member: discord.Member):

    fiches = charger_fiches()

    if str(member.id) not in fiches:
        await ctx.send("❌ Aucune fiche.")
        return

    data = fiches[str(member.id)]

    embed = discord.Embed(
        title=f"📊 Fiche - {member.name}",
        color=discord.Color.gold()
    )

    embed.add_field(name="Rang", value=data.get("rang", "Non défini"), inline=False)
    embed.add_field(name="Objectif", value=data.get("objectif", "Non défini"), inline=False)
    embed.add_field(name="Poste", value=data.get("poste", "Non défini"), inline=False)
    embed.add_field(name="Points forts", value=data.get("points_forts", "Non défini"), inline=False)
    embed.add_field(name="Points faibles", value=data.get("points_faibles", "Non défini"), inline=False)

    await ctx.send(embed=embed)

# =========================
# RAPPORT EQUIPE
# =========================

@bot.command()
async def rapport(ctx, equipe: discord.Role = None, *, contenu: str = None):

    if equipe is None or contenu is None:
        await ctx.send("❌ Utilisation : !rapport @Equipe contenu")
        return

    if not any(r.name == "Capitaine" for r in ctx.author.roles):
        await ctx.send("❌ Tu dois être Capitaine.")
        return

    if equipe not in ctx.author.roles:
        await ctx.send("❌ Tu n'es pas dans cette équipe.")
        return

    guild = ctx.guild
    direction = discord.utils.get(guild.roles, name="🎯 Direction Esport")
    manager = discord.utils.get(guild.roles, name="📊 Manager")

    channel = discord.utils.get(guild.text_channels, name="rapport")

    if channel is None:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            direction: discord.PermissionOverwrite(view_channel=True),
            manager: discord.PermissionOverwrite(view_channel=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }
        channel = await guild.create_text_channel("rapport", overwrites=overwrites)

    embed = discord.Embed(
        title=f"📋 Rapport - {equipe.name}",
        color=discord.Color.red(),
        timestamp=datetime.now()
    )

    embed.add_field(name="Capitaine", value=ctx.author.mention, inline=False)
    embed.add_field(name="Contenu", value=contenu, inline=False)

    await channel.send(embed=embed)
    await ctx.send("✅ Rapport envoyé.")

# =========================
# BOUTON FERMETURE STAFF
# =========================

class CloseTicketStaffView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fermer", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):

        if "Staff" not in [r.name for r in interaction.user.roles]:
            await interaction.response.send_message("❌ Staff uniquement.", ephemeral=True)
            return

        await interaction.response.send_message("🔒 Fermeture...")
        await asyncio.sleep(2)
        await interaction.channel.delete()

# =========================
# ACTION STAFF
# =========================

class TicketActionView(discord.ui.View):
    def __init__(self, member, ticket_type):
        super().__init__(timeout=None)
        self.member = member
        self.ticket_type = ticket_type

    @discord.ui.button(label="✅ Accepter", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):

        if "Staff" not in [r.name for r in interaction.user.roles]:
            await interaction.response.send_message("❌ Staff uniquement.", ephemeral=True)
            return

        fiches = charger_fiches()
        user_id = str(self.member.id)

        if user_id not in fiches:
            fiches[user_id] = {}

        messages = []
        async for msg in interaction.channel.history(limit=100):
            if msg.author == self.member:
                messages.append(msg.content)

        contenu = "\n".join(messages[::-1])

        if self.ticket_type == "academie":
            fiches[user_id]["candidature_academie"] = contenu
            fiches[user_id]["statut_academie"] = "Accepté"

        if self.ticket_type == "esport":
            fiches[user_id]["candidature_esport"] = contenu
            fiches[user_id]["statut_esport"] = "Accepté"

        sauvegarder_fiches(fiches)

        try:
            await self.member.send("🎉 Ta candidature a été ACCEPTÉE !")
        except:
            pass

        await interaction.response.send_message("✅ Accepté.")
        await asyncio.sleep(3)
        await interaction.channel.delete()

    @discord.ui.button(label="❌ Refuser", style=discord.ButtonStyle.danger)
    async def refuse(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_message(
            "📝 Écris le motif (5 minutes).",
            ephemeral=True
        )

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await bot.wait_for("message", timeout=300.0, check=check)
            motif = msg.content
        except:
            await interaction.followup.send("❌ Temps écoulé.")
            return

        fiches = charger_fiches()
        user_id = str(self.member.id)

        if user_id not in fiches:
            fiches[user_id] = {}

        fiches[user_id][f"motif_{self.ticket_type}"] = motif
        fiches[user_id][f"statut_{self.ticket_type}"] = "Refusé"

        sauvegarder_fiches(fiches)

        try:
            await self.member.send(f"❌ Refusé.\nMotif : {motif}")
        except:
            pass

        await interaction.followup.send("❌ Refus enregistré.")
        await asyncio.sleep(3)
        await interaction.channel.delete()

# =========================
# MENU TICKET
# =========================

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Inscription Académie", emoji="🎓"),
            discord.SelectOption(label="Inscription Team Esport", emoji="🔥"),
            discord.SelectOption(label="Besoin d'aide", emoji="🆘")
        ]
        super().__init__(
            placeholder="Choisis une option",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        guild = interaction.guild
        member = interaction.user

        existing = discord.utils.get(guild.text_channels, name=f"ticket-{member.id}")
        if existing:
            await interaction.response.send_message("❌ Ticket déjà ouvert.", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True),
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

        if self.values[0] == "Inscription Académie":
            await channel.send(
                "🎓 **Candidature Académie – Questions**\n\n"
                "Pseudo :\nÂge :\nRôle :\nRank + Peak :\nOP.GG :\n"
                "Pourquoi nous rejoindre ?\nObjectifs ?\nPrêt à suivre des cours ?",
                view=TicketActionView(member, "academie")
            )

        elif self.values[0] == "Inscription Team Esport":
            await channel.send(
                "🔥 **Candidature Team Esport – Questions**\n\n"
                "Pseudo :\nÂge :\nRôle :\nRank + Peak :\nOP.GG :\n"
                "Disponibilités :\nExpérience :\nTournois :\n"
                "Pourquoi nous ?\nObjectif saison :",
                view=TicketActionView(member, "esport")
            )

        elif self.values[0] == "Besoin d'aide":
            await channel.send(
                f"🆘 {member.mention} en quoi le staff peut t'aider ?",
                view=CloseTicketStaffView()
            )

        await interaction.response.send_message("✅ Ticket créé.", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

@bot.command()
async def ticketpanel(ctx):
    embed = discord.Embed(
        title="🎟 Système de Ticket",
        description="Sélectionne une catégorie.",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed, view=TicketView())

# =========================
# LANCEMENT
# =========================

bot.run(TOKEN)