# What Tapat is and what it does

Tapat is an exam monitor for quizzes made in Google Forms. *Tapat* is Filipino for "honest."

A student takes the quiz inside the Tapat Chrome extension instead of a normal browser tab. While the quiz is open, Tapat blocks a listed set of sites, notes when the student leaves the quiz, and sends those notes to the professor. The professor sees one row per student on a password-protected admin page and can look at each student's timeline after the quiz.

Tapat does not grade anything and does not decide who cheated. It gives the professor a record to look at, and the professor decides.

Live server: **https://tapat-xrg5.onrender.com**. Admin page: **https://tapat-xrg5.onrender.com/admin**.

# What it can do

| Feature | What it does |
|---|---|
| Block list | Blocks a listed set of sites during the quiz: ChatGPT, Gemini, Claude, Word Online / office.com, Google Docs documents and any `.pdf` link. Google Forms itself is never blocked. Every blocked attempt is logged. |
| Focus tracking | Logs when the student switches tabs, opens a new tab, or Chrome loses focus because another app came to the front. |
| Submit detection | Notices when the Form shows "Your response has been recorded" and closes the session. |
| Heartbeat | The extension checks in every 10 seconds, so a monitor that stops is visible. |
| Offline queue | If the wifi drops, every event is kept in the browser with its own time and number and sent in order later. Nothing is lost or counted twice. |
| Waking state | The free server sleeps when idle. The popup shows "Server waking up…" and waits instead of failing. |
| No session (CSV) | After the quiz, the professor uploads the Form's responses CSV. Anyone who submitted the Form without Tapat running is marked No session. |
| Delete logs | One button removes every log for a quiz after grading. |
| Desktop watcher | An optional small program that logs when Word, Notes, Preview or Acrobat comes to the front. It records app names only, never window titles. |

# How it works

Tapat has three parts.

1. **The Chrome extension** runs on the student's computer. It shows the consent screen, opens the Google Form inside its own exam page, blocks the listed sites and records events.
2. **The Tapat server** runs on Render, with its data in a Postgres database on Neon. It keeps the quizzes and events and serves the admin page.
3. **The desktop watcher** (optional) runs on the student's computer next to Chrome and reports which watched app is in front.

```
 Student's computer                                        Professor
┌───────────────────────────────┐
│ Chrome + Tapat extension      │  start (link + email)  ┌───────────────────┐
│  consent → Google Form        │ ─────────────────────▶ │ Tapat server      │
│  block list · tab/focus log   │  events                │ (Render)          │
│  heartbeat · offline queue    │ ─────────────────────▶ │                   │
└───────────────────────────────┘                        │ /admin ◀───────── professor
┌───────────────────────────────┐  app events            │                   │
│ Desktop watcher (optional)    │ ─────────────────────▶ │ Database (Neon)   │
└───────────────────────────────┘                        └───────────────────┘
```

**Start links and session tokens.** Each quiz has a start link with a secret part only the class receives. When a student starts, the server gives that student a session token tied to their email and that quiz. Every event must carry the token, so one student can't send events in a classmate's name.

**Offline queue.** Every event is saved in the browser first, then sent. If sending fails because the wifi is down or the server is still waking, the extension tries again after 2, 4, 8 and up to 60 seconds, and again as soon as the computer is back online. Events go out in their original order with the time they actually happened. The server ignores any event it already has.

**Statuses.** Each student row shows one status chip. They are explained in the Status meanings section.

# Professor guide

**Before the quiz**

1. In the Google Form, open **Settings → Responses** and turn on **Collect email addresses**. Tapat matches students by email.
2. About a minute before the quiz, open https://tapat-xrg5.onrender.com/admin. The first load can take about a minute because the free server was asleep. That is normal.
3. Enter the admin password and click **Log in**.

@@FIG:08_admin_login.png@@

4. Under New quiz, type a title, paste the Google Form link, and click **Create quiz**.

@@FIG:10_admin_home.png@@

5. On the quiz page, click **Copy start link**. The button changes to **Copied**. Send the link to the class, for example in the class group chat or Google Classroom.

**During the quiz**

6. Watch the Students table. Each row is one student. Click a row to open that student's timeline. Click it again to close it.

**After the quiz**

7. In Google Forms, open **Responses**, click the three dots, and download the responses as CSV.
8. Under Import responses, choose the file and click **Import responses**. Anyone who submitted without Tapat appears with a red **No session** chip.
9. After grading, type `DELETE` in the box under Delete logs and click **Delete logs**. This removes every event, session and imported response for that quiz.

@@FIG:09_admin_quiz.png@@

# Student guide

**Install the extension (once)**

1. Download the Tapat extension folder your professor shared, and unzip it if needed.
2. In Chrome, open `chrome://extensions`.
3. Turn on **Developer mode** (top right).
4. Click **Load unpacked** and choose the `extension` folder.
5. Pin Tapat: click the puzzle piece icon in the toolbar, then the pin next to Tapat.

**Take the quiz**

6. Click the Tapat icon. Paste the start link from your professor, enter your school email (the same one you will use in the Form), and click **Open exam**.

@@FIG:02_popup.png@@

7. If the popup says "Server waking up…", wait. It can take a minute, and the exam opens by itself when the server answers.

@@FIG:02b_popup_waking.png@@

8. Read the consent screen and click **I understand, start the quiz**.

@@FIG:03_consent.png@@

9. Answer the Form inside the exam page and submit it as usual.

@@FIG:04_exam.png@@

10. If you open a site on the block list, you see the block page instead. Click **Back to the exam**. The attempt is logged.

@@FIG:05_blocked.png@@

11. If your wifi drops, keep answering. The popup shows "Offline, N events queued", and the events are sent once you are back online.

@@FIG:02c_popup_offline.png@@

12. When the Form says your response has been recorded, Tapat stops. You can close the tab.

@@FIG:06_submitted.png@@

**Optional, the desktop watcher.** If your professor asks for it, click **Copy watcher command** at the top of the exam page and run it in a terminal from the `watcher` folder. It stops by itself when you submit.

# Status meanings and troubleshooting

| Status | Color | Meaning |
|---|---|---|
| OK | Gray | Tapat ran the whole time and the heartbeats had no long gaps. |
| Offline gap, synced later | Gray-amber | The student's connection dropped for a while. The events from that time arrived later, in order, so nothing is missing. |
| Monitor silent | Amber | No heartbeat for more than 25 seconds and nothing filled the gap later. The extension may have been turned off, Chrome closed, or the browser data cleared. |
| No session | Red | The student is in the Form responses CSV but never ran Tapat. |

The Notes column lists what happened during the session: **Blocked site**, **App opened**, and **Left exam** (three or more tab switches or focus losses).

**The admin page takes a minute to load.** The free server sleeps after about 15 minutes without use. Open the admin page about a minute before the quiz. Once students start, their heartbeats keep it awake.

**A student says the popup is stuck on "Server waking up…".** Wait up to a minute. If it gives up, check the internet connection and click **Open exam** again.

**A student lost wifi.** Nothing needs to be done. Their events are kept and sent later, and the row shows Offline gap, synced later.

**A student shows No session.** They submitted the Form without starting Tapat, for example in another browser or an incognito window, or they typed a different email in Tapat than in the Form. Ask them about it.

**A student shows Monitor silent.** Open their timeline to see when the heartbeats stopped, and ask them what happened.

**The CSV import found 0 responses.** Collect email addresses was off in the Form, so the CSV has no email column. Turn it on before the next quiz.

# Limitations and privacy

**Limitations**

- It blocks a list, not every site. A site that isn't on the list stays open, and a second device can't be seen at all.
- Each session has its own token, so events can't be faked for a classmate. It doesn't prove the student typed their own email. The responses CSV catches that mismatch afterward.
- Events queued offline are kept in the browser. If the student clears browser data or removes the extension before reconnecting, those events are lost and the gap shows as Monitor silent.
- The watcher only runs if the student starts it, and it stops on submit.
- Students who decline take the quiz on paper or in a proctored room.
- A flag is a reason to ask, not proof of cheating. The professor decides.

**Privacy**

Events are stored on a hosted server (Render) with a database on Neon, and only the teacher can see them through a password-protected admin page. Tapat stores emails and event types only, never page contents, keystrokes or window titles. Logs are deleted after grading with **Delete logs**.
