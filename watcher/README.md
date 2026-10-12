# Tapat watcher

Run during the quiz so Word, Notes, Preview and Acrobat opening gets logged.

```
python watcher.py --email you@school.edu --session <session id from the exam page>
```

- macOS uses `osascript`; Windows needs `pip install -r requirements.txt`.
- Logs app names only, never window titles.
- Exits by itself once the Form is submitted.
- Change the list with `--apps "Microsoft Word,Notes"`.
