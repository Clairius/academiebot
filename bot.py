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
# SYSTEME JSON
# =========================

def charger_fiches():
    if os.path.exists(FICHIER):
        with open(FICHIER, "r") as f:
            return json.load(f)
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

    embed.add_field(name="👨‍🏫 Prof", value=data["prof"], inline=False)
    embed.add_field(name="🏅 Rang", value=data["rang"] or "Non défini", inline=False)
    embed.add_field(name="🎯 Objectif", value=data["objectif"] or "Non défini", inline=False)
    embed.add_field(name="🧭 Poste", value=data["poste"] or "Non défini", inline=False)
    embed.add_field(name="💪 Points forts", value=data["points_forts"] or "Non défini", inline=False)
    embed.add_field(name="⚠ Points faibles", value=data["points_faibles"] or "Non défini", inline=False)
    embed.set_footer(text=data["maj"])

    await ctx.send(embed=embed)

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

    # =========================
    # ACCEPTER
    # =========================
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
            await self.member.send("🎉 Ton inscription à l'académie a été ACCEPTÉE !")
        except:
            pass

        await interaction.response.send_message(
            f"✅ Inscription acceptée pour {self.member.mention}"
        )

        await interaction.channel.send("🔒 Fermeture du ticket dans 3 secondes...")
        await asyncio.sleep(3)
        await interaction.channel.delete()

    # =========================
    # REFUSER
    # =========================
    @discord.ui.button(label="❌ Refuser l'inscription", style=discord.ButtonStyle.danger)
    async def refuse(self, interaction: discord.Interaction, button: discord.ui.Button):

        if "Staff" not in [r.name for r in interaction.user.roles]:
            await interaction.response.send_message("❌ Réservé au Staff.", ephemeral=True)
            return

        await interaction.response.send_message(
            "📝 Merci d'écrire le MOTIF du refus dans ce salon (60 secondes).",
            ephemeral=True
        )

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await bot.wait_for("message", timeout=60.0, check=check)
            motif = msg.content
        except:
            await interaction.followup.send("❌ Temps écoulé. Refus annulé.")
            return

        try:
            await self.member.send(
                f"❌ Ton inscription a été REFUSÉE.\n\n📌 Motif : {motif}"
            )
        except:
            pass

        await interaction.followup.send(
            f"❌ Inscription refusée pour {self.member.mention}\n📌 Motif : {motif}"
        )

        await interaction.channel.send("🔒 Fermeture du ticket dans 3 secondes...")
        await asyncio.sleep(3)
        await interaction.channel.delete()

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Demande Staff", emoji="👨‍🏫"),
            discord.SelectOption(label="Inscription Académique", emoji="📊")
        ]
        super().__init__(
            placeholder="Choisis le type de ticket...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        guild = interaction.guild
        member = interaction.user
        staff_role = discord.utils.get(guild.roles, name="Staff")

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
            f"ticket-{member.name}",
            category=category,
            overwrites=overwrites
        )

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

bot.run(TOKEN)