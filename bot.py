import os
import discord
from discord.ext import commands
from discord.ui import View, Button

# Переменная окружения
TOKEN = os.environ.get("TOKEN")
if TOKEN is None:
    raise ValueError("Переменная окружения TOKEN не установлена!")

# Настройка интентов
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ID каналов (замени на свои)
LOBBY_CHANNEL_ID = 1399216005032706058
CONTROL_TEXT_CHANNEL_ID = 1406753514973298708
CATEGORY_ID = 1406757149803024434

# Словарь для отслеживания приватных каналов
private_channels = {}

# Кнопки панели управления
class ControlPanel(View):
    def __init__(self, member, channel):
        super().__init__(timeout=None)
        self.member = member
        self.channel = channel

        self.add_item(Button(label="Kick", style=discord.ButtonStyle.danger, custom_id="kick"))
        self.add_item(Button(label="Mute/Unmute", style=discord.ButtonStyle.secondary, custom_id="mute"))

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.danger, custom_id="kick")
    async def kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.member.voice:
            await self.member.move_to(None)
            await interaction.response.send_message(f"{self.member.display_name} кикнут из канала.", ephemeral=True)
        else:
            await interaction.response.send_message("Пользователь не в голосовом канале.", ephemeral=True)

    @discord.ui.button(label="Mute/Unmute", style=discord.ButtonStyle.secondary, custom_id="mute")
    async def mute(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.member.voice:
            muted = self.member.voice.mute
            await self.member.edit(mute=not muted)
            await interaction.response.send_message(
                f"{self.member.display_name} теперь {'заглушен' if not muted else 'разглушен'}.", ephemeral=True
            )
        else:
            await interaction.response.send_message("Пользователь не в голосовом канале.", ephemeral=True)

# Создание приватного канала
async def create_private_channel(member):
    guild = member.guild
    category = guild.get_channel(CATEGORY_ID)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member: discord.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True),
    }
    channel = await guild.create_voice_channel(f"{member.display_name}-lobby", overwrites=overwrites, category=category)
    private_channels[member.id] = channel

    # Панель управления
    control_channel = guild.get_channel(CONTROL_TEXT_CHANNEL_ID)
    view = ControlPanel(member, channel)
    await control_channel.send(f"Панель управления для {member.display_name}:", view=view)

# Удаление приватного канала, если он пустой
async def delete_private_channel(member):
    channel = private_channels.get(member.id)
    if channel and len(channel.members) == 0:
        await channel.delete()
        private_channels.pop(member.id, None)

# Событие входа/выхода из голосового канала
@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and after.channel.id == LOBBY_CHANNEL_ID:
        # Создать приватный канал
        await create_private_channel(member)
        # Вернуть пользователя в приватный канал
        private_channel = private_channels[member.id]
        await member.move_to(private_channel)

    if before.channel and before.channel.id in [ch.id for ch in private_channels.values()]:
        # Удалить пустой приватный канал
        await delete_private_channel(member)

@bot.event
async def on_ready():
    print(f"{bot.user} запущен ✅")

# Простейшая команда для теста
@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

bot.run(TOKEN)
