import os
import sys
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
bot.is_poll_active = False

class ModalForSomethingElse(discord.ui.Modal, title="Custom Order"):
    
    def __init__(self, view):
        super().__init__()
        self.view = view
    
    custom_item = discord.ui.TextInput(
        label='What would you like to have today?',
        placeholder='e.g. Veg Chowmein, Chicken Momo Fry...',
        min_length=1,
        max_length=100
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        self.view.votes[interaction.user.id] = self.custom_item.value
        sys.stdout.write(f"\n📝 {interaction.user.name} custom order: {self.custom_item.value}\n")
        await interaction.response.edit_message(embed=self.view.create_embed(), view=self.view)
        

        
class KhajaTimeView(discord.ui.View):
    
    def __init__(self, initiator, channel_members):
        super().__init__(timeout=900)
        self.initiator = initiator
        self.channel_members = channel_members
        self.message = None
        self.votes = {}
    
    def create_embed(self):
        embed = discord.Embed(
            title=f"Khaja Poll for <t:{int(datetime.datetime.now().timestamp())}:D>:", 
            color=discord.Color.blue()
        )
        
        full_count = list(self.votes.values()).count("Full")
        half_count = list(self.votes.values()).count("Half")
        not_today_count = list(self.votes.values()).count("Not Today")
        others_count = len(self.votes) - (full_count + half_count + not_today_count)
    
        embed.add_field(
            name="Full Portion", 
            value=f"**{full_count}**" if full_count else "None", 
            inline=True
        )
        embed.add_field(
            name="Half Portion", 
            value=f"**{half_count}**" if half_count else "None", 
            inline=True
        )
        embed.add_field(
            name="Not Today", 
            value=f"**{not_today_count}**" if not_today_count else "None", 
            inline=True
        )
        embed.add_field(
            name="Something else", 
            value=f"**{others_count}**" if others_count else "None", 
            inline=False
        )
        embed.add_field(
            name="\u200b", # Zero-width space
            value="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬", 
            inline=False
        )
        return embed
    
    def get_poll_summary(self):
        total_votes = len(self.votes)
        full_count = list(self.votes.values()).count("Full")
        half_count = list(self.votes.values()).count("Half")
        
        did_not_vote_today = [
            member.name for member in self.channel_members if not member.bot and member.id not in self.votes
        ]
        
        members_who_chose_full = []
        members_who_chose_half = []
        custom_orders = []
        did_not_order_today = []
        
        for user_id, choice in self.votes.items():
            
            member = discord.utils.get(self.channel_members, id=user_id)
            name = member.name if member else f"Unknown-{user_id}"
            
            if choice not in ["Full", "Half", "Not Today"]:
                custom_orders.append(f"**{name}**: {choice}")
            if choice == "Full":
                members_who_chose_full.append(name)
            if choice == "Half":
                members_who_chose_half.append(name)
            if choice == "Not Today":
                did_not_order_today.append(name)
            
        msg = f"\n🗳️ **Total Votes:** {total_votes}\n"

        if full_count:
            msg += f"\n🌕 **Full Portion:** {full_count}\n- " + "\n- ".join(members_who_chose_full) + "\n"
        if half_count:
            msg += f"\n🌓 **Half Portion:** {half_count}\n- " + "\n- ".join(members_who_chose_half) + "\n"

        if custom_orders:
            msg += f"\n📝 **Custom Orders:** {len(custom_orders)}\n- " + "\n- ".join(custom_orders) + "\n"
        if did_not_order_today:
            msg += f"\n🙅 **Not Joining:** {len(did_not_order_today)}\n- " + "\n- ".join(did_not_order_today) + "\n"
        if did_not_vote_today:
            msg += f"\n❌ **No Votes from:** {len(did_not_vote_today)}\n- " + "\n- ".join(did_not_vote_today) + "\n"   
        msg += "\n---------------------------- END SUMMARY ----------------------------\n"
        
        return msg
            

    @discord.ui.button(label="Full", style=discord.ButtonStyle.primary)
    async def full_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.votes[interaction.user.id] = "Full"
        sys.stdout.write(f"\n🌕 {interaction.user.name} voted: Full\n")
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Half", style=discord.ButtonStyle.success)
    async def half_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.votes[interaction.user.id] = "Half"
        sys.stdout.write(f"\n🌓 {interaction.user.name} voted: Half\n")
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
        
    @discord.ui.button(label="Something else", style=discord.ButtonStyle.secondary)
    async def something_else(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalForSomethingElse(self))
        
    @discord.ui.button(label="Not Today", style=discord.ButtonStyle.danger)
    async def not_today_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.votes[interaction.user.id] = "Not Today"
        sys.stdout.write(f"\n🙅 {interaction.user.name} voted: Not Today\n")
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
        
    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
            
        bot.is_poll_active = False
        
        summary = self.get_poll_summary()
        await self.initiator.send(f"**✅ Poll Summary from khaja bot on <t:{int(datetime.datetime.now().timestamp())}:D>:**\n{summary}")
        if hasattr(self, 'message'):
            try:
                await self.message.edit(content="🛑 **This poll is now closed!**", view=None)
            except discord.HTTPException as e:
                print(f"Reminder cleanup failed: {e}")
                pass
        print("Poll Closed!")
        
    
@bot.command(name='khaja')
async def khaja(ctx):
    
    if bot.is_poll_active:
        await ctx.send("🛑 A poll is already in progress! Please wait for it to finish.")
        return 
    
    bot.is_poll_active = True
    
    try:
        view = KhajaTimeView(initiator=ctx.author, channel_members=ctx.channel.members)
        all_channel_members = ctx.channel.members
        view.message = await ctx.send("Pick your portion!", embed=view.create_embed(), view=view)
        await asyncio.sleep(300)
        
        members_who_have_not_voted_yet = [
            member for member in all_channel_members if not member.bot and member.id not in view.votes
        ]
        
        if members_who_have_not_voted_yet:
            try:
                mentions = [m.mention for m in members_who_have_not_voted_yet]
                reminder_msg = await ctx.send(f"🔔 **Lunch Reminder!**\nQuick {', '.join(mentions)}, please cast a vote so we can get lunch!")
                print("Sent reminder message!")
                await asyncio.sleep(150)
                await reminder_msg.delete()
                print("Deleted Reminder Message!")
            except discord.HTTPException as e:
                print(f"Reminder cleanup failed: {e}")
                pass
    
    finally:
        bot.is_poll_active = False

bot.run(token)