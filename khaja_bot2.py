import os
import discord

from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

token = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

class ModalForSomethingElse(discord.ui.Modal, title="Custom Order"):
    
    def __init__(self, view):
        super().__init__()
        self.view = view
    
    custom_item = discord.ui.TextInput(
        label='What would you like to have today?',
        placeholder='e.g. Veg Chowmein, Chicken Momo Fry...',
        min_length=1,
        max_length=50
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        self.view.votes[interaction.user.id] = self.custom_item.value
        await interaction.response.edit_message(embed=self.view.create_embed(), view=self.view)
        
        
        
class KhajaTimeView(discord.ui.View):
    
    def __init__(self):
        super().__init__(timeout=None)
        self.votes = {}
        
    def create_embed(self):
        embed = discord.Embed(title="Today's Khaja Poll", color=discord.Color.blue())
        
        full = [f"<@{u}>" for u, choice in self.votes.items() if choice == "Full"]
        half = [f"<@{u}>" for u, choice in self.votes.items() if choice == "Half"]
        others = [f"<@{u}> ({choice})" for u, choice in self.votes.items() if choice not in ["Full", "Half"]]

        embed.add_field(name="Full", value="\n".join(full) if full else "None", inline=True)
        embed.add_field(name="Half", value="\n".join(half) if half else "None", inline=True)
        embed.add_field(name="Others", value="\n".join(others) if others else "None", inline=False)
        return embed
    
    @discord.ui.button(label="Half", style=discord.ButtonStyle.primary)
    async def half_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.votes[interaction.user.id] = "Half"
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Full", style=discord.ButtonStyle.danger)
    async def full_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.votes[interaction.user.id] = "Full"
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Something else", style=discord.ButtonStyle.secondary)
    async def something_else(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalForSomethingElse(self))
        
    
@bot.command(name='khaja-momo')
async def khaja(ctx):
    view = KhajaTimeView()
    await ctx.send("Pick your portion!", embed=view.create_embed(), view=view)
    
    
bot.run(token)