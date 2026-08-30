import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os

# ---------- BOT AYARLARI ----------
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "!"

# FFmpeg yolunuzu ayarlayın
FFMPEG_PATH = r"C:\ffmpeg\bin\ffmpeg.exe"

# Intent Ayarları
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# Spam Kontrolü İçin Kullanıcı Takip Deposu
user_spam_counter = {}

# ---------- YTDL & FFMPEG AYARLARI ----------
YTDL_OPTIONS = {
    'format': 'best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'cookiefile': 'cookies.txt',  
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web']
        }
    },
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        
        search_query = url
        if "spotify.com" in url:
            search_query = f"ytsearch:{url}"

        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search_query, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, executable=FFMPEG_PATH, **FFMPEG_OPTIONS), data=data)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} aktif ve tüm sistemler yüklendi!")


# ==================== SPAM KORUMASI ====================

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return

    user_id = message.author.id
    current_time = asyncio.get_event_loop().time()
    content = message.content.strip().lower()

    if content:
        if user_id in user_spam_counter:
            data = user_spam_counter[user_id]
            time_diff = current_time - data["last_time"]

            if time_diff <= 5.0 and data["last_msg"] == content:
                data["count"] += 1
                data["last_time"] = current_time
            else:
                user_spam_counter[user_id] = {"last_msg": content, "count": 1, "last_time": current_time}
        else:
            user_spam_counter[user_id] = {"last_msg": content, "count": 1, "last_time": current_time}

        if user_spam_counter[user_id]["count"] >= 3:
            try:
                duration = discord.utils.utcnow() + discord.utils.datetime.timedelta(seconds=60)
                await message.author.timeout(duration, reason="Spam koruması")
                user_spam_counter[user_id] = {"last_msg": "", "count": 0, "last_time": 0}

                def is_spam_author(m):
                    return m.author.id == user_id

                try:
                    deleted = await message.channel.purge(limit=20, check=is_spam_author)
                    deleted_count = len(deleted)
                except:
                    deleted_count = 0

                await message.channel.send(
                    f"⚠️ {message.author.mention}, spam yaptığın için 1 dakika susturuldun!", 
                    delete_after=10
                )
            except:
                pass

    await bot.process_commands(message)


# ==================== KORUMA SİSTEMİ & OTO ROL ====================

@bot.event
async def on_member_join(member):
    if member.bot and member != bot.user:
        try:
            await member.kick(reason="Anti-Bot Koruması")
        except:
            pass
        return

    otomatik_rol = discord.utils.get(member.guild.roles, name="VNT pub")
    if otomatik_rol:
        try:
            await member.add_roles(otomatik_rol, reason="Yeni Üye Otomatik Rol")
        except:
            pass


@bot.event
async def on_voice_state_update(member, before, after):
    if not member.bot and after.channel is not None:
        if after.channel.name == "discord.gg/VNT":
            try:
                await member.move_to(None)
            except:
                pass


# ---------- GELLA KOMUTU ----------
@bot.command(name="GELLA", aliases=["gella"])
async def gella_komutu(ctx):
    if not ctx.author.guild_permissions.administrator:
        return

    kanal_adi = "discord.gg/VNT"
    hedef_kanal = discord.utils.get(ctx.guild.voice_channels, name=kanal_adi)

    if not hedef_kanal:
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(connect=True, speak=False),
            ctx.guild.me: discord.PermissionOverwrite(connect=True, speak=True, move_members=True)
        }
        hedef_kanal = await ctx.guild.create_voice_channel(name=kanal_adi, position=0, overwrites=overwrites)

    if ctx.voice_client is None:
        await hedef_kanal.connect()
    else:
        await ctx.voice_client.move_to(hedef_kanal)


# ==================== YÖNETİM KOMUTLARI ====================

@bot.command(name="CLEAR", aliases=["clear", "sil", "clean"])
async def clear_komutu(ctx):
    if not (ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.manage_messages):
        return
    try:
        deleted = await ctx.channel.purge(limit=10)
        await ctx.send(f"🧹 {len(deleted)} mesaj silindi.", delete_after=5)
    except:
        pass


@bot.command(name="ÇEK", aliases=["cek", "pull"])
async def cek(ctx):
    if not ctx.author.voice or not ctx.author.guild_permissions.move_members:
        return
    hedef = ctx.author.voice.channel
    for ses_kanali in ctx.guild.voice_channels:
        if ses_kanali == hedef:
            continue
        for uye in ses_kanali.members:
            if not uye.bot:
                try:
                    await uye.move_to(hedef)
                except:
                    pass


@bot.command(name="MUTE", aliases=["mute", "sustur"])
async def mute_komutu(ctx):
    if not ctx.author.voice or not ctx.author.guild_permissions.mute_members:
        return
    for uye in ctx.author.voice.channel.members:
        if not uye.bot and uye != ctx.author:
            try:
                await uye.edit(mute=True)
            except:
                pass


@bot.command(name="UNMUTE", aliases=["unmute", "konustur"])
async def unmute_komutu(ctx):
    if not ctx.author.voice or not ctx.author.guild_permissions.mute_members:
        return
    for uye in ctx.author.voice.channel.members:
        if not uye.bot:
            try:
                await uye.edit(mute=False)
            except:
                pass


# ==================== MÜZİK KOMUTLARI ====================

@bot.command(name="PLAY", aliases=["play", "oynat", "p"])
async def play(ctx, *, search: str):
    """YouTube veya Spotify linkini/ismini aratıp ses kanalında çalar."""
    if not ctx.author.voice:
        await ctx.reply("❌ Önce bir ses kanalına katılmalısın! 🔊", delete_after=5)
        return

    channel = ctx.author.voice.channel

    if ctx.voice_client is None:
        await channel.connect()
    elif ctx.voice_client.channel != channel:
        await ctx.voice_client.move_to(channel)

    async with ctx.typing():
        try:
            player = await YTDLSource.from_url(search, loop=bot.loop, stream=True)
            
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()

            ctx.voice_client.play(player, after=lambda e: print(f'Hata: {e}') if e else None)
            
            embed = discord.Embed(
                title="🎵 Müzik Çalınıyor",
                description=f"**[{player.title}]({player.url})**",
                color=0x1DB954
            )
            embed.set_footer(text=f"İsteyen: {ctx.author.display_name}")
            await ctx.reply(embed=embed)

        except Exception as e:
            await ctx.reply(f"❌ Şarkı oynatılırken bir hata oluştu: `{str(e)}`")


@bot.command(name="STOP", aliases=["stop", "dur", "dc", "leave"])
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.reply("⏹️ Müzik durduruldu.")
    else:
        await ctx.reply("❌ Bot zaten bir ses kanalında değil.")


bot.run(TOKEN)