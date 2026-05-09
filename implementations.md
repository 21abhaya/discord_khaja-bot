# Khaja Bot — Implementation Changelog

---

## v1.0.0 — Initial Version

**File:** `khaja_bot.py` (207 lines)

### Overview

A simple Discord bot for collecting daily food orders from channel members. One command, four buttons, flat in-memory vote storage, and a DM summary sent to the poll initiator on close.

### Command

- Registered via `@bot.command(name='khaja')` — a **prefix command**, not a true Discord slash command.
- Triggered when a user types `/khaja` as a plain text message in chat.
- Required the `message_content` intent to read message text.

### UI

Four buttons on a single message:

| Button | Style | Action |
|--------|-------|--------|
| Full | Primary (blue) | Records vote as `"Full"` |
| Half | Success (green) | Records vote as `"Half"` |
| Something else | Secondary (grey) | Opens `ModalForSomethingElse` — freeform text input |
| Not Today | Danger (red) | Records vote as `"Not Today"` |

### Vote Storage

```python
votes: dict[int, str]
# e.g. { 123456: "Full", 789012: "Chicken Momo" }
```

A flat dictionary mapping `user_id` to a single string. No structure — custom orders were raw freeform text from a modal.

### Poll Lifecycle

1. `/khaja` typed in channel → poll message sent
2. `asyncio.sleep(300)` — 5 minutes
3. Reminder ping sent to members who haven't voted
4. `asyncio.sleep(150)` — 2.5 minutes
5. Reminder deleted
6. View times out at 900 seconds (15 minutes total) → `on_timeout()` fires
7. Buttons disabled, poll message edited to "closed", DM summary sent to initiator

### Summary Format

Single section listing:
- Total votes
- Full Portion: count + names
- Half Portion: count + names
- Custom Orders: name + freeform text
- Not Joining: names
- No Votes from: names

### Known Bug

In the `finally` block of the `khaja` command (line 205), the guard flag was reset as:

```python
bot.is_bot_active = False   # wrong attribute name
```

The correct attribute was `bot.is_poll_active`. This meant if the poll command exited via the `finally` block (e.g. on error), the flag was never actually cleared, and the bot would be stuck refusing new polls until restarted. The flag was only correctly reset inside `on_timeout()`.

---

## v2.0.0 — Menu-Driven Poll with Structured Orders

**File:** `khaja_bot.py` (461 lines)

### Overview

A full rewrite introducing a structured weekly menu, Discord Select Menu components, per-item add-ons, and a two-section summary (aggregate counts + per-person breakdown). The goal was to eliminate the manual re-summarization step the initiator had to do after receiving the v1 DM.

---

### [CHANGED] Command: `bot.command` → `bot.tree.command`

**v1:**
```python
@bot.command(name='khaja')
async def khaja(ctx):
    ...
    view.message = await ctx.send("Pick your portion!", embed=..., view=view)
```

**v2:**
```python
@bot.tree.command(name="khaja", description="Start the daily food order poll")
async def khaja(interaction: discord.Interaction):
    ...
    await interaction.response.send_message(embed=..., view=view)
    view.message = await interaction.original_response()
```

**What changed and why:**

`bot.command` registers a prefix command — the bot watches all messages in the channel and reacts when it sees the prefix `/` followed by `khaja`. This is not a real Discord slash command. It does not show up in Discord's `/` command picker UI, has no description visible to users, and relies on the `message_content` intent (which Discord restricts for verified bots).

`bot.tree.command` registers a proper **application command** with Discord's API. Discord itself handles routing the interaction to the bot. It shows up in the slash command picker with a description, supports parameter autocomplete, and does not require the `message_content` intent.

The response mechanism also changes: prefix commands respond with `ctx.send(...)`, while slash commands respond via `interaction.response.send_message(...)`. The message reference is retrieved after via `interaction.original_response()`.

**Sync requirement:**

Application commands must be registered with Discord before they appear. This is done once via `bot.tree.sync()`, which sends all registered commands to Discord's API. Added an `on_ready` event to handle this automatically on startup:

```python
@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} slash command(s).")
```

After the first successful sync, the `/khaja` command will appear in Discord's UI for all members of the server.

---

### [ADDED] Menu Data Constants and Helper Functions

All menu data is defined at the top of the file as module-level constants, making it easy to update the menu without touching any UI or logic code.

**`ALL_ITEMS`** — the full pool of every orderable item and its variants:

```python
ALL_ITEMS = {
    "Fried Rice": ["Full", "Half", "Egg-Full", "Egg-Half"],
    "Anda-Chiura": ["Full", "Half"],
    "Momo": ["Veg Steam", "Veg Fried", "Chicken Steam", "Chicken Fried", "Buff Steam", "Buff Fried"],
    "Chowmein": ["Chicken Full", "Chicken Half", "Veg Full", "Veg Half", "Buff Full", "Buff Half"],
    "Chana": [],
    "Boiled Eggs": [],      # special — triggers egg count modal
    "Syabhale": [],
    "Pangra-Chiura": [],
    "Dahi Chiura": [],
    "Dahi": [],
}
```

Items with an empty variants list are single-option items. `Boiled Eggs` is a special case — selecting it triggers a modal (see below).

**`ADDONS`** — add-ons available every day:

```python
ADDONS = ["Momo ko Achaar", "Tomato Ketchup", "Salt"]
```

**`FIXED_ITEM_BY_DAY`** — maps Python weekday integers (0=Monday) to the featured item for that day:

```python
FIXED_ITEM_BY_DAY = {
    0: "Fried Rice",
    1: "Anda-Chiura",
    2: "Momo",
    3: "Chowmein",
    4: "Momo",       # Friday shares Momo with Wednesday
}
```

**Helper functions** build the `discord.SelectOption` lists dynamically from the constants above:

- `get_fixed_item(weekday)` — returns today's fixed item name, or `None` on weekends
- `build_fixed_options(item_name)` — returns select options for all variants of the fixed item
- `build_others_options(fixed_item_name)` — returns select options for every item *except* today's fixed item (auto-excludes it)
- `build_addon_options()` — returns select options for all add-ons

---

### [ADDED] `ModalForBoiledEggs` (replaces `ModalForSomethingElse`)

**v1** had a generic freeform modal (`ModalForSomethingElse`) that accepted any text as a custom order.

**v2** replaces this with a focused modal specifically for Boiled Eggs, triggered only when the user selects "Boiled Eggs" from the Others menu:

```python
class ModalForBoiledEggs(discord.ui.Modal, title="Boiled Eggs — How many?"):
    egg_count = discord.ui.TextInput(label="Number of eggs", placeholder="e.g. 2", ...)
```

On submit:
- Validates the input is a positive integer; responds with an ephemeral error if not
- Stores the order as a formatted string: `"Boiled Eggs x2"` under `votes[user_id]["others"]`
- Edits the poll message to refresh the embed with updated counts

This ensures Boiled Eggs orders aggregate correctly in the summary (e.g. `Boiled Eggs x2: 3`) rather than appearing as unstructured freeform text.

---

### [CHANGED] UI: 4 Buttons → 3 Select Menus + 2 Buttons

**v1:** 4 buttons (Full, Half, Something else, Not Today)

**v2:** 3 select menus + 2 buttons across 4 action rows:

| Row | Component | Type | Description |
|-----|-----------|------|-------------|
| 0 | `FixedItemSelect` | Single select | Today's featured item and all its variants. Only shown Mon–Fri. |
| 1 | `OthersSelect` | Single select | All items excluding today's fixed item. Selecting Boiled Eggs opens a modal. |
| 2 | `AddonsSelect` | Multi select | Add-ons — user can pick any combination of Momo ko Achaar, Tomato Ketchup, Salt. |
| 3 | Submit Order (green) | Button | Confirms and records the order. |
| 3 | Not Today (red) | Button | Opts out entirely. Clears any partial selections. |

The select menus are implemented as separate classes (`FixedItemSelect`, `OthersSelect`, `AddonsSelect`) that extend `discord.ui.Select` and are added to the view dynamically in `KhajaTimeView.__init__`. The two buttons are defined inline on the view class using `@discord.ui.button` decorators.

**Why a Submit button:**

Select menu interactions fire immediately when a user changes selection. Without a Submit button, every dropdown change would count as a vote, and there would be no way to distinguish "user is still deciding" from "user has confirmed". The Submit button gives users a deliberate confirmation step — selections are staged in `votes[user_id]` but only considered a confirmed order once Submit (or Not Today) is clicked.

---

### [CHANGED] Vote Storage: flat string → structured dict per user

**v1:**
```python
votes: dict[int, str]
# { user_id: "Full" }
# { user_id: "Chicken Momo" }
```

**v2:**
```python
votes: dict[int, dict]
# {
#   user_id: {
#     "fixed": "Momo — Chicken Steam",   # str or None
#     "others": "Boiled Eggs x2",         # str or None
#     "addons": ["Momo ko Achaar"],        # list
#     "not_today": False                   # bool
#   }
# }
```

Each user's vote is now a dictionary with four keys. This structure:
- Separates the fixed item selection from the others selection (a user can order both)
- Keeps add-ons as a list for easy iteration during aggregation
- Uses the `not_today` flag to cleanly distinguish opt-outs from unsubmitted selections

A user who interacted with a dropdown but never hit Submit will have a partial dict in `votes`. The summary logic treats a vote with both `fixed` and `others` as `None` (and `not_today` as `False`) as a non-voter.

---

### [CHANGED] `create_embed()` — now shows menu and live counts

**v1:** Static embed showing cumulative Full / Half / Not Today / Others counts.

**v2:** Dynamic embed showing:

1. **Today's Special** — the fixed item name and all its variants listed, so users know what's available before opening the dropdown
2. **Current Orders** — live running tally of item counts as members submit, updated on every interaction
3. **Three status counters** — Ordered (confirmed submits), Not Today, Pending (channel members who haven't interacted yet)
4. **Footer** — instruction text reminding users to hit Submit

---

### [CHANGED] `get_poll_summary()` — two-section structured summary

**v1:** Single section listing individuals grouped by vote type (Full, Half, Custom, Not Today, No Vote).

**v2:** Two sections:

**Section 1 — Order Aggregate:**

Iterates all votes and builds two count dictionaries — one for food items, one for add-ons. Produces a clean totals block ready to hand directly to the restaurant:

```
📊 ORDER AGGREGATE
  Momo — Chicken Steam: 5
  Fried Rice — Full: 3
  Boiled Eggs x2: 1

➕ Add-ons:
  Momo ko Achaar: 7
  Salt: 2

🙅 Not Today (2): name1, name2
❌ No Vote (1): name3
```

**Section 2 — Per Person:**

Lists every member's full order on one line:

```
👤 PER PERSON
  name — Momo — Chicken Steam | Boiled Eggs x2 + Momo ko Achaar
  name — Fried Rice — Full
  name — Not Today
```

Members who interacted but submitted no selection are counted under No Vote, not under Not Today.

---

### [CHANGED] `on_timeout()` — improved close behaviour

**v1:** Edited the poll message content to `"🛑 This poll is now closed!"` but left the embed in place.

**v2:** Edits the poll message with `embed=None` to remove the embed entirely on close, leaving only the closed message. This avoids the stale live-count embed remaining visible after the poll ends.

Error handling for both the DM send and the message edit is now wrapped in individual `try/except` blocks so a failure in one does not prevent the other from running.

---

### [FIXED] `is_poll_active` guard flag

**v1 bug:** The `finally` block in the `khaja` command reset `bot.is_bot_active` (wrong attribute), meaning the poll lock was never released via the command path.

**v2 fix:** Corrected to `bot.is_poll_active = False` in both the `finally` block of the command and in `on_timeout()`, ensuring the lock is always released regardless of how the poll ends.

---

## v2.1.0 — Syabhale Count Modal

### [ADDED] `ModalForSyabhale`

Syabhale, like Boiled Eggs, is an item where quantity matters. A new modal `ModalForSyabhale` was added mirroring the structure of `ModalForBoiledEggs`:

```python
class ModalForSyabhale(discord.ui.Modal, title="Syabhale — How many?"):
    syabhale_count = discord.ui.TextInput(label="Number of Syabhale", ...)
```

On submit:
- Validates input is a positive integer; sends an ephemeral error if not
- Stores the order as `"Syabhale x{count}"` under `votes[user_id]["others"]`
- Refreshes the embed with updated counts

### [CHANGED] `OthersSelect.callback` — added Syabhale intercept

The callback previously only intercepted `"Boiled Eggs"` to trigger a modal. A second check was added for `"Syabhale"`:

```python
if chosen == "Boiled Eggs":
    await interaction.response.send_modal(ModalForBoiledEggs(view))
    return
if chosen == "Syabhale":
    await interaction.response.send_modal(ModalForSyabhale(view))
    return
```

Both items now produce structured, countable order strings (`"Boiled Eggs x2"`, `"Syabhale x3"`) that aggregate correctly in the summary.

---

## v2.2.0 — Logging

### [ADDED] Logger setup

Replaced all `print` and `sys.stdout.write` calls with a named logger (`khaja_bot`). The logger has two handlers that both receive every log line simultaneously:

- **Console handler** (`StreamHandler`) — displays logs in the terminal as before
- **File handler** (`FileHandler`) — appends logs to `khaja_bot.log` in the working directory, UTF-8 encoded

Log format:
```
2026-05-09 10:32:11 | INFO     | <message>
```

`import sys` was removed as it was only used for `sys.stdout.write`.

### [CHANGED] What is logged and where

| Location | Level | Message |
|----------|-------|---------|
| `on_ready` | INFO | `Bot started — logged in as {bot.user} \| {datetime} \| synced N slash command(s)` |
| `khaja` command | INFO | `Poll initiated by {name} \| started at {datetime}` |
| `khaja` command — reminder | INFO | `Reminder sent to: {names}` |
| `khaja` command — reminder deleted | INFO | `Reminder message deleted` |
| `FixedItemSelect.callback` | INFO | `{name} selected fixed: {item}` |
| `OthersSelect.callback` | INFO | `{name} selected others: {item}` |
| `AddonsSelect.callback` | INFO | `{name} selected addons: [list]` |
| `ModalForBoiledEggs.on_submit` | INFO | `{name} selected others: Boiled Eggs x{n}` |
| `ModalForSyabhale.on_submit` | INFO | `{name} selected others: Syabhale x{n}` |
| `submit_button` | INFO | `{name} submitted order` |
| `not_today_button` | INFO | `{name} — Not Today` |
| `on_timeout` | INFO | `Poll closed — initiated by {name} \| closed at {datetime}` |
| `on_timeout` | INFO | Full summary block (exact DM text) |
| DM send failure | ERROR | `Failed to DM summary to {name}: {exception}` |
| Poll message edit failure | ERROR | `Failed to edit poll message on close: {exception}` |
| Reminder cleanup failure | ERROR | `Reminder cleanup failed: {exception}` |
| Slash command sync failure | ERROR | `Failed to sync slash commands: {exception}` |

Datetime is only included in three log lines: bot start (`on_ready`), poll start (`khaja` command), and poll close (`on_timeout`). All other log lines contain only the event description.

### [CHANGED] `on_ready` session separator

An empty line (`logger.info("")`) is logged before the bot start line so each restart is visually separated in the log file.

---

## v2.3.0 — WhatsApp Summary Button + Submit Validation — 2026-05-09

### [CHANGED] `get_poll_summary()` — split into three return values

The method now returns a tuple `(plain_msg, aggregate_text, embed)` instead of a single string.

**`plain_msg`** (str) — per-person breakdown only, sent as a plain Discord DM:
```
✅ Poll Summary — Monday <t:...:D>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 PER PERSON
  **alice** — Momo — Chicken Steam
  **bob** — Not Today
  ...
🙅 Not Today (1): bob
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ END
```
- Not Today members appear here, not in the aggregate

**`aggregate_text`** (str) — aggregate counts only, in WhatsApp markdown (`*bold*`), used as the WhatsApp message body:
```
📊 *ORDER AGGREGATE*
  Momo — Chicken Steam: *3*

➕ *Extra:*
  Momo ko Achaar: *2*

❌ *No Vote (1):* alice
```
- "Add-ons" label renamed to "Extra"
- No Not Today section

**`embed`** (`discord.Embed`) — same aggregate content as `aggregate_text` but in Discord markdown (`**bold**`), sent as an embed with the WhatsApp button attached.

---

### [ADDED] `WhatsappView`

A new `discord.ui.View` subclass added above `KhajaTimeView`:

```python
class WhatsappView(discord.ui.View):
    def __init__(self, url):
        super().__init__()
        self.add_item(discord.ui.Button(label="Whatsapp it", url=url))
```

The `url` is produced by `send_message(aggregate_text)` from `message.py`, which URL-encodes the aggregate text and produces a `wa.me` deep link that pre-fills the message on the initiator's WhatsApp.

---

### [CHANGED] `on_timeout()` — two DMs instead of one

**Before:**
```python
summary = self.get_poll_summary()
await self.initiator.send(summary)
```

**After:**
```python
plain_msg, aggregate_text, embed = self.get_poll_summary()
whatsapp_url = send_message(aggregate_text)
view = WhatsappView(whatsapp_url)
await self.initiator.send(plain_msg)
await self.initiator.send(embed=embed, view=view)
```

The initiator now receives two DMs:
1. Plain text per-person list
2. Aggregate embed with a "Whatsapp it" button

The logger now logs only `aggregate_text` (plain text, WhatsApp markdown) instead of the full summary.

---

### [FIXED] Submit button validation

Previously, the Submit button accepted clicks from users who had not selected any food item, silently recording an empty order. A validation check was added:

```python
current = self.votes.get(uid, {})
if not current.get("fixed") and not current.get("others"):
    await interaction.response.send_message(
        "⚠️ Please select at least one food item before submitting.", ephemeral=True
    )
    return
```

The error is sent as an ephemeral message (visible only to the user). Partial selections (e.g. add-ons already picked) are preserved in `self.votes` so the user can continue without losing their choices.

---

## v2.4.0 — Deferred Select Interactions + Simplified WhatsApp Aggregate — 2026-05-09

### [CHANGED] Select callbacks — `edit_message` → `defer_update()`

Previously, selecting any dropdown option immediately called `interaction.response.edit_message(...)`, which refreshed the embed and visually registered the selection as a response. This caused confusion — users expected the Submit button to be the confirmation step, but the dropdown was already acting as one.

All three select callbacks now call `await interaction.response.defer_update()` instead:

- `FixedItemSelect.callback`
- `OthersSelect.callback`
- `AddonsSelect.callback`

Selections are still staged into `self.votes[user_id]` immediately, but the embed no longer refreshes on selection. The embed only updates when the user clicks **Submit Order** or **Not Today**. This makes the Submit button the clear and only confirmation step.

`ModalForBoiledEggs.on_submit` and `ModalForSyabhale.on_submit` are unchanged — they still call `edit_message` since the modal submission itself is the confirmation for those items.

---

### [CHANGED] `aggregate_text` — plain text, no markdown or emojis

The WhatsApp aggregate string was previously formatted with WhatsApp markdown (`*bold*`) and emojis. It is now plain structured text with no decoration:

```
Orders:
Chicken Momo: 3
Veg Fried Momo: 2
Full Fried Rice: 2

Extras:
Momo ko Achaar: 2
```

- "Add-ons" / "Extra" header renamed to "Extras:"
- No Vote and Not Today sections removed entirely from `aggregate_text`
- The `discord.Embed` description is unchanged — it still uses Discord `**bold**` and emojis

---

## v2.5.0 — Removed Submit Button, Selection = Submission — 2026-05-09

### [REMOVED] `submit_button`

The Submit Order button and its validation logic were removed entirely. Clicking Submit was redundant — users had already made their selection via the dropdown. Having an extra confirmation step caused confusion about whether the order was placed or not.

### [CHANGED] Select callbacks — restored `edit_message`, selection is now submission

`FixedItemSelect.callback`, `OthersSelect.callback`, and `AddonsSelect.callback` all call `interaction.response.edit_message(...)` immediately on selection, refreshing the embed with updated live counts. Selecting a food item from a dropdown is now the act of placing an order — no further action required.

`ModalForBoiledEggs.on_submit` and `ModalForSyabhale.on_submit` are unchanged — submitting the modal is the confirmation for those items.

### [CHANGED] Embed footer

Updated to remove the stale "hit Submit" instruction:

**Before:** `"Use the menus below to place your order, then hit Submit."`
**After:** `"Use the menus below to place your order."`

---

## v2.6.0 — Chicken Sausage & Buff Sausage with Count Modal — 2026-05-09

### [ADDED] `Chicken Sausage` and `Buff Sausage` to `ALL_ITEMS`

Both added as standalone items with empty variants lists, following the same pattern as `Boiled Eggs` and `Syabhale`:

```python
"Chicken Sausage": [],  # special — triggers modal for count
"Buff Sausage": [],     # special — triggers modal for count
```

### [ADDED] `ModalForSausages`

A single modal class shared by both sausage variants. Takes `item_name` as a constructor argument so the stored label reflects whichever was selected:

```python
class ModalForSausages(discord.ui.Modal, title="Sausages — How many?"):
    def __init__(self, view: "KhajaTimeView", item_name: str):
        ...
```

On submit:
- Validates input is a positive integer; sends an ephemeral error if not
- Stores as `"Chicken Sausage x{count}"` or `"Buff Sausage x{count}"` under `votes[user_id]["others"]`
- Refreshes the embed with updated counts

### [CHANGED] `OthersSelect.callback` — added Sausage intercept

```python
if chosen in ("Chicken Sausage", "Buff Sausage"):
    await interaction.response.send_modal(ModalForSausages(view, chosen))
    return
```

One modal class handles both variants — the `item_name` parameter carries the distinction.
