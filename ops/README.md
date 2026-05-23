# Ops — autonomous publishing loop

## macOS (launchd)

1. Edit `ops/com.kterskih.tt-publisher.plist` and replace every `REPLACE_ME` with your `$USER`.
2. Copy to launchd:
   ```bash
   cp ops/com.kterskih.tt-publisher.plist ~/Library/LaunchAgents/
   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.kterskih.tt-publisher.plist
   ```
3. Verify it's running:
   ```bash
   launchctl print gui/$(id -u)/com.kterskih.tt-publisher
   ```
4. Tail logs:
   ```bash
   tail -f ~/.local/share/telegram-tech-publisher/loop.log
   ```
5. Stop / unload:
   ```bash
   launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.kterskih.tt-publisher.plist
   ```

## Linux (systemd)

Save the following as `~/.config/systemd/user/tt-publisher.service`, replacing `REPLACE_ME`:

```ini
[Unit]
Description=telegram-tech-publisher autonomous loop
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/REPLACE_ME/telegram-tech-publisher
ExecStart=/home/REPLACE_ME/.local/bin/uv run telegram-tech-publisher daemon
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
```

Then:
```bash
systemctl --user daemon-reload
systemctl --user enable --now tt-publisher.service
journalctl --user -u tt-publisher -f
```
