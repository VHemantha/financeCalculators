"""
Blog blueprint — auto-discovers HTML files in templates/blogs/ and serves them.
Adding a new .html file to templates/blogs/ automatically makes it appear on
the /blog dashboard with no code changes needed.
"""
import os
import re

from flask import Blueprint, abort, render_template

blog_bp = Blueprint("blog", __name__)

_BLOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "templates", "blogs")


def _get_posts():
    """Scan templates/blogs/ and extract title + description from each file."""
    posts = []
    try:
        filenames = sorted(os.listdir(_BLOGS_DIR), reverse=True)
    except FileNotFoundError:
        return posts

    for fname in filenames:
        if not fname.endswith(".html"):
            continue
        slug = fname[:-5]
        path = os.path.join(_BLOGS_DIR, fname)
        with open(path, encoding="utf-8") as f:
            html = f.read()

        title_m = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_m.group(1).strip() if title_m else slug.replace("-", " ").title()

        desc_m = re.search(
            r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        description = desc_m.group(1).strip() if desc_m else ""

        posts.append({"slug": slug, "title": title, "description": description})

    return posts


@blog_bp.route("/blog")
def blog_index():
    posts = _get_posts()
    return render_template("blog_index.html", posts=posts)


@blog_bp.route("/blog/<slug>")
def blog_post(slug):
    if "/" in slug or "\\" in slug or ".." in slug:
        abort(404)
    try:
        return render_template(f"blogs/{slug}.html")
    except Exception:
        abort(404)
