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
intents.members = True # Üye isimlerini değiştirmek ve takip etmek için bu intent şarttır!

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


# ==================== TICKET SİSTEMİ VIEW SINIFLARI ====================

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Talebi Kapat", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket_button")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Destek talebi kapatılıyor...", ephemeral=True)
        await interaction.channel.delete()


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="OPEN", style=discord.ButtonStyle.secondary, emoji="🎫", custom_id="open_ticket_button")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user

        existing_channel = discord.utils.get(guild.text_channels, name=f"ticket-{member.name.lower()}")
        if existing_channel:
            await interaction.response.send_message(f"Zaten açık bir destek talebiniz bulunuyor: {existing_channel.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{member.name}",
            overwrites=overwrites,
            topic=f"Destek talebi sahibi: {member.mention}"
        )

        await interaction.response.send_message(f"Destek talebiniz oluşturuldu: {ticket_channel.mention}", ephemeral=True)

        close_view = TicketCloseView()
        
        embed = discord.Embed(
            title="VNT SUPPORT",
            description="Destek talebiniz başarıyla açıldı. Lütfen yetkililerin sizinle ilgilenmesini bekleyin.",
            color=0x2b2d31
        )
        await ticket_channel.send(f"{member.mention} hoş geldin!", embed=embed, view=close_view)


@bot.event
async def on_ready():
    print(f"✅ {bot.user} aktif ve tüm sistemler yüklendi!")
    bot.add_view(TicketView())
    bot.add_view(TicketCloseView())


# ==================== WIPE GÖREV SEÇİM SİSTEMİ VIEW ====================

class WipeGorevView(discord.ui.View):
    def __init__(self, tarih_str="", saat_str="", duyuru_metni="", author_display=""):
        super().__init__(timeout=None)
        self.tarih_str = tarih_str
        self.saat_str = saat_str
        self.duyuru_metni = duyuru_metni
        self.author_display = author_display
        
        self.builder_users = []
        self.farmer_users = []
        self.roamer_users = []
        self.electric_users = []
        self.endustriyel_users = []

    def update_labels(self):
        self.builder_btn.label = f"Builder ({len(self.builder_users)}/2)"
        self.farmer_btn.label = f"Farmer ({len(self.farmer_users)})"
        self.roamer_btn.label = f"Roamer ({len(self.roamer_users)}/6)"
        self.electric_btn.label = f"Electric ({len(self.electric_users)}/1)"
        self.endustriyel_btn.label = f"Endüstriyel ({len(self.endustriyel_users)}/1)"

    def get_embed(self, guild_name):
        b_list = ", ".join([f"<@{uid}>" for uid in self.builder_users]) or "Seçen yok"
        f_list = ", ".join([f"<@{uid}>" for uid in self.farmer_users]) or "Seçen yok"
        r_list = ", ".join([f"<@{uid}>" for uid in self.roamer_users]) or "Seçen yok"
        e_list = ", ".join([f"<@{uid}>" for uid in self.electric_users]) or "Seçen yok"
        en_list = ", ".join([f"<@{uid}>" for uid in self.endustriyel_users]) or "Seçen yok"

        kanal_etiket = "<#1543368885569323098>"
        desc = (
            f"📢 **{guild_name} | Ekip Duyurusu**\n\n"
            f"📅 **Tarih:** {self.tarih_str} {self.saat_str}\n\n"
            f"🔹 **{guild_name} › {kanal_etiket}  {self.duyuru_metni}**\n\n"
            f"🛠️ **GÖREV DAĞILIMI:**\n"
            f"🧱 **Builder (Max 2):** {b_list}\n"
            f"⛏️ **Farmer (Sınırsız):** {f_list}\n"
            f"🔫 **Roamer (Max 6):** {r_list}\n"
            f"⚡ **Electric (Max 1):** {e_list}\n"
            f"⚙️ **Endüstriyel (Max 1):** {en_list}\n\n"
            f"@here"
        )
        embed = discord.Embed(description=desc, color=0x2b2d31)
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1541904408407711747/1546891550431383632/ds.png?ex=6aa16e85&is=6aa01d05&hm=6c35314200b13fc734a0bf41cfb48313f452620b546d28cc312d566e5af92952&")
        return embed

    def user_has_role(self, uid):
        return (uid in self.builder_users or 
                uid in self.farmer_users or 
                uid in self.roamer_users or 
                uid in self.electric_users or 
                uid in self.endustriyel_users)

    @discord.ui.button(label="Builder (0/2)", style=discord.ButtonStyle.primary, custom_id="gorev_builder")
    async def builder_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        uid = interaction.user.id
        if uid in self.builder_users:
            self.builder_users.remove(uid)
            await interaction.followup.send("❌ Builder görevinden ayrıldın.", ephemeral=True)
        else:
            if len(self.builder_users) >= 2:
                await interaction.followup.send("❌ Builder kadrosu dolu (Max 2 kişi)!", ephemeral=True)
                return
            if self.user_has_role(uid):
                await interaction.followup.send("❌ Zaten başka bir görev seçmişsin! Öncekini bırakmalısın.", ephemeral=True)
                return
            self.builder_users.append(uid)
            await interaction.followup.send("✅ Builder görevini seçtin!", ephemeral=True)
        
        self.update_labels()
        new_embed = self.get_embed(interaction.guild.name)
        await interaction.message.edit(embed=new_embed, view=self)

    @discord.ui.button(label="Farmer (0)", style=discord.ButtonStyle.success, custom_id="gorev_farmer")
    async def farmer_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        uid = interaction.user.id
        if uid in self.farmer_users:
            self.farmer_users.remove(uid)
            await interaction.followup.send("❌ Farmer görevinden ayrıldın.", ephemeral=True)
        else:
            if self.user_has_role(uid):
                await interaction.followup.send("❌ Zaten başka bir görev seçmişsin!", ephemeral=True)
                return
            self.farmer_users.append(uid)
            await interaction.followup.send("✅ Farmer görevini seçtin!", ephemeral=True)
        
        self.update_labels()
        new_embed = self.get_embed(interaction.guild.name)
        await interaction.message.edit(embed=new_embed, view=self)

    @discord.ui.button(label="Roamer (0/6)", style=discord.ButtonStyle.danger, custom_id="gorev_roamer")
    async def roamer_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        uid = interaction.user.id
        if uid in self.roamer_users:
            self.roamer_users.remove(uid)
            await interaction.followup.send("❌ Roamer görevinden ayrıldın.", ephemeral=True)
        else:
            if len(self.roamer_users) >= 6:
                await interaction.followup.send("❌ Roamer kadrosu dolu (Max 6 kişi)!", ephemeral=True)
                return
            if self.user_has_role(uid):
                await interaction.followup.send("❌ Zaten başka bir görev seçmişsin!", ephemeral=True)
                return
            self.roamer_users.append(uid)
            await interaction.followup.send("✅ Roamer görevini seçtin!", ephemeral=True)
        
        self.update_labels()
        new_embed = self.get_embed(interaction.guild.name)
        await interaction.message.edit(embed=new_embed, view=self)

    @discord.ui.button(label="Electric (0/1)", style=discord.ButtonStyle.secondary, custom_id="gorev_electric")
    async def electric_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        uid = interaction.user.id
        if uid in self.electric_users:
            self.electric_users.remove(uid)
            await interaction.followup.send("❌ Electric görevinden ayrıldın.", ephemeral=True)
        else:
            if len(self.electric_users) >= 1:
                await interaction.followup.send("❌ Electric kadrosu dolu (Max 1 kişi)!", ephemeral=True)
                return
            if self.user_has_role(uid):
                await interaction.followup.send("❌ Zaten başka bir görev seçmişsin!", ephemeral=True)
                return
            self.electric_users.append(uid)
            await interaction.followup.send("✅ Electric görevini seçtin!", ephemeral=True)
        
        self.update_labels()
        new_embed = self.get_embed(interaction.guild.name)
        await interaction.message.edit(embed=new_embed, view=self)

    @discord.ui.button(label="Endüstriyel (0/1)", style=discord.ButtonStyle.secondary, custom_id="gorev_endustriyel")
    async def endustriyel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        uid = interaction.user.id
        if uid in self.endustriyel_users:
            self.endustriyel_users.remove(uid)
            await interaction.followup.send("❌ Endüstriyel görevinden ayrıldın.", ephemeral=True)
        else:
            if len(self.endustriyel_users) >= 1:
                await interaction.followup.send("❌ Endüstriyel kadrosu dolu (Max 1 kişi)!", ephemeral=True)
                return
            if self.user_has_role(uid):
                await interaction.followup.send("❌ Zaten başka bir görev seçmişsin!", ephemeral=True)
                return
            self.endustriyel_users.append(uid)
            await interaction.followup.send("✅ Endüstriyel görevini seçtin!", ephemeral=True)
        
        self.update_labels()
        new_embed = self.get_embed(interaction.guild.name)
        await interaction.message.edit(embed=new_embed, view=self)


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
                except:
                    pass

                await message.channel.send(
                    f"⚠️ {message.author.mention}, spam yaptığın için 1 dakika susturuldun!", 
                    delete_after=10
                )
            except:
                pass

    await bot.process_commands(message)


# ==================== KORUMA, OTO ROL & VNT TAG SİSTEMİ ====================

@bot.event
async def on_member_join(member):
    if member.bot:
        return

    otomatik_rol = discord.utils.get(member.guild.roles, name="VNT pub")
    if otomatik_rol:
        try:
            await member.add_roles(otomatik_rol, reason="Yeni Üye Otomatik Rol")
        except:
            pass

    if not member.guild_permissions.administrator:
        try:
            yeni_isim = f"VNT {member.display_name}"
            if len(yeni_isim) <= 32:  
                await member.edit(nick=yeni_isim, reason="Oto VNT Tag Sistemi")
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


# ==================== YÖNETİM & TICKET KOMUTLARI ====================

@bot.command(name="VNTAG", aliases=["vnttag"])
@commands.has_permissions(administrator=True)
async def vnttag_komutu(ctx):
    await ctx.send("⏳ Mevcut üyelerin isimleri güncelleniyor, lütfen bekleyin...")
    sayac = 0
    
    for member in ctx.guild.members:
        if member.bot or member.guild_permissions.administrator:
            continue
        
        if not member.display_name.startswith("VNT "):
            try:
                yeni_isim = f"VNT {member.display_name}"
                if len(yeni_isim) <= 32:
                    await member.edit(nick=yeni_isim, reason="Toplu VNT Tag Dağıtımı")
                    sayac += 1
                    await asyncio.sleep(0.5) 
            except:
                pass
                
    await ctx.send(f"✅ İşlem tamamlandı! Toplam **{sayac}** kişinin ismine VNT eklendi.")


@bot.command(name="TICKETKUR", aliases=["ticketkur"])
@commands.has_permissions(administrator=True)
async def ticketkur_komutu(ctx):
    embed = discord.Embed(
        title="VNT SUPPORT !",
        description="you need help? OPEN TICKET",
        color=0x111111
    )
    embed.set_image(url="https://cdn.discordapp.com/attachments/1541904408407711747/1543372318363885678/ChatGPT_Image_30_Agu_2026_00_30_00.png?ex=6a9549bb&is=6a93f83b&hm=a9075766b9f0ff4b1a17a75f165087f2273690037efe6ab44a7ee65e02828406&")
    embed.set_footer(text="VNT TICKET SYSTEM")

    view = TicketView()
    await ctx.send(embed=embed, view=view)
    try:
        await ctx.message.delete()
    except:
        pass


# ==================== DUYURU & GÖREV SİSTEMİ ====================

@bot.command(name="DMGÖNDER", aliases=["dmgonder", "dm"])
@commands.has_permissions(administrator=True)
async def dmgonder_komutu(ctx, *, duyuru_metni: str = "MAZARETLİ KABUL EDİLMİYECEKTİR TIKLE"):
    """
    Kullanım: !dmgonder Verilecek Duyuru Metni
    """
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    await ctx.send("📅 Lütfen duyuru için **Tarih** bilgisini girin (Örn: `7 Eylül 2026 Pazartesi`):")
    try:
        tarih_msg = await bot.wait_for('message', timeout=60.0, check=check)
        tarih_str = tarih_msg.content
    except asyncio.TimeoutError:
        await ctx.send("❌ Süre bitti, işlem iptal edildi.")
        return

    await ctx.send("⏰ Lütfen duyuru için **Saat** bilgisini girin (Örn: `18:02`):")
    try:
        saat_msg = await bot.wait_for('message', timeout=60.0, check=check)
        saat_str = saat_msg.content
    except asyncio.TimeoutError:
        await ctx.send("❌ Süre bitti, işlem iptal edildi.")
        return

    hedef_kanal_id = 1546896143861153882
    kanal = ctx.guild.get_channel(hedef_kanal_id)

    if not kanal:
        await ctx.send(f"❌ Belirtilen ID (`{hedef_kanal_id}`) ile kanal bulunamadı!")
        return

    # 1. WIPE kanalına sadece butonlu ve görev dağılımlı embed gönderilir
    view = WipeGorevView(tarih_str=tarih_str, saat_str=saat_str, duyuru_metni=duyuru_metni, author_display=ctx.author.display_name)
    embed = view.get_embed(ctx.guild.name)
    await kanal.send(embed=embed, view=view)

    # 2. Yetkiliye DM üzerinden istediğin görseldeki formatta mesaj gönderilir
    try:
        dm_embed = discord.Embed(color=0x2b2d31)
        dm_embed.set_author(name="VNT community | Ekip Duyurusu")
        dm_embed.add_field(name="Gönderen", value=f"{ctx.author.mention} (`{ctx.author.id}`)", inline=False)
        dm_embed.add_field(name="Tarih", value=f"{tarih_str} {saat_str}", inline=False)
        dm_embed.add_field(name="Duyuru", value=f"VNT community › <#1543368885569323098> | **{duyuru_metni}**\n\n@here", inline=False)
        dm_embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1541904408407711747/1546891550431383632/ds.png?ex=6aa16e85&is=6aa01d05&hm=6c35314200b13fc734a0bf41cfb48313f452620b546d28cc312d566e5af92952&")
        dm_embed.set_footer(text="! VNT • Duyuru")
        
        await ctx.author.send(embed=dm_embed)
    except:
        await ctx.send("⚠️ Duyuru kanala atıldı ancak size DM gönderilemedi (DM'leriniz kapalı olabilir).")

    await ctx.send(f"✅ Duyuru <#{hedef_kanal_id}> kanalına atıldı ve DM bilgisi gönderildi!")


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
        await ctx.reply("❌ Botun bir ses kanalında olması gerekiyor.")


bot.run(TOKEN)