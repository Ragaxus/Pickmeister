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
        rgx = r"(?:(?P<quantity>\d+) )?(?P<name>.+)"
        matches = [re.match(rgx, line) for line in input.splitlines()]
        quantities = [m.groupdict()["quantity"] for m in matches]
        names = [m.groupdict()["name"] for m in matches]
        cards_info = self.fetch_cards_info(names)
        output_lines = []
        error_lines = []
        for (i,name) in enumerate(names):
            if cards_info[name] is not None:
                set_info = ', '.join(cards_info[name]["sets"]).upper() 
                output_lines.append(f"**{quantities[i] or 1} {name}** ({cards_info[name]['color']}) *({set_info})*")
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


def test_make_embed_content():
    example_input = """"4 Burglar Rat
3 Canyon Slough
2 Concealing Curtains // Revealing Eye
3 Dash Hopes
3 Defile
2 Extirpate
3 Grenzo, Dungeon Warden
4 Lightning Bolt
4 Mountain
2 Nezumi Shortfang // Stabwhisker the Odious
2 Reckoner's Bargain
3 Slavering Nulls
3 Stormfist Crusader
4 Sudden Edict
6 Swamp
3 Temple of Malice
2 Tourach, Dread Cantor
2 Unearth
4 Virus Beetle
1 Witch's Cottage"""

    print(Pickmeister().make_embed_content(example_input))

if __name__ == '__main__':
    if os.getenv('ENVIRONMENT') == 'test':
        test_make_embed_content()
    else:
        Pickmeister().run()