# ArrRelay First-Run Setup Guide

This guide explains every value requested by the ArrRelay first-run wizard.

> ArrRelay stores integration settings inside its persistent SQLite database under `/data`. You do **not** need to place Discord, Telegram, Radarr or Sonarr secrets in the Docker command.

## Before you begin

Start ArrRelay, then open:

```text
http://YOUR-SERVER-IP:3032
```

The wizard has six steps:

1. Admin account
2. Discord
3. Telegram
4. Radarr
5. Sonarr
6. Finish / Dry Run

Keep **Dry Run enabled** for the first test.

---

## Discord

ArrRelay uses an official Discord bot account. Do not use a user account token or self-bot.

### 1. Create a Discord application and bot

1. Open the Discord Developer Portal:
   https://discord.com/developers/applications
2. Select **New Application**.
3. Give it a name such as `ArrRelay`.
4. Open **Bot**.
5. Create/add the bot if Discord asks you to.
6. Under **Privileged Gateway Intents**, enable:
   - **Message Content Intent**
7. Copy/reset the **Bot Token** and paste it into ArrRelay.

Treat this token like a password.

### 2. Invite the bot to your Discord server

In the Developer Portal:

1. Open **OAuth2** → **URL Generator** or the current bot installation page.
2. Select the bot/application install scope required by Discord.
3. Give the bot only the permissions it needs:
   - View Channels
   - Read Message History
   - Send Messages (needed only if you choose channel replies)
4. Open the generated URL and add the bot to your server.

### 3. Find the Discord Server / Guild ID

In Discord:

1. Open **User Settings**.
2. Open **Advanced**.
3. Enable **Developer Mode**.
4. Right-click your server icon/name.
5. Choose **Copy Server ID**.

Paste that number into **Server / Guild ID**.

### 4. Find the request Channel ID

With Developer Mode still enabled:

1. Right-click the request channel.
2. Choose **Copy Channel ID**.
3. Paste it into ArrRelay.

For multiple channels, separate the IDs with commas:

```text
123456789012345678,987654321098765432
```

### 5. Missing-information reply mode

Choose one:

- **DM requester privately** — recommended when you do not want bot chatter in the request channel.
- **Reply in channel and auto-delete** — ArrRelay replies in the channel and removes the message later.

---

## Telegram

Telegram is the private admin review console.

### 1. Create a Telegram bot

1. Open Telegram.
2. Search for **@BotFather**.
3. Send:
   ```text
   /newbot
   ```
4. Follow the prompts.
5. BotFather gives you a token similar to:
   ```text
   123456789:AAExampleToken
   ```
6. Paste this token into **Telegram Bot Token**.

Do not publish this token.

### 2. Find your Telegram Chat ID

1. Open the new bot in Telegram.
2. Press **Start** or send it any message.
3. In a browser, open:
   ```text
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
4. Look for:
   ```json
   "chat": {
     "id": 123456789
   }
   ```
5. Copy that numeric `id` into **Telegram Admin Chat ID**.

ArrRelay accepts review actions only from the configured admin chat.

---

## Radarr

### 1. Radarr URL

Examples:

If Radarr is on another server:

```text
http://192.168.1.50:7878
```

If ArrRelay and Radarr share the same Docker network:

```text
http://radarr:7878
```

If Radarr runs directly on the Docker host, a LAN address is usually simplest.

### 2. Radarr API Key

In Radarr:

1. Open **Settings**.
2. Open **General**.
3. Find the **Security** section.
4. Copy the **API Key**.

Paste it into ArrRelay.

### 3. Radarr Root Folder

Use the same movie root path Radarr uses when adding movies.

Typical examples:

```text
/movies
/data/media/movies
/mnt/media/Movies
```

You can see configured root folders in Radarr when adding a movie or in Media Management/root-folder configuration.

### 4. Radarr Quality Profile ID

ArrRelay currently asks for the numeric profile ID.

The easiest API method is:

```bash
curl -s -H "X-Api-Key: YOUR_RADARR_API_KEY" \
  "http://YOUR-RADARR:7878/api/v3/qualityprofile"
```

Find the profile you want and use its `id`.

Example:

```json
{
  "id": 1,
  "name": "HD-1080p"
}
```

Use:

```text
1
```

---

## Sonarr

### 1. Sonarr URL

Examples:

```text
http://192.168.1.50:8989
http://sonarr:8989
```

### 2. Sonarr API Key

In Sonarr:

1. Open **Settings**.
2. Open **General**.
3. Find **Security**.
4. Copy the **API Key**.

### 3. Sonarr Root Folder

Use the same series root path Sonarr uses.

Examples:

```text
/tv
/data/media/tv
/mnt/media/TV
```

### 4. Sonarr Quality Profile ID

Run:

```bash
curl -s -H "X-Api-Key: YOUR_SONARR_API_KEY" \
  "http://YOUR-SONARR:8989/api/v3/qualityprofile"
```

Use the `id` belonging to the profile you want.

---

## Dry Run

Keep **Dry Run** enabled at first.

In Dry Run mode ArrRelay can:

- read Discord requests
- validate title / year / Movie-or-Series type
- query Radarr or Sonarr
- detect duplicates
- send Telegram review messages

but it does **not** add/download media.

After testing the complete workflow, disable Dry Run in **Settings**.

---

## Docker networking tips

If ArrRelay cannot connect to Radarr/Sonarr, remember that `localhost` inside the ArrRelay container means the ArrRelay container itself.

If Radarr or Sonarr is elsewhere, use a reachable LAN/IP/hostname.

If they share a Docker network, connect ArrRelay to that network and use container/service names such as:

```text
http://radarr:7878
http://sonarr:8989
```

---

## Troubleshooting

### Check the ArrRelay container

```bash
docker ps --filter name=arrrelay
docker logs --tail 200 -f arrrelay
```

### Restart ArrRelay

```bash
docker restart arrrelay
```

### Update ArrRelay

```bash
docker pull ghcr.io/kasundigital/arrrelay:latest
docker stop arrrelay
docker rm arrrelay
```

Then run the same Docker command again. Keep the same `/data` volume so your configuration remains available.

### Reset everything

Stop/remove the container and delete the persistent ArrRelay data directory/volume only if you intentionally want to remove the admin account, settings and request history.

---

## Security

- Never post bot tokens or API keys in screenshots/issues.
- Do not commit secrets to GitHub.
- Keep the ArrRelay dashboard behind LAN/VPN or HTTPS.
- Use a strong admin password.
- Keep Dry Run enabled until setup has been verified.
