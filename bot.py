import discord
from discord.ext import commands
import json
import os
from datetime import datetime

# =========================
# CONFIG
# =========================

import os
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
# CREER FICHE
# =========================

@bot.command()
@commands.has_role("Staff")
async def fiche(ctx, member: discord.Member):

    fiches = charger_fiches()

    if str(member.id) in fiches:
        await ctx.send("❌ Ce joueur a déjà une fiche.")
        return

    data = {
        "prof": ctx.author.name,
        "rang": "",
        "objectif": "",
        "poste": "",
        "points_forts": "",
        "points_faibles": "",
        "maj": f"Créée par {ctx.author.name} le {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    }

    fiches[str(member.id)] = data
    sauvegarder_fiches(fiches)

    await ctx.send(f"📊 Fiche créée pour {member.mention}")

# =========================
# MAJ FICHE
# =========================

@bot.command()
@commands.has_role("Staff")
async def majfiche(ctx, member: discord.Member, champ: str, *, valeur: str):

    fiches = charger_fiches()

    if str(member.id) not in fiches:
        await ctx.send("❌ Ce joueur n'a pas de fiche.")
        return

    champs_valides = ["rang", "objectif", "poste", "points_forts", "points_faibles"]

    if champ not in champs_valides:
        await ctx.send("❌ Champ invalide.\nUtilise : rang, objectif, poste, points_forts, points_faibles")
        return

    fiches[str(member.id)][champ] = valeur
    fiches[str(member.id)]["maj"] = f"Dernière mise à jour par {ctx.author.name} le {datetime.now().strftime('%d/%m/%Y %H:%M')}"

    sauvegarder_fiches(fiches)

    await ctx.send(f"✅ Fiche mise à jour pour {member.mention}")

# =========================
# VOIR FICHE
# =========================

@bot.command()
async def voirfiche(ctx, member: discord.Member):

    fiches = charger_fiches()

    if str(member.id) not in fiches:
        await ctx.send("❌ Ce joueur n'a pas de fiche.")
        return

    # Accès autorisé uniquement Prof ou joueur concerné
    if "Prof" not in [role.name for role in ctx.author.roles] and ctx.author != member:
        await ctx.send("❌ Tu n'as pas accès à cette fiche.")
        return

    data = fiches[str(member.id)]

    embed = discord.Embed(
        title=f"📊 Fiche Joueur - {member.name}",
        color=discord.Color.gold()
    )

    embed.add_field(name="👨‍🏫 Prof référent", value=data["prof"], inline=False)
    embed.add_field(name="🏅 Rang actuel", value=data["rang"] or "Non défini", inline=False)
    embed.add_field(name="🎯 Objectif", value=data["objectif"] or "Non défini", inline=False)
    embed.add_field(name="🧭 Poste principal", value=data["poste"] or "Non défini", inline=False)
    embed.add_field(name="💪 Points forts", value=data["points_forts"] or "Non défini", inline=False)
    embed.add_field(name="⚠ Points faibles", value=data["points_faibles"] or "Non défini", inline=False)
    embed.set_footer(text=data["maj"])

    await ctx.send(embed=embed)

# =========================

bot.run("")