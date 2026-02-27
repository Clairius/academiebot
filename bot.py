import discord
from discord.ext import commands
import json
import os
from datetime import datetime

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
# FICHE SYSTEM
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

    @discord.ui.button(label="📊 Valider inscription", style=discord.ButtonStyle.green)
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
                "maj": f"Validé par {interaction.user.name}"
            }
            sauvegarder_fiches(fiches)

        await interaction.response.send_message(
            f"✅ Inscription validée et fiche créée pour {self.member.mention}"
        )

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Demande de Staff", emoji="👨‍🏫"),
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

        if self.values[0] == "Demande de Staff":
            await channel.send(
                f"👨‍🏫 **Demande Staff**\n\n"
                f"{member.mention}, quelle est ta demande ?",
                view=CloseTicketView()
            )
        else:
            await channel.send(
                f"📊 **Inscription Académique**\n\n"
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
@commands.has_role("Staff")
async def ticketpanel(ctx):
    embed = discord.Embed(
        title="🎟 Support Académique",
        description="Merci de sélectionner le type de demande ci-dessous.",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed, view=TicketView())

# =========================
# STRUCTURE (SAFE)
# =========================

@bot.command()
@commands.has_role("Directeur FLTA")
async def setupstructure(ctx):

    guild = ctx.guild

    if discord.utils.get(guild.categories, name="🧾 STAFF – Administratif"):
        await ctx.send("❌ Structure déjà existante.")
        return

    await guild.create_category("🧾 STAFF – Administratif")
    await guild.create_category("🎯 STAFF – Opérationnel")
    await guild.create_category("🎓 PROFESSEURS – Pôle pédagogique")

    await ctx.send("✅ Structure créée.")

# =========================
# VOCAUX
# =========================

@bot.command()
@commands.has_role("Directeur FLTA")
async def setupvocaux(ctx):

    guild = ctx.guild

    if discord.utils.get(guild.categories, name="👑 DIRECTION – Réunions"):
        await ctx.send("❌ Vocaux déjà existants.")
        return

    dir_cat = await guild.create_category("👑 DIRECTION – Réunions")
    await guild.create_voice_channel("🎙 direction-réunion", category=dir_cat)
    await guild.create_voice_channel("🔒 direction-privé", category=dir_cat)

    prof_cat = await guild.create_category("🎓 PROF – Réunions & Coaching")
    await guild.create_voice_channel("🎙 salle-professeurs", category=prof_cat)
    await guild.create_voice_channel("🎙 coaching-1", category=prof_cat)
    await guild.create_voice_channel("🎙 coaching-2", category=prof_cat)

    await ctx.send("✅ Vocaux créés.")

# =========================
# REUNION
# =========================

@bot.command()
@commands.has_role("Directeur FLTA")
async def reunion(ctx, nom: str):
    channel = await ctx.guild.create_voice_channel(f"🗓 réunion-{nom}")
    await ctx.send(f"🎙 Salon réunion créé : {channel.name}")

bot.run(TOKEN)