"""A Discord bot that listens for posts in a particular channel. If the post contains an
attachment, the bot assumes that attachment is a deck, and saves that deck to a given
Google spreadsheet."""

import os
import re
import json
from datetime import date
from xml.etree.ElementTree import PI

import requests

import chardet
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
                content = msg.content
                desc = self.make_embed_content(content)
                embed=discord.Embed(title=f'Pull for {date.today().strftime("%m/%d/%Y")}', description=desc, color=0xFF5733)
                embed_message = await self.channel.send(embed=embed)
                await embed_message.add_reaction(clear_react_emoji)
                await msg.channel.send(embed_message.jump_url)

        @client.event
        async def on_raw_reaction_add(payload):  
            """When a user reacts with X, delete the post."""
            channel = client.get_channel(payload.channel_id)
            if payload.member.id == client.user.id:
                    return
            msg = await channel.fetch_message(payload.message_id)
            if msg.channel.type == discord.ChannelType.private:
                pass
            emoji = payload.emoji.name #This is the unicode codepoint of the emoji
            if emoji == clear_react_emoji:
                await msg.delete()

    
    def run(self):
        self.client.run(self.DISCORD_TOKEN)

    def make_embed_content(self, input):
        """Given the content of a message, creates the embed for that message."""
        matches = [re.match(r"(\d+) (.+)", line) for line in input.splitlines()]
        quantities = [m.group(1) for m in matches]
        names = [m.group(2) for m in matches]
        all_set_info = self.get_all_sets_of_cards(names)
        output_lines = []
        for (i,name) in enumerate(names):
            if all_set_info[name] is not None:
                set_info = ', '.join(all_set_info[name]).upper() 
            else: 
                set_info = 'set info not found'    
            output_lines.append(f"**{quantities[i]} {name}** *({set_info})*")
        return '\n'.join(output_lines)

    def get_all_sets_of_cards(self,names):
        set_info = {}
        for name in names:
            request = {"q": f'!"{name}"', "unique": "prints"}
            response = requests.get("https://api.scryfall.com/cards/search", headers={'Cache-Control': 'no-cache'}, params=request)
            if response.status_code == 200:
                sets = list(set(list(map(lambda card: card["set"], response.json()["data"]))))
            else:
                sets = None
            set_info[name] = sets
        return set_info


def test_make_embed_content():
    example_input = """1 Shock
3 Snow-Covered Swamp
1 Beck // Call"""

    print(Pickmeister().make_embed_content(example_input))

if __name__ == '__main__':
    Pickmeister().run()