import os
import discord
import asyncio
import datetime

from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

token = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

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
    
    def __init__(self, initiator, channel_members):
        super().__init__(timeout=30)
        self.initiator = initiator
        self.channel_members = channel_members
        self.votes = {}
    
    def create_embed(self):
        embed = discord.Embed(
            title="Today's Khaja Poll", 
            color=discord.Color.blue()
        )
        
        full_count = list(self.votes.values()).count("Full")
        half_count = list(self.votes.values()).count("Half")
        not_today_count = list(self.votes.values()).count("Not Today")
        others_count = len(self.votes) - (full_count + half_count + not_today_count)
    
        embed.add_field(
            name="Full", 
            value=f"**{full_count}**" if full_count else "None", 
            inline=True
        )
        embed.add_field(
            name="Half", 
            value=f"**{half_count}**" if half_count else "None", 
            inline=True
        )
        embed.add_field(
            name="Not Today", 
            value=f"**{not_today_count}**" if not_today_count else "None", 
            inline=True
        )
        embed.add_field(
            name="Will be having something else today!", 
            value=f"**{others_count}**" if others_count else "None", 
            inline=False
        )
        embed.add_field(
            name="\u200b", # Zero-width space
            value="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬", 
            inline=False
        )
        return embed
    
    def get_poll_summary(self):
        total_votes = len(self.votes)
        full_count = list(self.votes.values()).count("Full")
        half_count = list(self.votes.values()).count("Half")
        
        custom_orders = []
        did_not_order_today = []
        
        did_not_vote_today = [
            member.name for member in self.channel_members if not member.bot and member.id not in self.votes
        ]
        print("No Vote Today:", did_not_vote_today)
        for user_id, choice in self.votes.items():
            
            member = discord.utils.get(self.channel_members, id=user_id)
            name = member.name if member else f"Unknown-{user_id}"
            
            
            if choice == "Not Today":
                did_not_order_today.append(name)
            elif choice not in ["Full", "Half"]:
                custom_orders.append(f"• **{name}**: {choice}")
            
        msg = f"\n✅ **Summarizing Poll Results:**\n- **Total Votes:** {total_votes}\n"
        msg += f"\n- **Full:** {full_count}\n- **Half:** {half_count}\n"
        
        if custom_orders:
            msg += "\n📝 **Custom Orders:**\n" + "\n- ".join(custom_orders)
        if did_not_order_today:
            msg += "\n🙅 **Not Joining:**\n" + "\n- ".join(did_not_order_today)
        if did_not_vote_today:
            msg += "\n❌ **No Votes from:**\n" + "\n- ".join(did_not_vote_today)    
        
        return msg
        
        
            

    @discord.ui.button(label="Full", style=discord.ButtonStyle.primary)
    async def full_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.votes[interaction.user.id] = "Full"
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Half", style=discord.ButtonStyle.success)
    async def half_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.votes[interaction.user.id] = "Half"
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
        
    @discord.ui.button(label="Something else", style=discord.ButtonStyle.secondary)
    async def something_else(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalForSomethingElse(self))
        
    @discord.ui.button(label="Not Today", style=discord.ButtonStyle.danger)
    async def not_today_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.votes[interaction.user.id] = "Not Today"
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
        
    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        summary = self.get_poll_summary()
        print("Poll Closed!")
        await self.initiator.send(f"**Testing khaja bot <t:{int(datetime.datetime.now().timestamp())}:D>:**\n{summary}")
        
    
@bot.command(name='khaja')
async def khaja(ctx):
    view = KhajaTimeView(initiator=ctx.author, channel_members=ctx.channel.members)
    all_channel_members = ctx.channel.members
    await ctx.send("Pick your portion!", embed=view.create_embed(), view=view)
    await asyncio.sleep(15)
    
    members_who_have_not_voted_yet = [
        member for member in all_channel_members if not member.bot and member.id not in view.votes
    ]
    if members_who_have_not_voted_yet:
        mentions = [m.mention for m in members_who_have_not_voted_yet]
        reminder_msg = f"🔔 **Lunch Reminder!**\nQuick {', '.join(mentions)}, please cast a vote so we can get lunch!"
        await ctx.send(reminder_msg)
    
bot.run(token)