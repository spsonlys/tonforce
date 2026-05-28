#!/usr/bin/env python3
"""
TonForce Blog Builder
─────────────────────
Reads Markdown posts from blog/posts/, en/blog/posts/, ua/blog/posts/
Generates HTML pages, blog index pages, RSS feeds, and updated sitemap.

Frontmatter format (set by Decap CMS):
---
title: "Post Title"
lead: "Short summary"
date: 2026-05-28T00:00:00.000+03:00
category: "announcements"
cover_emoji: "🚀"
cover_image: "/images/blog/cover.png"  # optional
read_time: 5
meta_description: "SEO description"
published: true
---
"""

import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape


def parse_frontmatter(text):
    """Parse YAML frontmatter at the start of a Markdown file.

    Returns (metadata_dict, body_text). If no frontmatter, returns ({}, text).
    """
    if not text.startswith("---"):
        return {}, text
    # Find closing ---
    parts = text.split("\n---", 1)
    if len(parts) < 2:
        return {}, text
    # parts[0] starts with "---\n..."
    yaml_block = parts[0][3:].lstrip("\n")
    body = parts[1].lstrip("\n")
    try:
        metadata = yaml.safe_load(yaml_block) or {}
    except yaml.YAMLError:
        metadata = {}
    return metadata, body

# ─── Configuration ─────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = Path(__file__).parent / "templates"
LEGACY_CONFIG = Path(__file__).parent / "legacy_posts.json"

SITE_URL = "https://tonforce.app"

LANGUAGES = {
    "ru": {"path": "blog", "html_lang": "ru", "og_locale": "ru_RU"},
    "en": {"path": "en/blog", "html_lang": "en", "og_locale": "en_US"},
    "ua": {"path": "ua/blog", "html_lang": "uk", "og_locale": "uk_UA"},
}

# i18n labels — translated UI strings per language
I18N = {
    "ru": {
        "blog_title": "Блог TonForce",
        "blog_subtitle": "Новости, обновления и аналитика платформы",
        "back_to_blog": "← Назад к блогу",
        "share_label": "Поделиться статьёй",
        "share_copy": "🔗 Скопировать ссылку",
        "share_copied": "✓ Скопировано",
        "comments_title": "💬 Комментарии",
        "related_posts": "Похожие статьи",
        "read_more": "Читать дальше",
        "launch_btn": "🚀 Запустить",
        "min_label": "мин",
        "nav_about": "О проекте",
        "nav_security": "Безопасность",
        "nav_levels": "Уровни",
        "nav_blog": "Блог",
        "footer_about": "О проекте",
        "footer_security": "Безопасность",
        "footer_blog": "Блог",
        "footer_brand": "TonForce",
        "footer_copy": "© 2026 TonForce. Decentralized Matrix on TON Blockchain.",
        "no_posts": "Скоро здесь появятся статьи.",
        "rss_description": "Новости и обновления децентрализованной матричной платформы TonForce",
        "categories": {
            "announcements": "Анонс",
            "guides": "Гайд",
            "security": "Безопасность",
            "case-studies": "Кейсы",
            "analytics": "Аналитика",
            "success-stories": "Истории успеха",
        },
        "months": ["января", "февраля", "марта", "апреля", "мая", "июня",
                   "июля", "августа", "сентября", "октября", "ноября", "декабря"],
    },
    "en": {
        "blog_title": "TonForce Blog",
        "blog_subtitle": "News, updates and platform analytics",
        "back_to_blog": "← Back to blog",
        "share_label": "Share article",
        "share_copy": "🔗 Copy link",
        "share_copied": "✓ Copied",
        "comments_title": "💬 Comments",
        "related_posts": "Related posts",
        "read_more": "Read more",
        "launch_btn": "🚀 Launch",
        "min_label": "min",
        "nav_about": "About",
        "nav_security": "Security",
        "nav_levels": "Levels",
        "nav_blog": "Blog",
        "footer_about": "About",
        "footer_security": "Security",
        "footer_blog": "Blog",
        "footer_brand": "TonForce",
        "footer_copy": "© 2026 TonForce. Decentralized Matrix on TON Blockchain.",
        "no_posts": "Posts will appear here soon.",
        "rss_description": "News and updates from the TonForce decentralized matrix platform",
        "categories": {
            "announcements": "Announcement",
            "guides": "Guide",
            "security": "Security",
            "case-studies": "Case studies",
            "analytics": "Analytics",
            "success-stories": "Success stories",
        },
        "months": ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"],
    },
    "ua": {
        "blog_title": "Блог TonForce",
        "blog_subtitle": "Новини, оновлення та аналітика платформи",
        "back_to_blog": "← Назад до блогу",
        "share_label": "Поділитися статтею",
        "share_copy": "🔗 Копіювати посилання",
        "share_copied": "✓ Скопійовано",
        "comments_title": "💬 Коментарі",
        "related_posts": "Схожі статті",
        "read_more": "Читати далі",
        "launch_btn": "🚀 Запустити",
        "min_label": "хв",
        "nav_about": "Про проєкт",
        "nav_security": "Безпека",
        "nav_levels": "Рівні",
        "nav_blog": "Блог",
        "footer_about": "Про проєкт",
        "footer_security": "Безпека",
        "footer_blog": "Блог",
        "footer_brand": "TonForce",
        "footer_copy": "© 2026 TonForce. Decentralized Matrix on TON Blockchain.",
        "no_posts": "Незабаром тут з'являться статті.",
        "rss_description": "Новини та оновлення децентралізованої матричної платформи TonForce",
        "categories": {
            "announcements": "Анонс",
            "guides": "Гайд",
            "security": "Безпека",
            "case-studies": "Кейси",
            "analytics": "Аналітика",
            "success-stories": "Історії успіху",
        },
        "months": ["січня", "лютого", "березня", "квітня", "травня", "червня",
                   "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"],
    },
}


# ─── Helpers ───────────────────────────────────────────────────────

def format_date(date_obj, lang):
    """Format datetime as '25 мая 2026' / '25 May 2026' / '25 травня 2026'."""
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.fromisoformat(date_obj.replace("Z", "+00:00"))
        except ValueError:
            return date_obj
    return f"{date_obj.day} {I18N[lang]['months'][date_obj.month - 1]} {date_obj.year}"


def iso_date(date_obj):
    """Return ISO 8601 string for datetime field in schema/OG."""
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.fromisoformat(date_obj.replace("Z", "+00:00"))
        except ValueError:
            return date_obj
    return date_obj.strftime("%Y-%m-%dT%H:%M:%SZ")


def rss_date(date_obj):
    """RFC 822 date for RSS."""
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.fromisoformat(date_obj.replace("Z", "+00:00"))
        except ValueError:
            return date_obj
    return date_obj.strftime("%a, %d %b %Y %H:%M:%S +0000")


def parse_date(value):
    """Return datetime from various input forms."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


def share_text(title, lang):
    """URL-encoded share text."""
    return quote(title)


# ─── Load posts ────────────────────────────────────────────────────

def load_posts_for_lang(lang_code):
    """Load all .md posts for a language (Markdown + legacy) and sort by date desc."""
    lang_cfg = LANGUAGES[lang_code]
    posts_dir = ROOT / lang_cfg["path"] / "posts"
    posts = []

    # 1. Markdown posts (from Decap CMS)
    if posts_dir.exists():
        for md_file in posts_dir.glob("*.md"):
            try:
                text = md_file.read_text(encoding="utf-8")
                meta, body = parse_frontmatter(text)
                if meta.get("published") is False:
                    continue
                slug = md_file.stem
                # Convert Markdown body → HTML
                html_body = markdown.markdown(
                    body,
                    extensions=["extra", "tables", "nl2br", "sane_lists"],
                )
                posts.append({
                    "slug": slug,
                    "title": meta.get("title", "Untitled"),
                    "lead": meta.get("lead", ""),
                    "date": parse_date(meta.get("date", datetime.now())),
                    "category": meta.get("category", "announcements"),
                    "cover_emoji": meta.get("cover_emoji", "📝"),
                    "cover_image": meta.get("cover_image"),
                    "read_time": meta.get("read_time", 5),
                    "meta_description": meta.get("meta_description", meta.get("lead", "")),
                    "body_html": html_body,
                    "is_legacy": False,
                })
            except Exception as e:
                print(f"⚠️  Error parsing {md_file}: {e}", file=sys.stderr)

    # 2. Legacy posts (existing HTML files, metadata from JSON)
    if LEGACY_CONFIG.exists():
        with open(LEGACY_CONFIG, "r", encoding="utf-8") as f:
            legacy_data = json.load(f)
        for post in legacy_data.get(lang_code, []):
            post["date"] = parse_date(post["date"])
            post["is_legacy"] = True
            post["meta_description"] = post.get("meta_description", post.get("lead", ""))
            posts.append(post)

    # Sort by date desc
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


# ─── Render ────────────────────────────────────────────────────────

def render_post(env, post, lang_code, all_posts):
    """Render single post HTML."""
    lang_cfg = LANGUAGES[lang_code]
    labels = I18N[lang_code]
    tpl = env.get_template("post.html.j2")

    # Related: 2 newest posts excluding this one
    related = [p for p in all_posts if p["slug"] != post["slug"]][:2]

    blog_base = f"/{lang_cfg['path']}/"
    post_url = f"{SITE_URL}{blog_base}{post['slug']}.html"

    # hreflang alternates
    alt_links = {
        "ru": f"{SITE_URL}/blog/{post['slug']}.html",
        "en": f"{SITE_URL}/en/blog/{post['slug']}.html",
        "ua": f"{SITE_URL}/ua/blog/{post['slug']}.html",
    }

    return tpl.render(
        post=post,
        lang=lang_code,
        lang_cfg=lang_cfg,
        labels=labels,
        related=related,
        site_url=SITE_URL,
        blog_base=blog_base,
        post_url=post_url,
        alt_links=alt_links,
        category_label=labels["categories"].get(post["category"], post["category"]),
        formatted_date=format_date(post["date"], lang_code),
        iso_published=iso_date(post["date"]),
        share_text_encoded=share_text(post["title"], lang_code),
    )


def render_index(env, posts, lang_code):
    """Render blog index page."""
    lang_cfg = LANGUAGES[lang_code]
    labels = I18N[lang_code]
    tpl = env.get_template("blog_index.html.j2")
    blog_base = f"/{lang_cfg['path']}/"

    rendered_posts = []
    for p in posts:
        rendered_posts.append({
            **p,
            "category_label": labels["categories"].get(p["category"], p["category"]),
            "formatted_date": format_date(p["date"], lang_code),
        })

    return tpl.render(
        posts=rendered_posts,
        lang=lang_code,
        lang_cfg=lang_cfg,
        labels=labels,
        site_url=SITE_URL,
        blog_base=blog_base,
    )


def render_rss(env, posts, lang_code):
    """Render RSS feed."""
    lang_cfg = LANGUAGES[lang_code]
    labels = I18N[lang_code]
    tpl = env.get_template("rss.xml.j2")
    blog_base = f"/{lang_cfg['path']}/"

    rss_posts = []
    for p in posts[:20]:  # last 20
        rss_posts.append({
            **p,
            "url": f"{SITE_URL}{blog_base}{p['slug']}.html",
            "rss_date": rss_date(p["date"]),
        })

    return tpl.render(
        posts=rss_posts,
        lang=lang_code,
        lang_cfg=lang_cfg,
        labels=labels,
        site_url=SITE_URL,
        blog_base=blog_base,
        build_date=datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000"),
    )


# ─── Sitemap ───────────────────────────────────────────────────────

def build_sitemap(all_posts_by_lang):
    """Generate sitemap.xml from static pages + posts."""
    static_urls = [
        ("/", "1.0", "weekly"),
        ("/en/", "0.9", "weekly"),
        ("/ua/", "0.9", "weekly"),
        ("/blog/", "0.8", "daily"),
        ("/en/blog/", "0.7", "daily"),
        ("/ua/blog/", "0.7", "daily"),
    ]

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for path, priority, freq in static_urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{SITE_URL}{path}</loc>")
        lines.append(f"    <lastmod>{today}</lastmod>")
        lines.append(f"    <changefreq>{freq}</changefreq>")
        lines.append(f"    <priority>{priority}</priority>")
        lines.append("  </url>")

    for lang_code, posts in all_posts_by_lang.items():
        blog_base = f"/{LANGUAGES[lang_code]['path']}/"
        for post in posts:
            url = f"{SITE_URL}{blog_base}{post['slug']}.html"
            lastmod = post["date"].strftime("%Y-%m-%d") if isinstance(post["date"], datetime) else today
            lines.append("  <url>")
            lines.append(f"    <loc>{url}</loc>")
            lines.append(f"    <lastmod>{lastmod}</lastmod>")
            lines.append("    <changefreq>monthly</changefreq>")
            lines.append("    <priority>0.6</priority>")
            lines.append("  </url>")

    lines.append("</urlset>")
    return "\n".join(lines)


# ─── Main ──────────────────────────────────────────────────────────

def main():
    print("🔨 TonForce Blog Builder")
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    all_posts_by_lang = {}

    for lang_code in LANGUAGES.keys():
        lang_cfg = LANGUAGES[lang_code]
        out_dir = ROOT / lang_cfg["path"]
        out_dir.mkdir(parents=True, exist_ok=True)

        posts = load_posts_for_lang(lang_code)
        all_posts_by_lang[lang_code] = posts
        print(f"\n  [{lang_code.upper()}] Found {len(posts)} posts")

        # Render each non-legacy post
        for post in posts:
            if post["is_legacy"]:
                continue
            out_file = out_dir / f"{post['slug']}.html"
            html = render_post(env, post, lang_code, posts)
            out_file.write_text(html, encoding="utf-8")
            print(f"    ✓ {out_file.relative_to(ROOT)}")

        # Render blog index
        index_html = render_index(env, posts, lang_code)
        (out_dir / "index.html").write_text(index_html, encoding="utf-8")
        print(f"    ✓ {(out_dir / 'index.html').relative_to(ROOT)}")

        # Render RSS
        rss_xml = render_rss(env, posts, lang_code)
        (out_dir / "rss.xml").write_text(rss_xml, encoding="utf-8")
        print(f"    ✓ {(out_dir / 'rss.xml').relative_to(ROOT)}")

    # Build sitemap
    sitemap = build_sitemap(all_posts_by_lang)
    (ROOT / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    print(f"\n  ✓ sitemap.xml updated")

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
