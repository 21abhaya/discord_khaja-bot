import os
import logging
import discord
import asyncio
import datetime

from discord.ext import commands
from dotenv import load_dotenv

from whatsapp import generate_whatsapp_link

load_dotenv()

token = os.getenv('DISCORD_TOKEN')

# ---------------------------------------------------------------------------
# LOGGER SETUP
# ---------------------------------------------------------------------------

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logger = logging.getLogger("khaja_bot")
logger.setLevel(logging.INFO)

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))

_file_handler = logging.FileHandler("khaja_bot.log", mode="a", encoding="utf-8")
_file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))

logger.addHandler(_console_handler)
logger.addHandler(_file_handler)

# ---------------------------------------------------------------------------
# BOT SETUP
# ---------------------------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)
bot.is_poll_active = False

# ---------------------------------------------------------------------------
# MENU DEFINITION
# ---------------------------------------------------------------------------

ADDONS = ["Momo ko Achaar", "Tomato Ketchup", "Salt", "2 Boiled Eggs"]

# Full pool of all items with variants (used to build "Others" per day)
ALL_ITEMS = {
    "Fried Rice": ["Full", "Half", "Egg Full", "Egg Half"],
    "Anda-Chiura": ["Full", "Half"],
    "Momo": [
        "Veg Steam", "Veg Fried",
        "Chicken Steam", "Chicken Fried",
        "Buff Steam", "Buff Fried",
    ],
    "Chowmein": [
        "Chicken Full", "Chicken Half",
        "Chicken-Egg Full Mix", "Chicken-Egg Half Mix",
        "Veg Full", "Veg Half",
        "Egg Full", "Egg Half",
        "Buff Full", "Buff Half",
    ],
    "Boiled Eggs": [],   # special — triggers modal for count
    "Dahi Chiura": [],
    "Dahi": [],
    "Syabhale": [],      # special — triggers modal for count
    "Chana": [],
    "Chicken Sausage": [],  # special — triggers modal for count
    "Buff Sausage": [],     # special — triggers modal for count
    "Pangra-Chiura": [],
}

# Fixed item per weekday (0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri)
FIXED_ITEM_BY_DAY = {
    0: "Fried Rice",
    1: "Anda-Chiura",
    2: "Momo",
    3: "Chowmein",
    4: "Momo",
}

def get_fixed_item(weekday: int):
    """Return the fixed item name for today, or None on weekends."""
    return FIXED_ITEM_BY_DAY.get(weekday)

def build_fixed_options(item_name: str) -> list[discord.SelectOption]:
    variants = ALL_ITEMS.get(item_name, [])
    if variants:
        return [discord.SelectOption(label=f"{v} {item_name}", value=f"{v} {item_name}") for v in variants]
    return [discord.SelectOption(label=item_name, value=item_name)]

def build_others_options(fixed_item_name: str | None) -> list[discord.SelectOption]:
    options = []
    for item, variants in ALL_ITEMS.items():
        if item == fixed_item_name:
            continue
        if variants:
            for v in variants:
                options.append(discord.SelectOption(label=f"{v} {item}", value=f"{v} {item}"))
        else:
            options.append(discord.SelectOption(label=item, value=item))
    return options[:25]

def build_addon_options() -> list[discord.SelectOption]:
    return [discord.SelectOption(label=a, value=a) for a in ADDONS]

# ---------------------------------------------------------------------------
# MODAL — Boiled Eggs count
# ---------------------------------------------------------------------------

class ModalForBoiledEggs(discord.ui.Modal, title="arey o kaaliya, kitne andey khaoge?"):

    def __init__(self, view: "KhajaTimeView"):
        super().__init__()
        self.khaja_view = view

    egg_count = discord.ui.TextInput(
        label="Number of eggs",
        placeholder="e.g. 2",
        min_length=1,
        max_length=2,
    )

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.egg_count.value.strip()
        if not raw.isdigit() or int(raw) < 1:
            await interaction.response.send_message(
                "Please enter a valid number of eggs (e.g. 1, 2, 3).", ephemeral=True
            )
            return

        count = int(raw)
        label = f"{count} Boiled Eggs"

        if interaction.user.id not in self.khaja_view.votes:
            self.khaja_view.votes[interaction.user.id] = {}

        self.khaja_view.votes[interaction.user.id]["others"] = label
        logger.info(f"{interaction.user.name} selected others: {label}")
        await interaction.response.edit_message(
            embed=self.khaja_view.create_embed(), view=self.khaja_view
        )
        await interaction.followup.send("✅ Order placed!", ephemeral=True)


# ---------------------------------------------------------------------------
# MODAL — Syabhale count
# ---------------------------------------------------------------------------

class ModalForSyabhale(discord.ui.Modal, title="Kati ota Syabhale havs hanne ta saathi?"):

    def __init__(self, view: "KhajaTimeView"):
        super().__init__()
        self.khaja_view = view

    syabhale_count = discord.ui.TextInput(
        label="Number of Syabhale",
        placeholder="e.g. 2",
        min_length=1,
        max_length=2,
    )

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.syabhale_count.value.strip()
        if not raw.isdigit() or int(raw) < 1:
            await interaction.response.send_message(
                "Please enter a valid number (e.g. 1, 2, 3).", ephemeral=True
            )
            return

        count = int(raw)
        label = f"{count} Syabhale"

        if interaction.user.id not in self.khaja_view.votes:
            self.khaja_view.votes[interaction.user.id] = {}

        self.khaja_view.votes[interaction.user.id]["others"] = label
        logger.info(f"{interaction.user.name} selected others: {label}")
        await interaction.response.edit_message(
            embed=self.khaja_view.create_embed(), view=self.khaja_view
        )
        await interaction.followup.send("✅ Order placed!", ephemeral=True)


# ---------------------------------------------------------------------------
# MODAL — Sausage count (Chicken & Buff)
# ---------------------------------------------------------------------------

class ModalForSausages(discord.ui.Modal, title="arey o kaalia, kitne saussages khaoge?"):

    def __init__(self, view: "KhajaTimeView", item_name: str):
        super().__init__()
        self.khaja_view = view
        self.item_name = item_name

    sausage_count = discord.ui.TextInput(
        label="Number of Sausages",
        placeholder="e.g. 2",
        min_length=1,
        max_length=2,
    )

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.sausage_count.value.strip()
        if not raw.isdigit() or int(raw) < 1:
            await interaction.response.send_message(
                "Please enter a valid number (e.g. 1, 2, 3).", ephemeral=True
            )
            return

        count = int(raw)
        label = f"{count} {self.item_name}"

        if interaction.user.id not in self.khaja_view.votes:
            self.khaja_view.votes[interaction.user.id] = {}

        self.khaja_view.votes[interaction.user.id]["others"] = label
        logger.info(f"{interaction.user.name} selected others: {label}")
        await interaction.response.edit_message(
            embed=self.khaja_view.create_embed(), view=self.khaja_view
        )
        await interaction.followup.send("✅ Order placed!", ephemeral=True)


# ---------------------------------------------------------------------------
# SELECT MENUS
# ---------------------------------------------------------------------------

class FixedItemSelect(discord.ui.Select):
    def __init__(self, fixed_item: str):
        options = build_fixed_options(fixed_item)
        super().__init__(
            placeholder=f"Today's special: {fixed_item}",
            min_values=0,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        view: KhajaTimeView = self.view
        if interaction.user.id not in view.votes:
            view.votes[interaction.user.id] = {}

        chosen = self.values[0] if self.values else None
        view.votes[interaction.user.id]["fixed"] = chosen
        logger.info(f"{interaction.user.name} selected fixed: {chosen}")
        await interaction.response.edit_message(embed=view.create_embed(), view=view)
        await interaction.followup.send("✅ Order placed!", ephemeral=True)


class OthersSelect(discord.ui.Select):
    def __init__(self, fixed_item: str | None):
        options = build_others_options(fixed_item)
        super().__init__(
            placeholder="Others — pick something else",
            min_values=0,
            max_values=1,
            options=options,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        view: KhajaTimeView = self.view
        if interaction.user.id not in view.votes:
            view.votes[interaction.user.id] = {}

        chosen = self.values[0] if self.values else None

        # Boiled Eggs and Syabhale trigger a modal for count
        if chosen == "Boiled Eggs":
            await interaction.response.send_modal(ModalForBoiledEggs(view))
            return
        if chosen == "Syabhale":
            await interaction.response.send_modal(ModalForSyabhale(view))
            return
        if chosen in ("Chicken Sausage", "Buff Sausage"):
            await interaction.response.send_modal(ModalForSausages(view, chosen))
            return

        view.votes[interaction.user.id]["others"] = chosen
        logger.info(f"{interaction.user.name} selected others: {chosen}")
        await interaction.response.edit_message(embed=view.create_embed(), view=view)
        await interaction.followup.send("✅ Order placed!", ephemeral=True)


class AddonsSelect(discord.ui.Select):
    def __init__(self):
        options = build_addon_options()
        super().__init__(
            placeholder="Add-ons (optional, pick any)",
            min_values=0,
            max_values=len(ADDONS),
            options=options,
            row=2,
        )

    async def callback(self, interaction: discord.Interaction):
        view: KhajaTimeView = self.view
        if interaction.user.id not in view.votes:
            view.votes[interaction.user.id] = {}

        view.votes[interaction.user.id]["addons"] = self.values
        logger.info(f"{interaction.user.name} selected addons: {list(self.values)}")
        await interaction.response.edit_message(embed=view.create_embed(), view=view)
        await interaction.followup.send("✅ Add-ons updated!", ephemeral=True)


# ---------------------------------------------------------------------------
# WHATSAPP VIEW
# ---------------------------------------------------------------------------

class WhatsappView(discord.ui.View):
    def __init__(self, url):
        super().__init__()
        self.add_item(discord.ui.Button(label="Whatsapp it", url=url))


# ---------------------------------------------------------------------------
# MAIN VIEW
# ---------------------------------------------------------------------------

class KhajaTimeView(discord.ui.View):

    def __init__(self, initiator, channel_members, weekday: int):
        super().__init__(timeout=900)
        self.initiator = initiator
        self.channel_members = channel_members
        self.message = None
        self.votes = {}  # user_id -> {"fixed": str|None, "others": str|None, "addons": list, "not_today": bool}
        self.weekday = weekday

        fixed_item = get_fixed_item(weekday)
        self.fixed_item = fixed_item

        if fixed_item:
            self.add_item(FixedItemSelect(fixed_item))
        self.add_item(OthersSelect(fixed_item))
        self.add_item(AddonsSelect())

    # -- Not Today button ----------------------------------------------------

    @discord.ui.button(label="Not Today", style=discord.ButtonStyle.danger, row=3)
    async def not_today_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.votes[interaction.user.id] = {"not_today": True, "fixed": None, "others": None, "addons": []}
        logger.info(f"{interaction.user.name} — Not Today")
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
        await interaction.followup.send("👍 Got it, not joining today!", ephemeral=True)

    # -- Embed ---------------------------------------------------------------

    def create_embed(self):
        now = int(datetime.datetime.now().timestamp())
        day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][self.weekday]

        embed = discord.Embed(
            title=f"🍽️ {day_name} <t:{now}:D>",
            color=discord.Color.blue(),
        )

        if self.fixed_item:
            variants = ALL_ITEMS.get(self.fixed_item, [])
            variant_str = ", ".join(variants) if variants else self.fixed_item
            embed.add_field(
                name=f"⭐ Today's Special: {self.fixed_item}",
                value=variant_str,
                inline=False,
            )

        # Live vote counts
        total = 0
        not_today_count = 0

        for uid, vote in self.votes.items():
            if vote.get("not_today"):
                not_today_count += 1
                continue
            if not (vote.get("fixed") or vote.get("others")):
                continue
            total += 1

        embed.add_field(name="✅ Ordered", value=str(total), inline=True)
        embed.add_field(name="🙅 Not Today", value=str(not_today_count), inline=True)

        pending = [
            m for m in self.channel_members
            if not m.bot and m.id not in self.votes
        ]
        embed.add_field(name="⏳ Pending", value=str(len(pending)), inline=True)

        embed.set_footer(text="Use the menus below to place your order.")
        return embed

    # -- Summary -------------------------------------------------------------

    def get_poll_summary(self):
        now = int(datetime.datetime.now().timestamp())
        day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][self.weekday]

        item_counts: dict[str, int] = {}
        addon_counts: dict[str, int] = {}
        not_today_members: list[str] = []
        did_not_vote: list[str] = []
        per_person_lines: list[str] = []

        for member in self.channel_members:
            if member.bot:
                continue
            vote = self.votes.get(member.id)
            if vote is None:
                did_not_vote.append(member.name)
                continue

            if vote.get("not_today"):
                not_today_members.append(member.name)
                per_person_lines.append(f"**{member.name}** — Not Today")
                continue

            fixed = vote.get("fixed")
            others = vote.get("others")
            addons = vote.get("addons") or []

            if not fixed and not others:
                # Interacted but submitted nothing — treat as no order
                did_not_vote.append(member.name)
                continue

            if fixed:
                item_counts[fixed] = item_counts.get(fixed, 0) + 1
            if others:
                item_counts[others] = item_counts.get(others, 0) + 1
            for a in addons:
                addon_counts[a] = addon_counts.get(a, 0) + 1

            order_parts = []
            if fixed:
                order_parts.append(fixed)
            if others:
                order_parts.append(others)
            if addons:
                order_parts.append("+ " + ", ".join(addons))
            per_person_lines.append(f"**{member.name}** — {' | '.join(order_parts)}")

        # --- Aggregate text (WhatsApp) ---
        aggregate_text = "Orders:\n"
        if item_counts:
            for item, count in item_counts.items():
                aggregate_text += f"{item}: {count}\n"
        else:
            aggregate_text += "(no orders)\n"

        if addon_counts:
            aggregate_text += "\nExtras:\n"
            for addon, count in addon_counts.items():
                aggregate_text += f"{addon}: {count}\n"

        # --- Embed (Discord markdown) ---
        embed_desc = "📊 **ORDER SUMMARY**\n"
        if item_counts:
            for item, count in item_counts.items():
                embed_desc += f"  {item}: **{count}**\n"
        else:
            embed_desc += "  (no orders)\n"

        if addon_counts:
            embed_desc += "\n➕ **Extra:**\n"
            for addon, count in addon_counts.items():
                embed_desc += f"  {addon}: **{count}**\n"

        if did_not_vote:
            embed_desc += f"\n❌ **No Vote ({len(did_not_vote)}):** {', '.join(did_not_vote)}\n"

        embed = discord.Embed(
            title=f"📊 {day_name} <t:{now}:D>",
            description=embed_desc,
            color=discord.Color.green()
        )

        # --- Plain text per-person message ---
        plain_msg = f"**✅ Poll Summary — {day_name} <t:{now}:D>**\n"
        plain_msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        plain_msg += "👤 **PER PERSON**\n"
        for line in per_person_lines:
            plain_msg += f"  {line}\n"

        if not_today_members:
            plain_msg += f"\n🙅 **Not Today ({len(not_today_members)}):** {', '.join(not_today_members)}\n"

        plain_msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ END\n"

        return plain_msg, aggregate_text, embed

    # -- Timeout -------------------------------------------------------------

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        bot.is_poll_active = False

        plain_msg, aggregate_text, embed = self.get_poll_summary()

        logger.info(f"Poll closed — initiated by {self.initiator.name} | closed at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Poll summary:\n{aggregate_text}")

        try:
            whatsapp_url = generate_whatsapp_link(aggregate_text)
            view = WhatsappView(whatsapp_url)
            await self.initiator.send(plain_msg)
            await self.initiator.send(embed=embed, view=view)
        except discord.HTTPException as e:
            logger.error(f"Failed to DM summary to {self.initiator.name}: {e}")

        if self.message:
            try:
                await self.message.edit(content="🛑 **This poll is now closed!**", embed=None, view=None)
            except discord.HTTPException as e:
                logger.error(f"Failed to edit poll message on close: {e}")


# ---------------------------------------------------------------------------
# SLASH COMMAND
# ---------------------------------------------------------------------------

@bot.tree.command(name="khaja", description="Start the daily food order poll")
async def khaja(interaction: discord.Interaction):

    if bot.is_poll_active:
        await interaction.response.send_message(
            "🛑 A poll is already in progress! Please wait for it to finish.", ephemeral=True
        )
        return

    bot.is_poll_active = True

    weekday = datetime.datetime.now().weekday()
    view = KhajaTimeView(
        initiator=interaction.user,
        channel_members=interaction.channel.members,
        weekday=weekday,
    )

    logger.info(f"Poll initiated by {interaction.user.name} | started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    await interaction.response.send_message(
        embed=view.create_embed(), view=view
    )
    view.message = await interaction.original_response()

    try:
        await asyncio.sleep(300)

        members_not_voted = [
            m for m in interaction.channel.members
            if not m.bot and m.id not in view.votes
        ]

        if members_not_voted:
            try:
                names = ", ".join(m.name for m in members_not_voted)
                mentions = ", ".join(m.mention for m in members_not_voted)
                reminder_msg = await interaction.channel.send(
                    f"🔔 **Lunch Reminder!** Quick {mentions}, please place your order!"
                )
                logger.info(f"Reminder sent to: {names}")
                await asyncio.sleep(200)
                await reminder_msg.delete()
                logger.info("Reminder message deleted")
            except discord.HTTPException as e:
                logger.error(f"Reminder cleanup failed: {e}")

    finally:
        bot.is_poll_active = False


# ---------------------------------------------------------------------------
# SYNC SLASH COMMANDS ON READY
# ---------------------------------------------------------------------------

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        logger.info(f"Bot started — logged in as {bot.user} | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | synced {len(synced)} slash command(s)")
    except Exception as e:
        logger.error(f"Failed to sync slash commands: {e}")


bot.run(token)
