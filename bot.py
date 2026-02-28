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

COOLDOWN_DURATION = 3 * 60 * 60
ESPORT_COOLDOWN = 24 * 60 * 60

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
# RAPPORT EQUIPE SECURISE
# =========================

@bot.command()
async def rapport(ctx, equipe: discord.Role = None, *, contenu: str = None):

    if equipe is None or contenu is None:
        await ctx.send("❌ Utilisation : `!rapport @NomEquipe contenu`")
        return

    if not any(role.name == "Capitaine" for role in ctx.author.roles):
        await ctx.send("❌ Tu dois être Capitaine.")
        return

    if equipe not in ctx.author.roles:
        await ctx.send("❌ Tu n'es pas le capitaine de cette équipe.")
        return

    guild = ctx.guild
    direction_role = discord.utils.get(guild.roles, name="🎯 Direction Esport")
    manager_role = discord.utils.get(guild.roles, name="📊 Manager")

    rapport_channel = discord.utils.get(guild.text_channels, name="rapport")

    if rapport_channel is None:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            direction_role: discord.PermissionOverwrite(view_channel=True),
            manager_role: discord.PermissionOverwrite(view_channel=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }
        rapport_channel = await guild.create_text_channel("rapport", overwrites=overwrites)

    embed = discord.Embed(
        title=f"📋 Rapport - {equipe.name}",
        color=discord.Color.red(),
        timestamp=datetime.now()
    )

    embed.add_field(name="🏷 Équipe", value=equipe.mention, inline=False)
    embed.add_field(name="👤 Capitaine", value=ctx.author.mention, inline=False)
    embed.add_field(name="📝 Contenu", value=contenu, inline=False)

    await rapport_channel.send(embed=embed)
    await ctx.send("✅ Rapport envoyé.")

# =========================
# INSCRIPTION TEAM ESPORT
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
        fiches[user_id]["maj"] = f"Validé le {datetime.now().strftime('%d/%m/%Y %H:%M')}"

        sauvegarder_fiches(fiches)

        try:
            await self.member.send("🎮 Inscription Esport ACCEPTÉE.")
        except:
            pass

        await interaction.response.send_message("✅ Validé.")
        await asyncio.sleep(3)
        await interaction.channel.delete()

    @discord.ui.button(label="❌ Refuser", style=discord.ButtonStyle.danger)
    async def refuse(self, interaction: discord.Interaction, button: discord.ui.Button):

        if "Staff" not in [r.name for r in interaction.user.roles]:
            await interaction.response.send_message("❌ Staff uniquement.", ephemeral=True)
            return

        await interaction.response.send_message(
            "📝 Écris le motif du refus (5 minutes).",
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

        fiches[user_id]["statut_esport"] = "Refusé"
        fiches[user_id]["motif_refus_esport"] = motif
        fiches[user_id]["maj"] = f"Refusé le {datetime.now().strftime('%d/%m/%Y %H:%M')}"

        sauvegarder_fiches(fiches)

        try:
            await self.member.send(f"❌ Inscription refusée.\nMotif : {motif}")
        except:
            pass

        await interaction.followup.send("❌ Refus enregistré.")
        await asyncio.sleep(3)
        await interaction.channel.delete()

# =========================
# TICKET SYSTEM
# =========================

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Inscription Team Esport", emoji="🔥"),
            discord.SelectOption(label="Demande Staff", emoji="👨‍🏫"),
        ]
        super().__init__(placeholder="Choisis le type de ticket...",
                         min_values=1,
                         max_values=1,
                         options=options)

    async def callback(self, interaction: discord.Interaction):

        guild = interaction.guild
        member = interaction.user
        fiches = charger_fiches()
        user_id = str(member.id)
        now = time.time()

        # Cooldown Esport
        if self.values[0] == "Inscription Team Esport":

            if user_id in fiches and "cooldown_esport" in fiches[user_id]:
                remaining = fiches[user_id]["cooldown_esport"] - now
                if remaining > 0:
                    hours = int(remaining // 3600)
                    minutes = int((remaining % 3600) // 60)

                    try:
                        await member.send(
                            f"⏳ Tu dois attendre {hours}h {minutes}min avant de repostuler."
                        )
                    except:
                        pass

                    await interaction.response.send_message(
                        "❌ Cooldown actif. Vérifie tes MP.",
                        ephemeral=True
                    )
                    return

            if user_id not in fiches:
                fiches[user_id] = {}

            fiches[user_id]["cooldown_esport"] = now + ESPORT_COOLDOWN
            sauvegarder_fiches(fiches)

        existing_channel = discord.utils.get(
            guild.text_channels,
            name=f"ticket-{member.id}"
        )

        if existing_channel:
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

        if self.values[0] == "Inscription Team Esport":
            await channel.send(
                "🔥 **Inscription Team Esport**\n\n"
                "Réponds aux questions :\n"
                "Pseudo en jeu :\n"
                "Âge :\n"
                "Rôle principal :\n"
                "Rank + Peak :\n"
                "OP.GG :\n"
                "Disponibilités :\n"
                "Expérience équipe :\n"
                "Tournois ?\n"
                "Pourquoi nous rejoindre ?\n"
                "Objectif saison :",
                view=ValidateEsportView(member)
            )

        await interaction.response.send_message("✅ Ticket créé.", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

@bot.command()
async def ticketpanel(ctx):
    embed = discord.Embed(
        title="🎟 Support",
        description="Sélectionne un type de ticket.",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed, view=TicketView())

# =========================
# LANCEMENT
# =========================

bot.run(TOKEN)