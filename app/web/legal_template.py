"""Shared HTML shell for legal pages."""

from __future__ import annotations

from html import escape
from typing import Optional


def render_legal_page(
    *,
    title: str,
    body_html: str,
    active: Optional[str] = None,
    meta_description: Optional[str] = None,
) -> str:
    """Wrap legal content in a responsive, branded layout."""
    desc = meta_description or title
    nav = [
        ("Legal centre", "/legal", "legal"),
        ("Privacy Policy", "/privacy-policy", "privacy"),
        ("Terms & Conditions", "/terms-and-conditions", "terms"),
    ]
    nav_li = []
    for label, href, slug in nav:
        is_active = slug == active
        cls = " active" if is_active else ""
        nav_li.append(
            f'<li><a class="nav-link{cls}" href="{escape(href)}">{escape(label)}</a></li>'
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="description" content="{escape(desc)}" />
  <title>{escape(title)} · Dely Cart</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,600;0,9..40,700;1,9..40,400&display=swap" rel="stylesheet" />
  <style>
    :root {{
      --bg: #f0f7ff;
      --card: #ffffff;
      --text: #0f172a;
      --muted: #64748b;
      --brand: #1d4ed8;
      --brand-dark: #0b3b8f;
      --border: #dbeafe;
      --radius: 16px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "DM Sans", system-ui, -apple-system, sans-serif;
      font-optical-sizing: auto;
      background: var(--bg);
      color: var(--text);
      line-height: 1.65;
      min-height: 100vh;
    }}
    .topbar {{
      background: linear-gradient(135deg, #0b3b8f 0%, #1d4ed8 100%);
      color: #fff;
      padding: 1.25rem 1.5rem;
      box-shadow: 0 4px 24px rgba(13, 59, 143, 0.25);
    }}
    .topbar-inner {{
      max-width: 52rem;
      margin: 0 auto;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
    }}
    .brand {{
      font-weight: 700;
      font-size: 1.25rem;
      letter-spacing: -0.02em;
      color: inherit;
      text-decoration: none;
    }}
    .brand span {{ opacity: 0.9; font-weight: 600; font-size: 0.9rem; }}
    nav ul {{
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-wrap: wrap;
      gap: 0.35rem 1rem;
    }}
    .nav-link {{
      color: rgba(255,255,255,0.88);
      text-decoration: none;
      font-weight: 600;
      font-size: 0.9rem;
      padding: 0.35rem 0;
      border-bottom: 2px solid transparent;
    }}
    .nav-link:hover {{ color: #fff; border-bottom-color: rgba(255,255,255,0.5); }}
    .nav-link.active {{ color: #fff; border-bottom-color: #fff; }}
    main {{
      max-width: 52rem;
      margin: 0 auto;
      padding: 1.75rem 1.25rem 3rem;
    }}
    .card {{
      background: var(--card);
      border-radius: var(--radius);
      border: 1px solid var(--border);
      padding: 1.75rem 1.5rem;
      box-shadow: 0 8px 30px rgba(15, 23, 42, 0.06);
    }}
    @media (min-width: 640px) {{
      .card {{ padding: 2rem 2.25rem; }}
    }}
    .prose h1 {{
      margin: 0 0 0.5rem;
      font-size: 1.75rem;
      font-weight: 700;
      color: var(--brand-dark);
      letter-spacing: -0.02em;
    }}
    .prose .lede {{
      color: var(--muted);
      font-weight: 600;
      margin: 0 0 1.5rem;
      font-size: 1rem;
    }}
    .prose h2 {{
      margin: 1.75rem 0 0.65rem;
      font-size: 1.1rem;
      font-weight: 700;
      color: var(--brand-dark);
    }}
    .prose h2:first-child {{ margin-top: 0; }}
    .prose p {{ margin: 0 0 0.85rem; }}
    .prose ul {{ margin: 0 0 1rem; padding-left: 1.25rem; }}
    .prose li {{ margin-bottom: 0.35rem; }}
    .prose a {{ color: var(--brand); font-weight: 600; }}
    .prose .muted {{ color: var(--muted); font-size: 0.95rem; }}
    .tiles {{
      display: grid;
      gap: 1rem;
      grid-template-columns: 1fr;
    }}
    @media (min-width: 560px) {{
      .tiles {{ grid-template-columns: 1fr 1fr; }}
    }}
    .tile {{
      display: block;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 1.25rem 1.35rem;
      text-decoration: none;
      color: inherit;
      transition: box-shadow 0.2s, border-color 0.2s;
    }}
    .tile:hover {{
      border-color: var(--brand);
      box-shadow: 0 12px 28px rgba(29, 78, 216, 0.12);
    }}
    .tile h2 {{
      margin: 0 0 0.35rem;
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--brand-dark);
    }}
    .tile p {{ margin: 0; color: var(--muted); font-size: 0.92rem; font-weight: 600; }}
    .tile .go {{ margin-top: 0.75rem; color: var(--brand); font-weight: 700; font-size: 0.88rem; }}
    footer {{
      max-width: 52rem;
      margin: 0 auto;
      padding: 0 1.25rem 2rem;
      text-align: center;
      color: var(--muted);
      font-size: 0.85rem;
      font-weight: 600;
    }}
    footer a {{ color: var(--brand); }}
  </style>
</head>
<body>
  <header class="topbar">
    <div class="topbar-inner">
      <a class="brand" href="/legal">Dely Cart <span>Legal</span></a>
      <nav aria-label="Legal documents">
        <ul>
          {"".join(nav_li)}
        </ul>
      </nav>
    </div>
  </header>
  <main>
    <div class="card prose">
      {body_html}
    </div>
  </main>
  <footer>
    <p>© Foodistic Marketing Services Pvt. Ltd. · <a href="mailto:delycart.in@gmail.com">delycart.in@gmail.com</a></p>
  </footer>
</body>
</html>"""


def render_legal_index() -> str:
    body = """
    <h1>Legal centre</h1>
    <p class="lede">Policies for the Dely Cart B2B platform and mobile application.</p>
    <div class="tiles">
      <a class="tile" href="/privacy-policy">
        <h2>Privacy Policy</h2>
        <p>How we collect, use, store, and protect your personal information.</p>
        <div class="go">Read policy →</div>
      </a>
      <a class="tile" href="/terms-and-conditions">
        <h2>Terms &amp; Conditions</h2>
        <p>Rules for using our platform, orders, and business accounts.</p>
        <div class="go">Read terms →</div>
      </a>
    </div>
    <p class="muted" style="margin-top:1.75rem">The complete Terms of Use text is also available inside the Dely Cart app under Help &amp; Support.</p>
    """
    return render_legal_page(
        title="Legal centre",
        body_html=body,
        active="legal",
        meta_description="Dely Cart legal documents: Privacy Policy and Terms & Conditions.",
    )
