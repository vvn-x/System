import os
import random
import discord
from discord.ext import commands

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
ALLOWED_CHANNEL_IDS = {int(cid.strip()) for cid in os.environ.get("ALLOWED_CHANNEL_IDS", "").split(",") if cid.strip()}
TEXT_DELETE_CHANNEL_IDS = {int(cid.strip()) for cid in os.environ.get("TEXT_DELETE_CHANNEL_IDS", "").split(",") if cid.strip()}
GIFS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gifs")

# ===== إعدادات نظام الاقتراحات =====
SUGGESTIONS_CHANNEL_ID = 1281895871897800808  # ID قناة الاقتراحات
EMBED_COLOR = 0xB6392D  # لون الإيمبد

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


def get_random_gif_path():
    if not os.path.isdir(GIFS_DIR):
        return None
    files = [f for f in os.listdir(GIFS_DIR) if f.lower().endswith((".gif", ".png", ".jpg", ".jpeg", ".webp"))]
    if not files:
        return None
    chosen = random.choice(files)
    return os.path.join(GIFS_DIR, chosen)


async def handle_suggestion(message: discord.Message):
    """يحول رسالة المستخدم بقناة الاقتراحات إلى إيمبد مرتب مع تفاعلات تصويت."""
    content = message.content.strip()

    # البحث عن أول صورة مرفقة بالرسالة
    image_url = None
    for attachment in message.attachments:
        if attachment.content_type and attachment.content_type.startswith("image/"):
            image_url = attachment.url
            break

    # لو الرسالة فاضية تماماً (لا نص ولا صورة) نتجاهلها
    if not content and not image_url:
        return

    embed = discord.Embed(
        description=content if content else None,
        color=EMBED_COLOR,
        timestamp=message.created_at,
    )
    embed.set_author(
        name=message.author.display_name,
        icon_url=message.author.display_avatar.url,
    )
    embed.set_footer(text=f"User ID: {message.author.id}")

    if image_url:
        embed.set_image(url=image_url)

    sent_message = await message.channel.send(embed=embed)
    await sent_message.add_reaction("👍")
    await sent_message.add_reaction("👎")

    try:
        await message.delete()
    except discord.Forbidden:
        print("❌ ما عندي صلاحية Manage Messages لمسح رسالة الاقتراح الأصلية.")


@bot.event
async def on_ready():
    print(f"✅ البوت اشتغل باسم: {bot.user} (ID: {bot.user.id})")
    print(f"📺 الشاتات المسموحة: {ALLOWED_CHANNEL_IDS or 'كل الشاتات (ما تحدد شي)'}")
    print(f"🗑️ الشاتات الي بتمسح فيها الرسائل النصية: {TEXT_DELETE_CHANNEL_IDS or 'ولا شات'}")
    print(f"📝 قناة الاقتراحات: {SUGGESTIONS_CHANNEL_ID}")
    gif_count = len(os.listdir(GIFS_DIR)) if os.path.isdir(GIFS_DIR) else 0
    print(f"🖼️ عدد ملفات الـ GIF الموجودة بمجلد gifs: {gif_count}")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # ===== نظام الاقتراحات: له أولوية وقناته الخاصة =====
    if message.channel.id == SUGGESTIONS_CHANNEL_ID:
        await handle_suggestion(message)
        await bot.process_commands(message)
        return

    if message.channel.id in TEXT_DELETE_CHANNEL_IDS and not message.attachments and not message.embeds and not message.stickers:
        try:
            await message.delete()
        except discord.Forbidden:
            print("❌ ما عندي صلاحية Manage Messages لمسح الرسالة النصية.")
        except discord.HTTPException:
            pass
        return

    if ALLOWED_CHANNEL_IDS and message.channel.id not in ALLOWED_CHANNEL_IDS:
        return

    gif_path = get_random_gif_path()
    if gif_path is None:
        print("⚠️ ما في ولا ملف GIF جوا مجلد gifs — تأكد إنك رفعته صح.")
    else:
        await message.channel.send(file=discord.File(gif_path))

    await bot.process_commands(message)


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id:
        return

    if ALLOWED_CHANNEL_IDS and payload.channel_id not in ALLOWED_CHANNEL_IDS:
        return

    channel = bot.get_channel(payload.channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(payload.channel_id)
        except discord.HTTPException:
            return

    try:
        message = await channel.fetch_message(payload.message_id)
    except discord.HTTPException:
        return

    if message.author.id != bot.user.id:
        return

    member = payload.member
    if member is None and channel.guild is not None:
        try:
            member = await channel.guild.fetch_member(payload.user_id)
        except discord.HTTPException:
            member = None

    if member is not None and member.bot:
        try:
            await message.remove_reaction(payload.emoji, member)
            print(f"🧹 مسحت ريأكشن حطه البوت {member} عن رسالة بعتها بوتنا.")
        except discord.Forbidden:
            print("❌ ما عندي صلاحية Manage Messages لمسح الريأكشن.")
        except discord.HTTPException:
            pass


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise SystemExit("❌ لازم تحط DISCORD_TOKEN في متغيرات البيئة (Environment Variables).")
    bot.run(DISCORD_TOKEN)
