# Tapat watcher

Run during the quiz so Word, Notes, Preview and Acrobat opening gets logged.

```
python watcher.py --email you@school.edu --session SESSION_ID --token SESSION_TOKEN --server SERVER
```

- On the exam page, click **Copy watcher command** to get this line with your own values filled in.
- macOS uses `osascript`; Windows needs `pip install -r requirements.txt`.
- Logs app names only, never window titles.
- Exits by itself once the Form is submitted.
- Change the list with `--apps "Microsoft Word,Notes"`.
