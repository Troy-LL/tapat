"""Build docs/Tapat_INTE301_Project1_Lazaro.pdf, the short user manual, from docs/manual.md and screenshots.

Usage: python docs/build_pdf.py   (needs markdown, playwright, pypdf)
"""
import base64
import datetime
import html
import pathlib
import re

import markdown
from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "Tapat_INTE301_Project1_Lazaro.pdf"
SHOTS = ROOT / "docs" / "screenshots"
ACCENT = "#1F3A8A"
FIGURES = [
    ("08_admin_login.png", "Admin login. Only someone with the admin password can open the admin page."),
    ("10_admin_home.png", "Admin home. A new quiz needs a title and the Google Form link. Existing quizzes are listed below."),
    ("14_start_link.png", "Start link. This is the link the class pastes into the extension. It only works for this quiz."),
    ("15_students_timeline.png", "Students table. Each row is one student. The open row shows the timeline, including a blocked ChatGPT visit."),
    ("11_import_result.png", "Import responses. The page confirms how many rows were read from the CSV."),
    ("12_no_session_rows.png", "No session rows. These students are in the Form responses but never started Tapat."),
    ("13_delete_confirm.png", "Delete logs and Delete quiz. A button turns red and clickable only after DELETE is typed."),
    ("02_popup.png", "Popup, ready. The student pastes the start link and enters their email."),
    ("02b_popup_waking.png", "Popup, server waking up. It waits and opens the exam when the server answers."),
    ("02c_popup_offline.png", "Popup, offline. Events are kept in the browser until the connection is back."),
    ("03_consent.png", "Consent screen. It says what is recorded before the quiz starts."),
    ("04_exam.png", "Exam page. The Google Form opens inside Tapat. This screenshot uses a sample quiz."),
    ("05_blocked.png", "Block page. Opening a listed site during the quiz shows this page, and the attempt is recorded."),
    ("06_submitted.png", "Submitted. Tapat sees the Form's confirmation page and ends the session."),
]
CSS = f"""
@page {{ size: A4; margin: 22mm 22mm 24mm 22mm; }}
body {{ font-family: 'Inter','Helvetica Neue',Arial,sans-serif; font-size: 10.5pt; line-height: 1.55; color: #1a1a1a; }}
h1, h2, h3 {{ color: #1a1a1a; break-after: avoid; font-weight: 700; }}
a {{ color: {ACCENT}; text-decoration: none; white-space: nowrap; }}
code {{ font-family: 'DejaVu Sans Mono',Consolas,monospace; font-size: 9pt; }}
p {{ margin: 0 0 8px; }}
ol {{ margin: 0 0 10px; padding-left: 20px; }} li {{ margin-bottom: 3px; }}
table {{ border-collapse: collapse; width: 100%; margin: 6px 0 12px; break-inside: avoid; }}
th, td {{ border-bottom: 0.6pt solid #cfd3da; padding: 5px 8px 5px 0; text-align: left; vertical-align: top; }}
th {{ border-bottom: 1pt solid #1a1a1a; font-weight: 700; }}
td:first-child {{ width: 32%; }}
.page {{ break-before: page; }}
.cover {{ text-align: center; padding-top: 14mm; }}
.cover img.logo {{ width: 90mm; border: 0; margin: 0 0 4px; }}
.cover .kind {{ font-size: 12pt; letter-spacing: .15em; text-transform: uppercase; color: #444; margin: 2px 0 0; }}
.cover .one {{ font-size: 12.5pt; color: #333; margin: 8px 0 20px; }}
.cover .meta {{ font-size: 11pt; line-height: 1.8; }}
.cover .url {{ color: #444; font-size: 10pt; }}
.cover img:not(.logo) {{ max-width: 100%; max-height: 110mm; border: 0.6pt solid #cfd3da; margin-top: 16px; }}
.readme {{ counter-reset: h2; break-before: page; }}
.readme h2 {{ counter-increment: h2; font-size: 14pt; margin: 18px 0 6px; }}
.readme h2:first-child {{ margin-top: 0; }}
.readme h2::before {{ content: counter(h2) ". "; }}
figure {{ break-inside: avoid; margin: 8px 0 14px; text-align: center; }}
figure img {{ max-width: 100%; max-height: 85mm; border: 0.6pt solid #cfd3da; }}
.f-13_delete_confirm img {{ max-width: 72%; }}
figure.diagram svg {{ width: 100%; max-width: 135mm; }}
.keep {{ break-inside: avoid; page-break-inside: avoid; }}
h1, h2 {{ break-after: avoid; page-break-after: avoid; }}
.grid {{ display: grid; gap: 5mm; margin: 6px 0 12px; break-inside: avoid; align-items: start; }}
.grid.g2 {{ grid-template-columns: 1fr 1fr; }} .grid.g3 {{ grid-template-columns: 1fr 1fr 1fr; }}
.grid figure {{ margin: 0; }}
.grid figure img {{ width: 100%; max-height: none; height: auto; }}
.grid.g3 figure img {{ height: 72mm; width: auto; max-width: 100%; object-fit: contain; }}
.grid.g2 figure img {{ height: auto; max-height: 58mm; width: 100%; object-fit: contain; object-position: top; background: #fff; }}
figcaption {{ text-align: left; }}
.pair {{ display: flex; gap: 6mm; align-items: stretch; break-inside: avoid; }}
.pair figure {{ flex: 1; margin: 4px 0 10px; display: flex; flex-direction: column; justify-content: space-between; align-items: center; }}
.pair figure img {{ max-height: 62mm; }}
figcaption {{ font-size: 9.5pt; color: #333; margin-top: 4px; }}
.chip {{ display: inline-block; padding: 0 7px; border-radius: 8px; font-size: 9pt; font-weight: 600; }}
.chip.ok {{ background: #eceef2; color: #4a505c; }} .chip.offline {{ background: #f3ecdc; color: #6e5a2e; }}
.chip.silent {{ background: #fdf0d5; color: #8a5a00; }} .chip.none {{ background: #fde2e2; color: #a61b1b; }}
"""


def img(name, folder=SHOTS):
    return "data:image/png;base64," + base64.b64encode((folder / name).read_bytes()).decode()


def manual_html():
    """docs/manual.md -> numbered sections, each starting on a new page, with numbered figures."""
    md = (ROOT / "docs" / "manual.md").read_text()
    body = markdown.markdown(md, extensions=["tables", "fenced_code", "md_in_html", "sane_lists"])
    captions = dict(FIGURES)
    counter = [0]

    def figure(m):
        name = m.group(1)
        counter[0] += 1
        cap = html.escape(captions[name])
        return (f'<figure class="f-{name.split('.')[0]}"><img src="{img(name)}"><figcaption>Figure {counter[0]}. {cap}'
                f'</figcaption></figure>')

    def diagram(_):
        counter[0] += 1
        svg = (ROOT / "docs" / "diagram.svg").read_text()
        return (f'<figure class="diagram">{svg}<figcaption>Figure {counter[0]}. How the parts connect.'
                f'</figcaption></figure>')

    def pair(m):
        a = figure(re.match(r"(.*)", m.group(1)))
        b = figure(re.match(r"(.*)", m.group(2)))
        return f'<div class="pair">{a}{b}</div>'

    def grid(names, cols):
        figs = "".join(figure(re.match(r"(.*)", n)) for n in names.split(","))
        return f'<div class="grid g{cols}">{figs}</div>'

    def any_marker(m):
        if m.group(1) == "DIAGRAM":
            return diagram(m)
        if m.group(1).startswith("GRID3:"):
            return grid(m.group(1)[6:], 3)
        if m.group(1).startswith("GRID:"):
            return grid(m.group(1)[5:], 2)
        if m.group(1).startswith("PAIR:"):
            return pair(re.match(r"PAIR:([\w.]+):([\w.]+)", m.group(1)))
        return figure(re.match(r"FIG:([\w.]+)", m.group(1)))

    # One pass in document order so figures are numbered 1, 2, 3...
    body = re.sub(r"<p>@@(DIAGRAM|GRID3?:[\w.,]+|PAIR:[\w.:]+|FIG:[\w.]+)@@</p>", any_marker, body)
    body = re.sub(r"@@CHIP:(\w+):([^@]+)@@", r'<span class="chip \1">\2</span>', body)
    body = re.sub(r"<h1>(.*?)</h1>", r'<h2 class="sec">\1</h2>', body)
    sections = re.findall(r'<h2 class="sec">(.*?)</h2>', body)
    return body, sections, ""


def build():
    body, sections, appendix = manual_html()
    today = datetime.date.today().strftime("%B %d, %Y").replace(" 0", " ")
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><title>Tapat</title>
<meta name="author" content="Troy Lazaro"><style>{CSS}</style></head><body>
<section class="cover"><img class="logo" src="{img('logo.png', ROOT / 'logo')}" alt="Tapat">
<p class="kind">User manual</p>
<p class="one">A Chrome extension and web server for monitoring Google Forms quizzes</p>
<div class="meta"><b>INTE301 Systems Integration &amp; Architecture · Project 1</b><br>
Sir Rodel Villareaz<br>Troy Lazaro<br>{today}<br>
<a class="url" href="https://github.com/Troy-LL/tapat">github.com/Troy-LL/tapat</a></div>
<img src="{img('09_admin_quiz.png')}"></section>
<section class="readme">{body}</section>
{appendix}
</body></html>"""
    (ROOT / "docs" / "build").mkdir(exist_ok=True)
    tmp = ROOT / "docs" / "build" / "tapat.html"
    tmp.write_text(doc)
    footer = ('<div style="width:100%;margin:0 22mm;padding-top:4px;border-top:0.5pt solid #999;font-size:8pt;'
              'color:#444;display:flex;justify-content:space-between;font-family:Arial">'
              '<span>Tapat User Manual</span><span class="pageNumber"></span></div>')
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page()
        pg.goto(tmp.as_uri())
        pg.pdf(path=str(OUT), format="A4", print_background=True, display_header_footer=True,
               header_template="<div></div>", footer_template=footer,
               margin={"top": "22mm", "bottom": "24mm", "left": "22mm", "right": "22mm"})
        b.close()
    w = PdfWriter(clone_from=PdfReader(str(OUT)))
    w.add_metadata({"/Title": "Tapat", "/Author": "Troy Lazaro",
                    "/Subject": "INTE301 Systems Integration & Architecture · Project 1"})
    w.write(str(OUT))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
