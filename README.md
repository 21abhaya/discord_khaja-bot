# Khaja Bot

Khaja Bot is a Python Discord bot for collecting daily food orders. It starts a poll with the `/khaja` slash command, lets members choose their food, and sends the poll summary to the initiator when the poll closes. The summary can also be opened in WhatsApp.

## Requirements

- Python 3.12.3 or a compatible Python 3.12 version
- A Discord application and bot token
- A Discord server where you can add the bot
- A WhatsApp number in international format, without the `+` sign or spaces

## Setup

1. Clone the repository and enter the project directory:

   ```bash
   git clone <repository-url>
   cd discord_khaja-bot
   ```

2. Create and activate a virtual environment:

   Linux/macOS:

   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```

   Windows PowerShell:

   ```powershell
   py -3.12 -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. Install the required packages:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

4. Create the environment file:

   ```bash
   cp .env.example .env
   ```

   On Windows, copy `.env.example` to `.env` manually or run:

   ```powershell
   Copy-Item .env.example .env
   ```

5. Edit `.env` and replace the placeholder values with your Discord application details and WhatsApp number.

## Environment Variables

| Variable | Description |
| --- | --- |
| `DISCORD_TOKEN` | Secret token for the Discord bot |
| `DISCORD_APPLICATION_ID` | Application/client ID from the Discord Developer Portal |
| `DISCORD_PUBLIC_KEY` | Public key from the Discord Developer Portal |
| `WHATSAPP_NUMBER` | Recipient number in international format, without `+` or spaces |

`DISCORD_APPLICATION_ID` and `DISCORD_PUBLIC_KEY` are loaded from `.env` for configuration consistency, although the current bot runtime primarily requires `DISCORD_TOKEN` and `WHATSAPP_NUMBER`.

Never commit `.env` or share your Discord token. If a token is exposed, regenerate it from the Discord Developer Portal immediately.

## Discord Configuration

In the [Discord Developer Portal](https://discord.com/developers/applications):

1. Create an application and add a bot user.
2. Copy the bot token, application ID, and public key into `.env`.
3. Under **Bot > Privileged Gateway Intents**, enable:
   - **Server Members Intent**
   - **Message Content Intent**
4. Invite the bot to your server with the `bot` and `applications.commands` scopes.
5. Grant it permission to view channels, send messages, embed links, and read message history.

The `/khaja` command is synchronized automatically when the bot starts. It may take a short time to appear after the first startup.

## Running the Bot

With the virtual environment activated, run:

```bash
python khaja_bot.py
```

The bot will log startup and poll activity to the console and to `khaja_bot.log`. In Discord, use:

```text
/khaja
```

The poll remains active for five minutes, followed by a reminder period for members who have not voted. Poll state is held in memory and is lost if the bot restarts.

## Project Files

- `khaja_bot.py` - Discord bot, slash command, poll UI, and logging
- `whatsapp.py` - WhatsApp summary link generation
- `requirements.txt` - Pinned Python dependencies
- `.env.example` - Safe environment variable template

## Troubleshooting

- **The command does not appear:** Confirm the bot was invited with the `applications.commands` scope and wait briefly after startup.
- **The bot cannot see members:** Confirm the Server Members Intent is enabled in the Developer Portal and that the bot has access to the channel.
- **The bot fails at startup:** Confirm `.env` exists in the project directory, `DISCORD_TOKEN` is valid, and dependencies were installed in the active virtual environment.
- **The WhatsApp button is incorrect:** Confirm `WHATSAPP_NUMBER` includes the country code and contains only digits.
