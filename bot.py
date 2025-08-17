import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import os

# ===== Настройка интентов =====
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== Настройка каналов =====
LOBBY_CHANNEL_ID = 1399216005032706058       # Главный голосовой канал
CATEGORY_ID = 1406757149803024434           # Категория для приватных каналов
CONTROL_TEXT_CHANNEL_ID = 1406753514973298708  # Текстовый канал панели управления

private_channels = {}
panel_message = None  # Сообщение панели для автообновления

# ===== Панель с селект-меню =====
class ScrollingControlPanel(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.selected_member_id = None
        self.update_menu()

    def update_menu(self):
        self.clear_items()
        options = []
        for member_id, channel_id in private_channels.items():
            member = bot.get_user(member_id)
            channel = bot.get_channel(channel_id)
            if member and channel:
                options.append(discord.SelectOption(label=f"{member.display_name} ({channel.name})", value=str(member_id)))
        if options:
            select = Select(placeholder="Выберите участника", options=options)
            select.callback = self.select_callback
            self.add_item(select)

        # Кнопки действий
        self.add_item(Button(label="Кикнуть", style=discord.ButtonStyle.danger, custom_id="kick"))
        self.add_item(Button(label="Мьют", style=discord.ButtonStyle.secondary, custom_id="mute"))
        self.add_item(Button(label="Удалить канал", style=discord.ButtonStyle.danger, custom_id="delete"))

    async def select_callback(self, interaction: discord.Interaction):
        self.selected_member_id = int(interaction.data['values'][0])
        await interaction.response.send_message(f"Выбран участник для управления ✅", ephemeral=True)

# ===== Функция обновления панели =====
async def update_panel():
    global panel_message
    channel = bot.get_channel(CONTROL_TEXT_CHANNEL_ID)
    if not channel:
        return
    view = ScrollingControlPanel()
    try:
        if panel_message:
            await panel_message.edit(content="Панель управления лобби:", view=view)
        else:
            panel_message = await channel.send("Панель управления лобби:", view=view)
    except discord.NotFound:
        panel_message = await channel.send("Панель управления лобби:", view=view)

# ===== Обработчик кнопок =====
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if not interaction.type == discord.InteractionType.component:
        return

    view = interaction.message.components[0].children[0].view if interaction.message.components else None
    if not isinstance(view, ScrollingControlPanel):
        return

    member_id = view.selected_member_id
    if not member_id:
        await interaction.response.send_message("Выберите участника сначала ❌", ephemeral=True)
        return

    member = bot.get_user(member_id)
    channel_id = private_channels.get(member_id)
    channel = bot.get_channel(channel_id) if channel_id else None

    custom_id = interaction.data.get('custom_id')
    if custom_id == "kick":
        if member and member.voice and member.voice.channel:
            await member.move_to(None)
            await interaction.response.send_message(f"{member.display_name} кикнут ✅", ephemeral=True)
        else:
            await interaction.response.send_message("Невозможно кикнуть ❌", ephemeral=True)
    elif custom_id == "mute":
        if member and member.voice and member.voice.channel:
            await member.edit(mute=True)
            await interaction.response.send_message(f"{member.display_name} замучен ✅", ephemeral=True)
        else:
            await interaction.response.send_message("Невозможно замутить ❌", ephemeral=True)
    elif custom_id == "delete":
        if channel:
            await channel.delete()
            del private_channels[member_id]
            await interaction.response.send_message(f"Приватный канал {channel.name} удалён ✅", ephemeral=True)
            await update_panel()
        else:
            await interaction.response.send_message("Канал не найден ❌", ephemeral=True)

# ===== Событие изменения голоса =====
@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and after.channel.id == LOBBY_CHANNEL_ID:
        category = bot.get_channel(CATEGORY_ID)
        if not category:
            return
        overwrites = {
            member.guild.default_role: discord.PermissionOverwrite(connect=False),
            member: discord.PermissionOverwrite(connect=True, manage_channels=True, mute_members=True)
        }
        private_channel = await member.guild.create_voice_channel(
            name=f"{member.display_name}'s channel",
            category=category,
            overwrites=overwrites
        )
        await member.move_to(private_channel)
        private_channels[member.id] = private_channel.id
        await update_panel()

    if before.channel and before.channel.id in private_channels.values():
        channel_id = before.channel.id
        channel = bot.get_channel(channel_id)
        if channel and len(channel.members) == 0:
            await channel.delete()
            for key, val in list(private_channels.items()):
                if val == channel_id:
                    del private_channels[key]
                    break
            await update_panel()

# ===== Команда для ручного вызова панели =====
@bot.command(name="panel")
async def panel(ctx):
    if ctx.channel.id != CONTROL_TEXT_CHANNEL_ID:
        await ctx.send("Эта команда доступна только в панели управления ❌")
        return
    await update_panel()

# ===== Старт бота =====
@bot.event
async def on_ready():
    print(f"Бот {bot.user} запущен ✅")
    await update_panel()

# ===== Запуск бота =====
bot.run(os.getenv("TOKEN"))  # <-- Токен берется из переменной окружения Railway
