# What Tapat does

Tapat is an exam monitor for Google Forms quizzes. *Tapat* is Filipino for "honest." The student takes the quiz inside the Tapat Chrome extension, which blocks a listed set of sites and notes when the student leaves the quiz. The professor sees one row per student on a password-protected admin page. Tapat gives the professor a record; the professor decides.

Repo: **https://github.com/Troy-LL/tapat** · Live admin: **https://tapat-xrg5.onrender.com/admin**

# Features

| Feature | What it does |
|---|---|
| Block list | Blocks ChatGPT, Gemini, Claude, Word Online / office.com, Google Docs documents and `.pdf` links during the quiz. Google Forms is never blocked. Attempts are logged. |
| Focus tracking | Logs tab switches, new tabs and Chrome losing focus. |
| Submit detection | Closes the session when the Form records the response. |
| Heartbeat | Checks in every 10 seconds so a stopped monitor shows up. |
| Offline queue | Keeps events in the browser while offline and sends them in order later, never twice. |
| Waking state | Shows "Server waking up…" while the free server starts. |
| No session | Flags students in the Form responses CSV who never ran Tapat. |
| Delete logs / quiz | Removes a quiz's logs, or the whole quiz, after grading. |
| Desktop watcher | Optional; logs when Word, Notes, Preview or Acrobat comes to the front (app names only). |

# How it works

```
 Student's computer                                  Tapat server (Render)
+------------------------------+  start link + email  +----------------------+
| Chrome + Tapat extension     | -------------------> | events, quizzes      |
| consent, Google Form         |  events              | database (Neon)      |
| block list, focus, offline   | -------------------> |                      |
+------------------------------+                      | /admin for professor |
 Desktop watcher (optional) ------ app events ------> +----------------------+
```

Each quiz has a start link with a secret part. Starting gives the student a session token tied to their email and the quiz, and every event must carry it, so no one can send events in a classmate's name. Events are saved in the browser first and retried until the server has them.

# Professor steps

1. In the Google Form, turn on **Collect email addresses** (Settings → Responses).
2. About a minute before the quiz, open https://tapat-xrg5.onrender.com/admin and **Log in**. The first load can take a minute while the free server wakes.
3. Type a title, paste the Form link, and click **Create quiz**.
4. Click **Copy start link** and send it to the class.
5. During the quiz, click a student's row to see their timeline.
6. After the quiz, download the Form responses as CSV and click **Import responses**. Students who skipped Tapat show **No session**.
7. After grading, type `DELETE` and click **Delete logs**, or **Delete quiz** to remove the quiz entirely.

@@FIG:09_admin_quiz.png@@

# Student steps

1. Install once: open `chrome://extensions`, turn on **Developer mode**, click **Load unpacked**, and pick the `extension` folder.
2. Click the Tapat icon, paste the start link, enter your school email (the same one as in the Form), and click **Open exam**. If it says "Server waking up…", wait.
3. Read the consent screen ("This logs tab switches and apps opened, nothing else.") and click **I understand, start the quiz**.
4. Answer and submit the Form. Blocked sites show the block page; click **Back to the exam**. If the wifi drops, keep going; events send when you are back online.

@@FIG:02_popup.png@@

@@FIG:05_blocked.png@@

# Status meanings

| Status | Color | Meaning |
|---|---|---|
| OK | Gray | Monitored the whole time. |
| Offline gap, synced later | Gray-amber | Connection dropped; the events arrived later, nothing missing. |
| Monitor silent | Amber | No heartbeat for over 25 seconds and nothing filled the gap. |
| No session | Red | In the Form responses but never ran Tapat. |

Notes show **Blocked site**, **App opened** and **Left exam** (three or more tab switches or focus losses).

# Limitations and privacy

- It blocks a list, not every site, and can't see a second device.
- Session tokens stop events being faked for a classmate, but don't prove the student typed their own email. The responses CSV catches that mismatch afterward.
- Offline events are lost if the student clears browser data before reconnecting; that gap shows as Monitor silent.
- Students who decline take the quiz on paper or in a proctored room. A flag is a reason to ask, not proof.

Events are stored on a hosted server (Render) with a database on Neon, and only the teacher can see them through a password-protected admin page. Tapat stores emails and event types only, never page contents, keystrokes or window titles.
