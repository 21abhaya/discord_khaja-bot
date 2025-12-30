import os
import discord
import random

from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

token = os.getenv('DISCORD_TOKEN')


class ModalForSomethingElse(discord.ui.Modal, title="Custom Order"):
    
    custom_item = discord.ui.TextInput(
        label='What would you like to have today?',
        placeholder='e.g. Veg Chowmein, Chicken Momo Fry...',
        min_length=1,
        max_length=50
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'Ordered:{self.custom_item}', ephemeral=True)
        
        
        
class KhajaTimeView(discord.ui.View, timeout=900.0):
    
    votes = {}
    
    @discord.ui.button(label="Half", style=discord.ButtonStyle.primary)
    async def half_button_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.votes[interaction.user.id] = "Half"
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
        
    @discord.ui.button(label="Full", style=discord.ButtonStyle.danger)
    async def full_button_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.votes[interaction.user.id] = "Full"
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
        
    @discord.ui.button(label="Something else", style=discord.ButtonStyle.secondary)
    async def something_else_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_modal(ModalForSomethingElse())