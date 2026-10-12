<div class="keep" markdown="1">

# What Tapat does

Tapat is a Chrome extension and a small web server for Google Forms quizzes. The student opens the quiz through the extension. While the quiz is open, the extension blocks a list of sites and records when the student leaves the quiz tab. The professor sees one row per student on a password-protected admin page.

Tapat does not decide who cheated. It gives the professor a record to check.

Code: <https://github.com/Troy-LL/tapat>

Live admin page: <https://tapat-xrg5.onrender.com/admin>

</div>

<div class="keep" markdown="1">

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

</div>

<div class="keep" markdown="1">

# How it works

@@DIAGRAM@@

The professor creates a quiz and gets a start link. Each student pastes the link into the extension with their school email. The server then gives that student a session token, and every event has to include it. A student cannot send events under a classmate's name.

The server sleeps when nobody uses it, so the first visit can take about a minute.

</div>

<div class="keep" markdown="1">

# Professor guide

All of these steps happen on the admin page at <https://tapat-xrg5.onrender.com/admin>.

1. In the Google Form, go to Settings, then Responses, and turn on Collect email addresses.
2. About a minute before the quiz, open the admin page and log in with the admin password.
3. Enter a quiz title and the Form link, then click Create quiz.

@@GRID:08_admin_login.png,10_admin_home.png@@

</div>

<div class="keep" markdown="1">

4. Click Copy start link and send the link to the class. The button changes to Copied.

@@FIG:14_start_link.png@@

</div>

<div class="keep" markdown="1">

5. During the quiz, watch the Students table. Click a row to open that student's timeline, and click it again to close it.

@@FIG:15_students_timeline.png@@

</div>

<div class="keep" markdown="1">

6. After the quiz, download the Form responses as CSV and click Import responses. Students who answered the Form without Tapat get a No session status.

@@GRID:11_import_result.png,12_no_session_rows.png@@

</div>

<div class="keep" markdown="1">

7. After grading, type DELETE and click Delete logs. To remove the quiz as well, type DELETE under Delete quiz and click it. Each button stays off until DELETE is typed.

@@FIG:13_delete_confirm.png@@

</div>

<div class="keep" markdown="1">

# Student guide

1. Open `chrome://extensions`, turn on Developer mode, click Load unpacked and choose the `extension` folder. This only has to be done once.
2. Click the Tapat icon. Paste the start link, enter the same email you use in the Form, and click Open exam.

@@GRID3:02_popup.png,02b_popup_waking.png,02c_popup_offline.png@@

</div>

<div class="keep" markdown="1">

3. Read the consent screen and click "I understand, start the quiz". The Form then opens inside the exam page.

@@GRID:03_consent.png,04_exam.png@@

</div>

<div class="keep" markdown="1">

4. Answer the Form and submit it. If you open a blocked site, Tapat shows a block page and records the attempt. When the Form says your response was recorded, Tapat stops and you can close the tab.

@@GRID:05_blocked.png,06_submitted.png@@

</div>

<div class="keep" markdown="1">

# Status meanings

| Status | Meaning |
|---|---|
| @@CHIP:ok:OK@@ | Tapat ran the whole time. |
| @@CHIP:offline:Offline gap, synced later@@ | The connection dropped, but the missing events arrived later. |
| @@CHIP:silent:Monitor silent@@ | No heartbeat for more than 25 seconds, and nothing came in later. |
| @@CHIP:none:No session@@ | The student is in the Form responses but never started Tapat. |

The Notes column shows when a student opened a blocked site, opened a watched app, or left the quiz three or more times.

</div>

<div class="keep" markdown="1">

# Limitations and privacy

Tapat only blocks the sites on its list. It cannot see a phone or a second computer. The session token stops one student from posting events for another, but it does not prove the student typed their own email. The responses CSV shows that kind of mismatch after the quiz. Events saved offline are lost if the student clears their browser data before reconnecting. Students who do not agree to the consent screen take the quiz on paper or in a proctored room. A flag is a reason to ask the student, not proof.

Events are stored on a hosted server (Render) with a database on Neon, and only the teacher can see them through a password-protected admin page. Tapat stores emails and event types. It does not store page contents, keystrokes or window titles.

</div>
