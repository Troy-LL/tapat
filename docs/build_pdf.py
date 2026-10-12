"""Build docs/Tapat_INTE301_Project1_Lazaro.pdf, the short user manual, from docs/manual.md and screenshots.

Usage: python docs/build_pdf.py   (needs markdown, pygments, playwright, pypdf)
"""
import base64
import datetime
import html
import pathlib
import re

import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_for_filename
from pygments.util import ClassNotFound
from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "Tapat_INTE301_Project1_Lazaro.pdf"
SHOTS = ROOT / "docs" / "screenshots"
ACCENT = "#1F3A8A"
FIGURES = [
    ("09_admin_quiz.png", "Admin quiz page: start link, one row per student with status and timeline, Import responses, Delete logs and Delete quiz."),
    ("08_admin_login.png", "Professor log in. The password is set only in the server's environment."),
    ("10_admin_home.png", "Admin home: create a quiz from a Google Form link, and the list of quizzes."),
    ("02_popup.png", "Extension popup: paste the start link and enter your school email."),
    ("02b_popup_waking.png", "Popup while the free server wakes up. It waits and opens the exam once the server answers."),
    ("03_consent.png", "Consent screen shown before the quiz starts."),
    ("04_exam.png", "Exam page with a sample quiz embedded in place of a real Google Form."),
    ("05_blocked.png", "Block page when a listed site is opened during the quiz; the attempt is logged."),
    ("02c_popup_offline.png", "Popup while the server can't be reached: events are kept in the browser and sent in order later."),
    ("06_submitted.png", "Sample quiz submitted: Tapat detects the formResponse page and closes the session."),
]
PARTS = [
    ("Tapat server", ["server/app.py", "server/db.py", "server/auth.py", "server/seed.py", "server/run.sh",
                      "server/requirements.txt", "server/sample_responses.csv", "server/tests/test_app.py",
                      "render.yaml"]),
    ("Chrome extension", ["extension/manifest.json", "extension/config.js", "extension/background.js",
                          "extension/popup.html", "extension/popup.js", "extension/exam.html",
                          "extension/exam.js", "extension/blocked.html", "extension/blocked.js",
                          "extension/style.css", "extension/tests/blocklist.test.js"]),
    ("Desktop watcher", ["watcher/watcher.py", "watcher/requirements.txt", "watcher/README.md"]),
    ("Documentation build", ["docs/build_pdf.py"]),
]
LANG = {".py": "Python", ".js": "JavaScript", ".json": "JSON", ".html": "HTML", ".css": "CSS",
        ".sh": "Bash", ".txt": "Text", ".csv": "CSV", ".md": "Markdown", ".yaml": "YAML"}

CSS = f"""
@page {{ size: A4; margin: 20mm 20mm 22mm 20mm; }}
body {{ font-family: 'Inter','Helvetica Neue',Arial,sans-serif; font-size: 10.5pt; line-height: 1.5; color: #111; }}
h1, h2, h3 {{ color: {ACCENT}; break-after: avoid; }}
a {{ color: {ACCENT}; }}
code, pre {{ font-family: 'DejaVu Sans Mono',Consolas,monospace; font-size: 8.5pt; }}
pre {{ white-space: pre-wrap; word-break: break-all; background: #f5f7fb; padding: 8px; border-radius: 4px; }}
table {{ border-collapse: collapse; width: 100%; margin: 8px 0; }}
th, td {{ border: 1px solid #d5dbea; padding: 5px 7px; text-align: left; vertical-align: top; }}
th {{ background: #eef2fb; color: {ACCENT}; }}
.page {{ break-before: page; }}
.cover {{ text-align: center; padding-top: 18mm; }}
.cover h1 {{ font-size: 44pt; margin: 0; }}
.cover .one {{ font-size: 14pt; color: #333; margin: 6px 0 22px; }}
.cover .meta {{ font-size: 11pt; line-height: 1.8; }}
.cover img.logo {{ width: 95mm; border: 0; margin: 0 0 6px; }}
.cover img:not(.logo) {{ max-width: 100%; max-height: 125mm; border: 1px solid #ccd; margin-top: 18px; }}
.toc ol {{ font-size: 12pt; line-height: 2; }}
.readme {{ counter-reset: h2; }}
.readme h1 {{ display: none; }}
.readme h2.sec {{ break-before: auto; margin-top: 14px; }}
.readme {{ break-before: page; }}
.cover .kind {{ font-size: 13pt; letter-spacing: .2em; text-transform: uppercase; color: {ACCENT}; margin: 4px 0 0; }}
.cover .url {{ color: {ACCENT}; font-weight: 600; }}
.toc .apx {{ font-size: 12pt; line-height: 2; margin: 6px 0 0 0; }}
.toc ol.src {{ font-size: 11pt; line-height: 1.8; margin-left: 2em; list-style: none; }}
.appendix h3 {{ color: {ACCENT}; }}
.readme h2 {{ counter-increment: h2; border-bottom: 2px solid {ACCENT}; padding-bottom: 2px; }}
.readme h2::before {{ content: counter(h2) ". "; }}
figure {{ break-inside: avoid; margin: 0 0 14px; text-align: center; }}
figure img {{ max-width: 100%; max-height: 95mm; border: 1px solid #ccd; }}
figcaption {{ font-size: 9.5pt; color: #333; margin-top: 4px; }}
.label {{ background: {ACCENT}; color: #fff; font-family: 'DejaVu Sans Mono',monospace; font-size: 8.5pt; padding: 5px 8px; border-radius: 4px 4px 0 0; }}
.listing table {{ border: 0; margin: 0; }}
.listing td {{ border: 0; padding: 0; }}
.listing .linenos {{ color: #999; padding-right: 8px; user-select: none; width: 1%; }}
.listing .linenos pre, .listing .code pre {{ margin: 0; border-radius: 0; padding: 6px; line-height: 1.35; }}
.listing .linenos pre {{ background: #eef0f5; word-break: normal; white-space: pre; }}
.listing tr {{ break-inside: auto; }}
.part h2 {{ font-size: 20pt; }}
.listing .highlight pre {{ margin: 0; border-radius: 0 0 4px 4px; line-height: 1.35; }}
.linenos {{ color: #999; background: #eef0f5; padding: 0 6px 0 2px; margin-right: 6px; }}
{HtmlFormatter(style="friendly").get_style_defs(".highlight")}
"""


def img(name, folder=SHOTS):
    return "data:image/png;base64," + base64.b64encode((folder / name).read_bytes()).decode()


def manual_html():
    """docs/manual.md -> numbered sections, each starting on a new page, with numbered figures."""
    md = (ROOT / "docs" / "manual.md").read_text()
    body = markdown.markdown(md, extensions=["tables", "fenced_code"])
    captions = dict(FIGURES)
    counter = [0]

    def figure(m):
        name = m.group(1)
        counter[0] += 1
        cap = html.escape(captions[name])
        return (f'<figure><img src="{img(name)}"><figcaption><b>Figure {counter[0]}.</b> {cap}'
                f'</figcaption></figure>')

    body = re.sub(r"<p>@@FIG:([\w.]+)@@</p>", figure, body)
    body = re.sub(r"<h1>(.*?)</h1>", r'<h2 class="sec">\1</h2>', body)
    sections = re.findall(r'<h2 class="sec">(.*?)</h2>', body)
    deploy = (ROOT / "docs" / "deploy.md").read_text()
    deploy = re.sub(r"^# .*\n", "", deploy).replace("\n## ", "\n### ")
    appendix = ('<div class="page appendix"><h2>Appendix A. Deployment</h2>'
                + markdown.markdown(deploy, extensions=["tables", "fenced_code"]) + "</div>")
    return body, sections, ""


def listing(path):
    p = ROOT / path
    src = p.read_text()
    n = src.count("\n") + (0 if src.endswith("\n") else 1)
    try:
        lexer = get_lexer_for_filename(p.name, stripnl=False)
    except ClassNotFound:
        lexer = TextLexer(stripnl=False)
    code = highlight(src, lexer, HtmlFormatter(linenos="inline", style="friendly"))
    lang = LANG.get(p.suffix, "Text")
    return f'<div class="page listing"><div class="label">{path} · {lang} · {n} lines</div>{code}</div>'


def build():
    body, sections, appendix = manual_html()
    today = datetime.date.today().strftime("%B %d, %Y").replace(" 0", " ")
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><title>Tapat</title>
<meta name="author" content="Troy Lazaro"><style>{CSS}</style></head><body>
<section class="cover"><img class="logo" src="{img('logo.png', ROOT / 'logo')}" alt="Tapat">
<p class="kind">User manual</p>
<p class="one">An exam monitor for Google Forms quizzes that blocks a listed set of sites and logs when students leave the exam.</p>
<div class="meta"><b>INTE301 Systems Integration &amp; Architecture · Project 1</b><br>
Sir Rodel Villareaz<br>Troy Lazaro<br>{today}<br>
<span class="url">github.com/Troy-LL/tapat · tapat-xrg5.onrender.com/admin</span></div>
<img src="{img('09_admin_quiz.png')}"></section>
<section class="readme">{body}</section>
{appendix}
</body></html>"""
    (ROOT / "docs" / "build").mkdir(exist_ok=True)
    tmp = ROOT / "docs" / "build" / "tapat.html"
    tmp.write_text(doc)
    footer = ('<div style="width:100%;font-size:8pt;color:#555;padding:0 20mm;display:flex;'
              'justify-content:space-between;font-family:Arial"><span>Tapat · INTE301 Project 1</span>'
              '<span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>')
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page()
        pg.goto(tmp.as_uri())
        pg.pdf(path=str(OUT), format="A4", print_background=True, display_header_footer=True,
               header_template="<div></div>", footer_template=footer,
               margin={"top": "20mm", "bottom": "22mm", "left": "20mm", "right": "20mm"})
        b.close()
    w = PdfWriter(clone_from=PdfReader(str(OUT)))
    w.add_metadata({"/Title": "Tapat", "/Author": "Troy Lazaro",
                    "/Subject": "INTE301 Systems Integration & Architecture · Project 1"})
    w.write(str(OUT))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
