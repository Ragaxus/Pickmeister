"""A Discord bot that listens for posts in a particular channel. If the post contains an
attachment, the bot assumes that attachment is a deck, and saves that deck to a given
Google spreadsheet."""

import os
import re
from datetime import date
import time

import requests

from dotenv import load_dotenv
import discord

class Pickmeister:
    def __init__(self):
        load_dotenv()
        self.DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
        self.CHANNEL_NAME = os.getenv('CHANNEL')
        self.SERVER_ID = os.getenv('DISCORD_SERVER_ID')
        self.channel = None
        self.client = discord.Client()
        client = self.client
        clear_react_emoji = '❌'

        @client.event
        async def on_ready():
            """The function that handles the 'bot is connected' event."""
            print(f'{client.user} has connected to Discord!')
            guild = client.get_guild(int(self.SERVER_ID))
            self.channel = next(ch for ch in guild.text_channels if ch.name == self.CHANNEL_NAME)

        @client.event
        async def on_message(msg):
            if msg.author == client.user:
                    return
            """The function that handles both DMs and channel messages."""
            if not msg.guild: # (i.e. it is a DM):
                try:
                    await msg.channel.send("Fetching card data...")
                    content = msg.content
                    desc = self.make_embed_content(content)
                    embed=discord.Embed(title=f'Pull for {date.today().strftime("%m/%d/%Y")}', description=desc, color=0xFF5733)
                    embed_message = await self.channel.send(embed=embed)
                    await embed_message.add_reaction(clear_react_emoji)
                    await msg.channel.send(embed_message.jump_url)
                except:
                    await msg.channel.send("An error occurred; please contact store to resolve.")

        @client.event
        async def on_raw_reaction_add(payload):  
            """When a user reacts with X, delete the post."""
            channel = client.get_channel(payload.channel_id)
            if payload.member.id == client.user.id:
                return
            try:
                msg = await channel.fetch_message(payload.message_id)
                if msg.channel.type == discord.ChannelType.private:
                    pass
                emoji = payload.emoji.name #This is the unicode codepoint of the emoji
                if emoji == clear_react_emoji:
                    await msg.delete()
            except:
                pass
    
    def run(self):
        self.client.run(self.DISCORD_TOKEN)

    def make_embed_content(self, input):
        """Given the content of a message, creates the embed for that message."""
        rgx = r"(?:(?P<quantity>\d+) )?(?:(?P<name>[^{]+))( \{(?:(?P<annotation>.+))\}){0,1}$"
        matches = [re.match(rgx, line) for line in input.splitlines()]
        quantities = [m.groupdict()["quantity"] for m in matches]
        names = [m.groupdict()["name"] for m in matches]
        annotations = [m.groupdict()["annotation"] for m in matches]
        cards_info = self.fetch_cards_info(names)
        output_lines = []
        error_lines = []
        for (i,name) in enumerate(names):
            if cards_info[name] is not None:
                set_info = ', '.join(cards_info[name]["sets"]).upper() 
                output_lines.append(f"**{quantities[i] or 1} {name}{', '+annotations[i] if annotations[i] else ''}** ({cards_info[name]['color']}) *({set_info})*")
            else:
                error_lines.append(name)
        if len(error_lines) > 0:
            output_lines.append("\nCould not find data for: ")
            output_lines += error_lines
        return '\n'.join(output_lines)

    def fetch_cards_info(self,names):
        set_info = {}
        for name in names:
            request = {"q": f'!"{name}"', "unique": "prints"}
            response = requests.get("https://api.scryfall.com/cards/search", headers={'Cache-Control': 'no-cache'}, params=request)
            time.sleep(.05)
            card_info = response.json()
            if response.status_code == 200:
                sets = list(set(list(map(lambda card: card["set"], card_info["data"]))))
                color = self.get_card_color(card_info["data"][0])
                set_info[name] = {"sets": sets, "color": color}
            else:
                set_info[name] = None
        return set_info
    
    def get_card_color(self, card_data):
        if "card_faces" in card_data:
            card = card_data["card_faces"][0]
        else:
            card = card_data 
        if "colors" in card_data:
            colors = card_data["colors"]
        else:
            colors = card["colors"]
        if "Land" in card["type_line"]:
            return "L"
        elif len(colors) > 1:
            return "M"
        elif len(colors) > 0:
            return colors[0]
        elif "Artifact" in card["type_line"]:
            return "A"
        else:
            return "C"


if __name__ == '__main__':
        Pickmeister().run()