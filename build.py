"""Build the Notes pages of the homepage from _posts/*.md.

Run `python3 build.py` after adding or editing a post. It writes notes/<slug>.html
for each post, notes/index.html with the full list, and refreshes the block between
the NOTES markers in index.html. No third-party packages are needed.

Post format: a file named YYYY-MM-DD-slug.md that starts with

    ---
    title: Post title
    date: YYYY-MM-DD
    ---

followed by the body in a small Markdown subset: paragraphs, **bold**, *italic*,
[links](url), `code`, images on their own line as ![alt](src), and "- " lists.
"""

import html
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POSTS = ROOT / "_posts"
NOTES = ROOT / "notes"
INDEX = ROOT / "index.html"
HOME_COUNT = 3
START, END = "<!-- NOTES:START -->", "<!-- NOTES:END -->"

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="stylesheet" href="../assets/css/site.css">
</head>
<body>
<header class="site-header">
  <div class="wrap">
    <a class="brand" href="../">Zixuan Qi</a>
    <nav class="nav">
      <a href="../#projects">Projects</a>
      <a href="../#testbed">Test houses</a>
      <a href="./">Notes</a>
      <a href="../#people">People</a>
    </nav>
  </div>
</header>

<main class="wrap">
{body}
</main>

<footer>
  <div class="wrap">
    <p>Zixuan Qi · <a href="mailto:qizixuan@tamu.edu">qizixuan@tamu.edu</a> · <a href="https://github.com/mrkey4real">GitHub</a> · <a href="https://hvac.engr.tamu.edu/tamscht">TAM-SCHT</a></p>
  </div>
</footer>
</body>
</html>
"""


def inline(text):
    """Escape text, then apply the inline Markdown subset."""
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    return text


def render_body(markdown):
    """Turn the Markdown subset into HTML blocks."""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", markdown.strip()) if b.strip()]
    out = []
    for block in blocks:
        lines = block.splitlines()
        image = re.fullmatch(r"!\[([^\]]*)\]\(([^)\s]+)\)", block)
        if image:
            alt, src = html.escape(image.group(1)), html.escape(image.group(2))
            out.append(f'<figure><img src="{src}" alt="{alt}" loading="lazy"></figure>')
        elif all(line.startswith("- ") for line in lines):
            items = "".join(f"<li>{inline(line[2:])}</li>" for line in lines)
            out.append(f"<ul>{items}</ul>")
        else:
            out.append(f"<p>{inline(' '.join(lines))}</p>")
    return "\n".join(out)


def read_post(path):
    """Parse one post file into a dict. Fails loudly on a malformed file."""
    match = re.fullmatch(r"(\d{4}-\d{2}-\d{2})-([a-z0-9-]+)\.md", path.name)
    if not match:
        raise ValueError(f"{path.name}: file name must be YYYY-MM-DD-slug.md")
    raw = path.read_text(encoding="utf-8")
    parts = re.match(r"---\n(.*?)\n---\n(.*)", raw, re.S)
    if not parts:
        raise ValueError(f"{path.name}: missing front matter")
    meta = dict(line.split(":", 1) for line in parts.group(1).splitlines() if line.strip())
    meta = {k.strip(): v.strip() for k, v in meta.items()}
    if "title" not in meta:
        raise ValueError(f"{path.name}: front matter needs a title")
    day = date.fromisoformat(meta.get("date", match.group(1)))
    body = parts.group(2)
    first = body.strip().split("\n\n")[0].replace("\n", " ")
    first = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", first)  # keep link text, drop targets
    first = re.sub(r"[*`]", "", first)
    return {
        "slug": f"{match.group(1)}-{match.group(2)}",
        "title": meta["title"],
        "date": day,
        "html": render_body(body),
        "excerpt": first if len(first) <= 160 else first[:157].rsplit(" ", 1)[0] + "...",
    }


def nice_date(day):
    return f"{day:%b} {day.day}, {day.year}"


def list_items(posts, prefix):
    return "\n".join(
        f'    <li><a href="{prefix}{p["slug"]}.html">{html.escape(p["title"])}</a>'
        f' <span class="when">{nice_date(p["date"])}</span>'
        f'<p>{html.escape(p["excerpt"])}</p></li>'
        for p in posts
    )


def main():
    posts = sorted((read_post(p) for p in POSTS.glob("*.md")), key=lambda p: (p["date"], p["slug"]), reverse=True)
    NOTES.mkdir(exist_ok=True)
    for old in NOTES.glob("*.html"):
        old.unlink()

    for p in posts:
        body = (
            f'  <article class="post">\n    <p class="when">{nice_date(p["date"])}</p>\n'
            f'    <h1>{html.escape(p["title"])}</h1>\n    <div class="prose">\n{p["html"]}\n    </div>\n'
            f'  </article>\n  <a class="back" href="./">← All notes</a>'
        )
        (NOTES / f'{p["slug"]}.html').write_text(
            PAGE.format(title=f'{html.escape(p["title"])} · Zixuan Qi',
                        description=html.escape(p["excerpt"]), body=body),
            encoding="utf-8",
        )

    listing = (
        '  <div class="page-head">\n    <h1>Notes</h1>\n'
        "    <p>What I'm working on, and the occasional complaint.</p>\n  </div>\n"
        f'  <ul class="notes">\n{list_items(posts, "")}\n  </ul>'
    )
    (NOTES / "index.html").write_text(
        PAGE.format(title="Notes · Zixuan Qi",
                    description="Short notes on what Zixuan Qi is working on.", body=listing),
        encoding="utf-8",
    )

    page = INDEX.read_text(encoding="utf-8")
    if START not in page or END not in page:
        raise ValueError("index.html is missing the NOTES markers")
    block = f'{START}\n  <ul class="notes">\n{list_items(posts[:HOME_COUNT], "notes/")}\n  </ul>\n  {END}'
    page = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, page, flags=re.S)
    INDEX.write_text(page, encoding="utf-8")
    print(f"Built {len(posts)} notes.")


if __name__ == "__main__":
    main()
