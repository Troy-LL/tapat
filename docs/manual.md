# What Tapat does

Tapat is a Chrome extension and a small web server for Google Forms quizzes. The student opens the quiz through the extension. While the quiz is open, the extension blocks a list of sites and records when the student leaves the quiz tab. The professor sees one row per student on a password-protected admin page.

Tapat does not decide who cheated. It gives the professor a record to check.

The code is at https://github.com/Troy-LL/tapat and the live admin page is at https://tapat-xrg5.onrender.com/admin.

# Features

| Feature | Description |
|---|---|
| Site blocking | Blocks ChatGPT, Gemini, Claude, Word Online, Google Docs and PDF links during the quiz. Google Forms is not blocked. |
| Focus tracking | Records tab switches, new tabs and when Chrome loses focus. |
| Submit detection | Ends the session when the Form says the response was recorded. |
| Heartbeat | The extension checks in every 10 seconds. |
| Offline queue | If the wifi drops, events are saved in the browser and sent later in order. |
| No session check | After the quiz, the professor uploads the Form responses CSV. Students who answered without Tapat are flagged. |
| Deleting data | The professor can delete a quiz's logs, or the whole quiz, after grading. |
| Desktop watcher | Optional. Records when Word, Notes, Preview or Acrobat is opened. It saves app names only. |

# How it works

@@DIAGRAM@@

The professor creates a quiz and gets a start link. Each student pastes the link into the extension with their school email. The server then gives that student a session token, and every event has to include it. A student cannot send events under a classmate's name.

The server sleeps when nobody uses it, so the first visit can take about a minute.

# Professor steps

1. In the Google Form, go to Settings, then Responses, and turn on Collect email addresses.
2. About a minute before the quiz, open the admin page and log in.
3. Enter a quiz title and the Form link, then click Create quiz.
4. Click Copy start link and send the link to the class.
5. During the quiz, click a student's row to see their timeline.
6. After the quiz, download the Form responses as CSV and click Import responses.
7. After grading, type DELETE and click Delete logs. Use Delete quiz to remove the quiz as well.

@@FIG:09_admin_quiz.png@@

# Student steps

1. Open `chrome://extensions`, turn on Developer mode, click Load unpacked and choose the `extension` folder. This only has to be done once.
2. Click the Tapat icon. Paste the start link, enter the same email you use in the Form, and click Open exam. If the popup says the server is waking up, wait.
3. Read the consent screen and click "I understand, start the quiz".
4. Answer and submit the Form. If you open a blocked site, Tapat shows a block page and records it. If your wifi drops, keep answering.

@@PAIR:02_popup.png:05_blocked_card.png@@

# Status meanings

| Status | Meaning |
|---|---|
| @@CHIP:ok:OK@@ | Tapat ran the whole time. |
| @@CHIP:offline:Offline gap, synced later@@ | The connection dropped, but the missing events arrived later. |
| @@CHIP:silent:Monitor silent@@ | No heartbeat for more than 25 seconds, and nothing came in later. |
| @@CHIP:none:No session@@ | The student is in the Form responses but never started Tapat. |

The Notes column shows when a student opened a blocked site, opened a watched app, or left the quiz three or more times.

# Limitations and privacy

Tapat only blocks the sites on its list. It cannot see a phone or a second computer. The session token stops one student from posting events for another, but it does not prove the student typed their own email. The responses CSV shows that kind of mismatch after the quiz. Events saved offline are lost if the student clears their browser data before reconnecting. Students who do not agree to the consent screen take the quiz on paper or in a proctored room. A flag is a reason to ask the student, not proof.

Events are stored on a hosted server (Render) with a database on Neon, and only the teacher can see them through a password-protected admin page. Tapat stores emails and event types. It does not store page contents, keystrokes or window titles.
