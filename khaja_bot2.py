import os
import discord
import asyncio

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
    
    def __init__(self, initiator):
        super().__init__(timeout=60)
        self.initiator = initiator
        self.votes = {}
    
    def create_embed(self):
        embed = discord.Embed(title="Today's Khaja Poll", color=discord.Color.blue())
        
        full_count = 0
        half_count = 0
        others_count = 0
        for u, choice in self.votes.items(): 
            if choice not in ["Full", "Half"]:
                others_count += 1
            if choice == "Full":
                full_count += 1
            if choice == "Half":
                half_count += 1

        embed.add_field(name="Full", value=full_count if full_count else "None", inline=True)
        embed.add_field(name="Half", value=half_count if half_count else "None", inline=True)
        embed.add_field(name="Something else", value=others_count if others_count else "None", inline=True)
        return embed
    
    def get_poll_summary(self):
        return " Testing Summary from poll!"
    
    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        summary = self.get_poll_summary()
        await self.initiator.send(f"Here is the poll summary:{summary}")
        
    
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
        
    
@bot.command(name='khaja')
async def khaja(ctx):
    view = KhajaTimeView(initiator=ctx.author)
    all_channel_members = ctx.channel.members
    await ctx.send("Pick your portion!", embed=view.create_embed(), view=view)
    await asyncio.sleep(30)
    
    members_who_have_not_voted_yet = [
        member for member in all_channel_members if not member.bot and member.id not in view.votes
    ]
    if members_who_have_not_voted_yet:
        mentions = [m.mention for m in members_who_have_not_voted_yet]
        reminder_msg = f"🔔 **Lunch Reminder!**\nQuick {', '.join(mentions)}, please cast a vote so we can get lunch!"
        await ctx.send(reminder_msg)
    
bot.run(token)