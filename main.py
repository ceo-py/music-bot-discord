import discord
import pafy
import youtube_dl
from discord.ext import commands
from discord_buttons_plugin import *
import urllib.request
import json
import urllib
from pytube import Playlist
from requests_html import HTMLSession

client = commands.Bot(command_prefix=["?", "/"], help_command=None)
TOKEN = ("YOUR TOKEN HERE")
buttons = ButtonsClient(client)
song_queue = {}


@client.event
async def on_ready():
    await client.change_presence(activity=discord.Game(name='Playing your awesome music!!!'))


intents = discord.Intents.default()
intents.members = True


class Player(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.setup()

    def setup(self):
        for guild in self.bot.guilds:
            song_queue[guild.id] = []

    async def check_queue(self, ctx):
        if len(song_queue[ctx.guild.id]) > 0:
            await self.play_song(ctx, song_queue[ctx.guild.id][0])
            song_queue[ctx.guild.id].pop(0)

    async def search_song(self, amount, song, get_url=False):
        info = await self.bot.loop.run_in_executor(None, lambda: youtube_dl.YoutubeDL(
            {"format": "bestaudio", "quiet": True}).extract_info(f"ytsearch{amount}:{song}", download=False,
                                                                 ie_key="YoutubeSearch"))
        if len(info["entries"]) == 0: return None

        return [entry["webpage_url"] for entry in info["entries"]] if get_url else info

    async def play_song(self, ctx, song):
        url = pafy.new(song).getbestaudio().url
        ctx.voice_client.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(url)),
                              after=lambda error: self.bot.loop.create_task(self.check_queue(ctx)))
        ctx.voice_client.source.volume = 0.5
        self.name_song = pafy.new(song).title
        await ctx.send(f":musical_note: `{self.name_song}`")
        await play_buttons(ctx)

    @commands.command(aliases=['pl'])
    async def playlist(self, ctx, *, song=None):
        p = Playlist(song)
        number_songs = 0
        for number_songs, _ in enumerate(p,1):
            song_queue[ctx.guild.id].append(_)
            if number_songs == 20:
                break
        try:
            await ctx.author.voice.channel.connect()
        except:
            pass
        if song is None:
            return await ctx.send("You must include a playlist.\nTip - `type ?pl playlist url from youtube`")

        if ctx.voice_client is None:
            return await ctx.send(
                "I must be in a voice channel to play a song.\nTip enter in channel that you can hear voice and `type // song name`")

        await self.play_song(ctx, song_queue[ctx.guild.id][0])
        song_queue[ctx.guild.id].pop(0)
        await ctx.send(f"{number_songs} songs has been added to the playlist!")

    @commands.command(aliases=['p', 's', 'r'])
    async def play(self, ctx, *, song=None):
        try:
            await ctx.author.voice.channel.connect()
        except:
            pass
        if song is None:
            return await ctx.send("You must include a song to play.\nTip - `type ?p song name`")

        if ctx.voice_client is None:
            return await ctx.send(
                "I must be in a voice channel to play a song.\nTip enter in channel that you can hear voice and `type // song name`")

        if not ("youtube.com/watch?" in song or "https://youtu.be/" in song):
            result = await self.search_song(1, song, get_url=True)
            if result is None:
                return await ctx.send("Sorry, I could not find the given song.")
            song = result[0]

        if ctx.voice_client.source is not None:
            queue_len = len(song_queue[ctx.guild.id])
            next_song = pafy.new(song).title
            if queue_len < 20:
                song_queue[ctx.guild.id].append(song)
                return await ctx.send(
                    f"Now playing {self.name_song}!\n**{next_song}** has been added to the playlist at position: {queue_len + 1}.")

            else:
                return await ctx.send(
                    f"Sorry, only up to 20 songs in the playlist, please wait for **{self.name_song}** to finish.")

        await self.play_song(ctx, song)


@buttons.click
async def skip_b(ctx):
    await ctx.reply(content="The current song has been stop.Next one will start shortly.",
                    flags=MessageFlags().EPHEMERAL)


@buttons.click
async def list_b(ctx):
    await ctx.reply(content="Current playlist.", flags=MessageFlags().EPHEMERAL)


@buttons.click
async def resume_b(ctx):
    await ctx.reply(content="I am resuming the song.", flags=MessageFlags().EPHEMERAL)


@buttons.click
async def pause_b(ctx):
    await ctx.reply(content="I am pausing current song.", flags=MessageFlags().EPHEMERAL)


@buttons.click
async def stop_b(ctx):
    await ctx.reply(content="See you around.", flags=MessageFlags().EPHEMERAL)


@commands.command()
async def play_buttons(ctx):
    await buttons.send(
        content=":tumbler_glass: Cheers!!!",
        channel=ctx.channel.id,
        components=[ActionRow([Button(style=ButtonType().Primary, label="Next Song", custom_id="skip_b"),
                               Button(style=ButtonType().Success, label="Playlist", custom_id="list_b"),
                               Button(style=ButtonType().Success, label="Pause", custom_id="pause_b"),
                               Button(style=ButtonType().Secondary, label="Resume", custom_id="resume_b"),
                               Button(style=ButtonType().Danger, label="Stop", custom_id="stop_b", )])])


async def setup():
    await client.wait_until_ready()
    client.add_cog(Player(client))


@client.event
async def on_message(message):
    ctx = await client.get_context(message)
    if message.content == "See you around.":
        try:
            del song_queue[ctx.guild.id][:]
        except IndexError:
            print("Empty List")
        if ctx.voice_client is not None:
            return await ctx.voice_client.disconnect()
    elif message.content == "The current song has been stop.Next one will start shortly.":
        ctx.voice_client.stop()
    elif message.content == "I am resuming the song.":
        if ctx.voice_client is None:
            return await ctx.send("I am not connected to a voice channel.")
        if not ctx.voice_client.is_paused():
            return await ctx.send("I am already playing a song.")
        ctx.voice_client.resume()
    elif message.content == "I am pausing current song.":
        if ctx.voice_client.is_paused():
            return await ctx.send("I am already paused.")
        ctx.voice_client.pause()
    elif message.content == "Current playlist.":
        if len(song_queue[ctx.guild.id]) == 0:
            return await ctx.send("There are currently no songs in the playlist.")
        embed = discord.Embed(title="Playlist", description="", colour=discord.Colour.dark_gold())
        for i, url in enumerate(song_queue[ctx.guild.id], 1):
            # song = pafy.new(url).title !!!!! that way is way slower to show the play list
            # embed.description += f"{i}. [{song}]({url})\n"
            url_song = url
            params = {"format": "json", "url": url_song}
            url_api = "https://www.youtube.com/oembed"
            query_string = urllib.parse.urlencode(params)
            name = url_api + "?" + query_string
            with urllib.request.urlopen(name) as response:
                response_text = response.read()
                data = json.loads(response_text.decode())
            embed.description += f"{i}. [{data['title']}]({url})\n"
        await ctx.send(embed=embed)

    await client.process_commands(message)


client.loop.create_task(setup())
client.run(TOKEN)
