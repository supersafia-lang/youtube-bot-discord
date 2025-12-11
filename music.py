import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)
cookies = os.getenv('YOUTUBE_COOKIES')
if cookies:
    with open('cookies.txt', 'w', encoding='utf-8') as f:
        f.write(cookies)
# yt-dlp options (stream best audio only, no download)
ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'cookiefile': 'cookies.txt',  # this line is new
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',  # no video
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

        if 'entries' in data:
            # Take first item if it's a playlist
            data = data['entries'][0]

        filename = data['url']
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

@bot.event
async def on_ready():
    print(f'{bot.user} is online and ready!')

@bot.command(name='join')
async def join(ctx):
    """Join the voice channel you're in."""
    if ctx.author.voice is None:
        return await ctx.send("You need to be in a voice channel first!")
    voice_channel = ctx.author.voice.channel
    await voice_channel.connect()
    await ctx.send(f"Joined {voice_channel.name}")

@bot.command(name='leave')
async def leave(ctx):
    """Leave the voice channel."""
    if ctx.voice_client is None:
        return await ctx.send("I'm not in a voice channel!")
    await ctx.voice_client.disconnect()
    await ctx.send("Left the voice channel")

@bot.command(name='play')
async def play(ctx, url: str):
    """Play a YouTube video's audio from the given URL."""
    if ctx.author.voice is None:
        return await ctx.send("You need to be in a voice channel first!")
    
    voice_channel = ctx.author.voice.channel

    # Connect if not already connected
    if ctx.voice_client is None:
        await voice_channel.connect()
    elif ctx.voice_client.channel != voice_channel:
        await ctx.voice_client.move_to(voice_channel)

    # Stop anything currently playing
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()

    await ctx.send(f"Searching for {url}...")

    try:
        player = await YTDLSource.from_url(url, loop=bot.loop)
        ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)
        await ctx.send(f"Now playing: **{player.title}**")
    except Exception as e:
        await ctx.send(f"Something went wrong: {e}")

@bot.command(name='stop')
async def stop(ctx):
    """Stop playing audio."""
    if ctx.voice_client is None:
        return await ctx.send("I'm not playing anything!")
    ctx.voice_client.stop()
    await ctx.send("Stopped playing")


bot.run(os.getenv('DISCORD_TOKEN'))
