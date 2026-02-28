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

ACADEMIE_COOLDOWN = 3 * 60 * 60
ESPORT_COOLDOWN = 24 * 60 * 60

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# JSON
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
    print(f"Connecté en tant que {bot.user}")

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
        await ctx.send("❌ Tu n'es pas le capitaine de cette équipe.")
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
# INSCRIPTION ESPORT VIEW
# =========================

class ValidateEsportView(discord.ui.View):
    def __init__(self, member):
        super().__init__(timeout=None)
        self.member = member

    @discord.ui.button(label="✅ Valider", style=discord.ButtonStyle.green)
    async def validate(self, interaction: discord.Interaction, button: discord.ui.Button):

        if "Staff" not in [r.name for r in interaction.user.roles]:
            await interaction.response.send_message("❌ Staff uniquement.", ephemeral=True)
            return

        fiches = charger_fiches()
        user_id = str(self.member.id)

        if user_id not in fiches:
            fiches[user_id] = {}

        messages = []
        async for msg in interaction.channel.history(limit=50):
            if msg.author == self.member:
                messages.append(msg.content)

        fiches[user_id]["inscription_esport"] = "\n".join(messages[::-1])
        fiches[user_id]["statut_esport"] = "Accepté"
        fiches[user_id]["maj"] = datetime.now().strftime("%d/%m/%Y %H:%M")

        sauvegarder_fiches(fiches)

        await interaction.response.send_message("✅ Inscription validée.")
        await asyncio.sleep(3)
        await interaction.channel.delete()

    @discord.ui.button(label="❌ Refuser", style=discord.ButtonStyle.danger)
    async def refuse(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_message("📝 Écris le motif (5 minutes).", ephemeral=True)

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

        fiches[user_id]["statut_esport"] = "Refusé"
        fiches[user_id]["motif_refus_esport"] = motif
        fiches[user_id]["maj"] = datetime.now().strftime("%d/%m/%Y %H:%M")

        sauvegarder_fiches(fiches)

        await interaction.followup.send("❌ Refus enregistré.")
        await asyncio.sleep(3)
        await interaction.channel.delete()

# =========================
# TICKET SYSTEM
# =========================

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Inscription Académique", emoji="📊"),
            discord.SelectOption(label="Inscription Team Esport", emoji="🔥"),
            discord.SelectOption(label="Demande Staff", emoji="👨‍🏫")
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
        fiches = charger_fiches()
        user_id = str(member.id)
        now = time.time()

        if user_id not in fiches:
            fiches[user_id] = {}

        # ===== Cooldown Académie =====
        if self.values[0] == "Inscription Académique":
            if "cooldown_academie" in fiches[user_id]:
                remaining = fiches[user_id]["cooldown_academie"] - now
                if remaining > 0:
                    await interaction.response.send_message("⏳ Cooldown 3h actif.", ephemeral=True)
                    return
            fiches[user_id]["cooldown_academie"] = now + ACADEMIE_COOLDOWN

        # ===== Cooldown Esport =====
        if self.values[0] == "Inscription Team Esport":
            if "cooldown_esport" in fiches[user_id]:
                remaining = fiches[user_id]["cooldown_esport"] - now
                if remaining > 0:
                    hours = int(remaining // 3600)
                    minutes = int((remaining % 3600) // 60)
                    try:
                        await member.send(f"⏳ Tu dois attendre {hours}h {minutes}min.")
                    except:
                        pass
                    await interaction.response.send_message("❌ Cooldown actif. Vérifie tes MP.", ephemeral=True)
                    return
            fiches[user_id]["cooldown_esport"] = now + ESPORT_COOLDOWN

        sauvegarder_fiches(fiches)

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

        if self.values[0] == "Inscription Team Esport":
            await channel.send(
                "🔥 **Inscription Team Esport**\n\n"
                "Pseudo :\nÂge :\nRôle principal :\nRank + Peak :\nOP.GG :\n"
                "Disponibilités :\nExpérience équipe :\nTournois :\n"
                "Pourquoi nous rejoindre ?\nObjectif saison :",
                view=ValidateEsportView(member)
            )

        elif self.values[0] == "Inscription Académique":
            await channel.send("📊 **Inscription Académique**\n\nMerci de répondre aux questions.")

        elif self.values[0] == "Demande Staff":
            await channel.send(f"👨‍🏫 **Demande Staff**\n\n{member.mention} quel est ta demande ?")

        await interaction.response.send_message("✅ Ticket créé.", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

@bot.command()
async def ticketpanel(ctx):
    embed = discord.Embed(
        title="🎟 Support",
        description="Sélectionne une inscription",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed, view=TicketView())

# =========================
# START
# =========================

bot.run(TOKEN)