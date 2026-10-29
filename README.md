---
title: Colonel Party Bot
emoji: 🏰
colorFrom: red
colorTo: black
sdk: docker
app_port: 7860
pinned: false
---

# Project Blackout: The Colonel's Garden
Telegram Bot for the 52-person Halloween party.


## GitHub Actions setup

Before enabling the scheduled runner, add these repository **Actions secrets**:

- `BOT_TOKEN`: the Telegram bot token. The workflow deliberately has no hardcoded token fallback.
- `ADMIN_USER_ID`: the numeric Telegram ID of the organizer.
- `DB_ENCRYPTION_KEY`: a long random passphrase used to encrypt the SQLite snapshot before it is stored in Actions cache. Generate one locally with `openssl rand -base64 32`; keep it private and do not commit it.

The scheduled runner restores and decrypts the prior SQLite snapshot, runs one bot process, then encrypts the database on its planned graceful restart. The encrypted cache lets registration, teams, clue progress, accusations, and the first-winner record survive runner restarts without placing guest data in the repository.

**Security note:** if a bot token was ever committed in repository history, removing the fallback from the current workflow does not erase that history. Revoke/rotate the token in BotFather and save the new value as the `BOT_TOKEN` Actions secret before running the workflow again.

The investigation cap is 15; the mystery remains optional for the rest of the party guests.
