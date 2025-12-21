
import os
import discord 

from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

token = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.default()
intents.message_content = True


def khaja_poll(khaja_item: str):
    
    poll = discord.Poll(
        question=f"Hey guys, we're having {khaja_item} today, please vote below how may you want it:", 
        duration=timedelta(hours=1),
    )
    
    if khaja_item in ["Momo", "momo", "MOMO"]:
        poll.add_answer(text="Chicken Steam")
        poll.add_answer(text="Chicken Fry")
        poll.add_answer(text="Buff Steam")
        poll.add_answer(text="Buff Fry")
        poll.add_answer(text="Veg Steam")
        poll.add_answer(text="Veg Fry")
    
    if khaja_item not in ["Momo", "momo", "MOMO"]:        
        poll.add_answer(text="Full")
        poll.add_answer(text="Half")
    
    if khaja_item in ["Chowmein", "chowmein"]:
        poll.add_answer(text="Veg Half")
        poll.add_answer(text="Veg Full")
        poll.add_answer(text="Egg Half")
        poll.add_answer(text="Egg Full")
        poll.add_answer(text="Buff Half")
        poll.add_answer(text="Buff Full")  
        
    poll.add_answer(text="I wanna try something else.")
    poll.add_answer(text="Not today!")
    return poll


class MyClient(discord.Client):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')

    async def on_message(self, message):
        if message.content.startswith("khajatime") and message.content.endswith("!"):
            content = message.content
            content_after_split = content.split()
            khaja_today = content_after_split[1]
            print(khaja_today)
            poll = khaja_poll(khaja_today)
            await message.channel.send(poll=poll)
        

client = MyClient(intents=intents)
client.run(token)