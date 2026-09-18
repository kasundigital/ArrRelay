# ArrRelay

**ArrRelay** is a free, open-source, Docker-first request automation service that listens to selected Discord channels, validates movie/series requests, sends clear requests to Radarr or Sonarr, and forwards ambiguous requests or errors to a private Telegram admin review flow.

> Discord is the request inbox. Radarr/Sonarr do the media automation. Telegram is the private review console. ArrRelay ties them together.

## Features

- Docker / Docker Compose deployment
- Private **admin-only web dashboard** on port `3032`
- First-run administrator setup and password login
- Browser-based configuration for Discord, Telegram, Radarr and Sonarr
- Watches only the Discord server/channels you configure
- Requires **Movie/Series + Title + Year** before automatic processing
- Missing information can be requested by Discord reply or private DM
- Movie requests route to Radarr
- Series requests route to Sonarr
- High-confidence matches can be added and searched automatically
- Ambiguous matches go to Telegram with result-selection and Cancel buttons
- Duplicate detection before adding media
- SQLite request history that survives Docker restarts
- Dashboard counters for total requests, movie requests, series requests, reviews, added items and failures
- Live Radarr library totals and downloaded-movie count
- Live Sonarr series totals and downloaded/total episode counts
- Recent-request activity table
- Dry-run mode enabled by default for safe testing
- Responsive dark admin UI
- Built-in **Support ArrRelay** / Buy Me a Coffee button

## Request examples

```text
Movie: No Time to Die (2021)
Series: FBI (2018)
Chicago PD (2014) - Series
```

If information is missing, for example:

```text
The Drop
```

ArrRelay asks the requester to provide the missing type and/or year instead of guessing and downloading the wrong item.

## How the workflow works

```text
Discord message
      |
      v
   ArrRelay
      |
      +-- Missing type/year ----------> Ask Discord requester
      |
      +-- Movie + clear match --------> Radarr -> Add + Search
      |
      +-- Series + clear match -------> Sonarr -> Add + Search
      |
      +-- Ambiguous / lookup error ---> Telegram admin review
                                          |
                                          +-- Select result
                                          +-- Cancel
```

## Docker quick start

Clone the repository:

```bash
git clone https://github.com/kasundigital/ArrRelay.git
cd ArrRelay
cp .env.example .env
```

Change at least `APP_SECRET` in `.env`, then start:

```bash
docker compose up -d --build
```

Open:

```text
http://YOUR-SERVER-IP:3032
```

On the first visit, ArrRelay asks you to create the local administrator account. After login, open **Settings** and configure Discord, Telegram, Radarr and Sonarr.

## First-run setup

1. Create the ArrRelay admin account.
2. Add the Discord bot token, server ID and request-channel IDs.
3. Choose whether missing-information requests should be a channel reply or private DM.
4. Add the Telegram bot token and your private admin chat ID.
5. Add the Radarr URL/API key/root folder/quality profile ID.
6. Add the Sonarr URL/API key/root folder/quality profile ID.
7. Leave **Dry Run** enabled for initial testing.
8. Save settings. ArrRelay restarts the background integrations automatically.
9. After testing is successful, disable Dry Run to allow real add/search operations.

## Discord requirements

The Discord bot needs only the permissions required for the configured request channels:

- View Channel
- Read Message History
- Send Messages if using channel replies
- Message Content Intent enabled in the Discord Developer Portal

For a more private experience, choose **DM requester privately** in ArrRelay Settings.

## Telegram security

Telegram review actions are accepted only from the configured `TELEGRAM_ADMIN_CHAT_ID`. Other chats cannot approve or cancel ArrRelay requests.

## Dashboard

The admin dashboard currently reports:

- Total requests
- Movie requests
- Series requests
- Requests requiring review
- Successfully added requests
- Failed requests
- Radarr total movies
- Radarr movies with files/downloaded
- Sonarr total series
- Sonarr downloaded episodes / total episodes
- Discord listener status
- Recent request activity

## Data

ArrRelay uses SQLite by default:

```text
/data/arrrelay.db
```

The Docker Compose file maps `./data:/data`, so configuration, admin login and request history survive container recreation.

## Security notes

- Do not publish your `.env` file.
- Do not commit Discord, Telegram, Radarr or Sonarr API tokens.
- Change `APP_SECRET` before exposing the web interface.
- Use a reverse proxy with HTTPS if accessing ArrRelay over the internet.
- Keep the admin dashboard private where possible.
- Start with `DRY_RUN=true`.

## Support this free project

ArrRelay is free and open source. If it saves you time or you would like to support continued development, you can buy me a coffee:

[☕ Buy Me a Coffee — Kasun Digital](https://buymeacoffee.com/kasundigital)

A support button is also included in the ArrRelay admin interface.

## Author

**Kasun Indika**  
GitHub: [@kasundigital](https://github.com/kasundigital)

## Status

ArrRelay is under active development. Test with Dry Run before enabling automatic downloads in a production Radarr/Sonarr library.
