"""
HTML email template builders.

Ported verbatim from the Next.js API routes:
- build_email      ← webapp/src/app/api/request-report/route.ts  (buildEmail)
- build_full_report ← webapp/src/app/api/send-report-now/route.ts (buildFullReport)
"""

from app.services.email_palette import email_palette

p = email_palette  # short alias used only inside this module


def escape_html(s: str) -> str:
    """Escape HTML entities to prevent XSS in email templates."""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#039;")
    )


def build_email(score: int, tips: list[str]) -> str:
    """Simple report email with score display and up to 7 tips.

    Score color: green (>=70), yellow (>=40), red (<40).
    """
    score_color = (
        p["success"] if score >= 70 else p["warning"] if score >= 40 else p["error"]
    )
    tip_items = "".join(
        f'<li style="margin-bottom:12px;color:{p["textBody"]};font-size:15px;line-height:1.5;">'
        f"{i + 1}. {escape_html(str(t))}</li>"
        for i, t in enumerate((tips or [])[:7])
    )

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:{p["background"]};font-family:-apple-system,BlinkMacSystemFont,Inter,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td align="center" style="padding:48px 20px;">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">
  <tr><td style="text-align:center;padding-bottom:32px;">
    <span style="font-size:20px;font-weight:700;color:{p["textHeading"]};">alpo.ai</span>
  </td></tr>
  <tr><td style="background:{p["cardBg"]};border:1.5px solid {p["cardBorder"]};border-radius:12px;padding:40px 36px;">
    <p style="margin:0 0 8px;font-size:13px;color:{p["textTertiary"]};text-transform:uppercase;letter-spacing:0.05em;">Your conversion audit</p>
    <div style="text-align:center;margin:24px 0;">
      <span style="font-size:80px;font-weight:800;color:{score_color};line-height:1;">{score}</span>
      <span style="font-size:20px;color:{p["textTertiary"]};">/100</span>
    </div>
    <h2 style="margin:0 0 16px;font-size:18px;font-weight:600;color:{p["textHeading"]};">Your fix list:</h2>
    <ul style="margin:0;padding:0;list-style:none;">
      {tip_items}
    </ul>
    <div style="margin-top:32px;padding:24px;background:{p["promoBg"]};border-radius:8px;text-align:center;">
      <p style="margin:0 0 4px;font-size:15px;color:{p["textHeading"]};font-weight:600;">Want weekly monitoring + AI rewrites?</p>
      <p style="margin:0 0 16px;font-size:14px;color:{p["textMuted"]};">Get alerted when your score drops and get AI fixes automatically.</p>
      <a href="https://alpo.ai" style="display:inline-block;padding:12px 28px;background:{p["brandCta"]};color:{p["cardBg"]};font-size:15px;font-weight:600;text-decoration:none;border-radius:8px;">Upgrade to Pro — $49/mo</a>
    </div>
  </td></tr>
  <tr><td style="text-align:center;padding-top:24px;">
    <p style="margin:0;font-size:12px;color:{p["textTertiary"]};">alpo.ai · alpo.ai</p>
  </td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Full 18-dimension report
# ---------------------------------------------------------------------------

category_labels: dict[str, str] = {
    "pageSpeed": "Page Speed",
    "images": "Product Images",
    "socialProof": "Reviews & Social Proof",
    "checkout": "Checkout & Payments",
    "mobileCta": "Mobile CTA & UX",
    "title": "Title & SEO",
    "aiDiscoverability": "AI Discoverability",
    "structuredData": "Schema Markup",
    "pricing": "Pricing Psychology",
    "description": "Description Quality",
    "shipping": "Shipping Transparency",
    "crossSell": "Cross-Sell & Upsell",
    "trust": "Trust & Guarantees",
    "socialCommerce": "Social Commerce",
    "sizeGuide": "Size & Fit",
    "variantUx": "Variant UX",
    "accessibility": "Accessibility",
    "contentFreshness": "Content Freshness",
}

impact_levels: dict[str, str] = {
    "pageSpeed": "🔴 Very High",
    "images": "🔴 Very High",
    "socialProof": "🔴 Very High",
    "checkout": "🔴 Very High",
    "mobileCta": "🟠 High",
    "title": "🟠 High",
    "aiDiscoverability": "🟠 High",
    "structuredData": "🟠 High",
    "pricing": "🟠 High",
    "description": "🟡 Medium-High",
    "shipping": "🟡 Medium-High",
    "crossSell": "🟡 Medium-High",
    "trust": "🟢 Medium",
    "socialCommerce": "🟢 Medium",
    "sizeGuide": "🟢 Medium",
    "variantUx": "🟢 Medium",
    "accessibility": "⚪ Low-Medium",
    "contentFreshness": "⚪ Low-Medium",
}


def build_full_report(
    score: int, tips: list[str], categories: dict[str, int]
) -> str:
    """Full 18-dimension report email with sorted category table (worst-first),
    score colors, impact levels, tip list (up to 20), and promo CTA.
    """
    score_color = (
        p["success"] if score >= 70 else p["warning"] if score >= 40 else p["error"]
    )

    # Sort categories worst-first (ascending score)
    sorted_cats = sorted((categories or {}).items(), key=lambda kv: kv[1])

    category_rows = "".join(
        _category_row(key, int(val) if val is not None else 0)
        for key, val in sorted_cats
    )

    tip_items = "".join(
        f'<li style="margin-bottom:10px;color:{p["textBody"]};font-size:14px;line-height:1.5;">'
        f"{i + 1}. {escape_html(str(t))}</li>"
        for i, t in enumerate((tips or [])[:20])
    )

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:{p["background"]};font-family:-apple-system,BlinkMacSystemFont,Inter,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td align="center" style="padding:48px 20px;">
<table width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;">
  <tr><td style="text-align:center;padding-bottom:32px;">
    <span style="font-size:20px;font-weight:700;color:{p["textHeading"]};">alpo.ai</span>
    <span style="font-size:12px;color:{p["textSecondary"]};margin-left:8px;">Priority Report</span>
  </td></tr>
  <tr><td style="background:{p["cardBg"]};border:1.5px solid {p["cardBorder"]};border-radius:12px;padding:40px 36px;">
    <div style="text-align:center;margin-bottom:32px;">
      <p style="margin:0 0 8px;font-size:13px;color:{p["textTertiary"]};text-transform:uppercase;letter-spacing:0.05em;">Overall Score</p>
      <span style="font-size:72px;font-weight:800;color:{score_color};line-height:1;">{score}</span>
      <span style="font-size:20px;color:{p["textTertiary"]};">/100</span>
    </div>

    <h2 style="margin:0 0 16px;font-size:18px;font-weight:700;color:{p["textHeading"]};">All 20 Dimensions Scored</h2>
    <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid {p["cardBorder"]};border-radius:8px;overflow:hidden;margin-bottom:32px;">
      <tr style="background:{p["tableHeaderBg"]};">
        <th style="padding:10px 12px;text-align:left;font-size:12px;font-weight:600;color:{p["textLabel"]};text-transform:uppercase;letter-spacing:0.05em;">Dimension</th>
        <th style="padding:10px 12px;text-align:center;font-size:12px;font-weight:600;color:{p["textLabel"]};text-transform:uppercase;">Score</th>
        <th style="padding:10px 12px;text-align:left;font-size:12px;font-weight:600;color:{p["textLabel"]};text-transform:uppercase;">Revenue Impact</th>
      </tr>
      {category_rows}
    </table>

    <h2 style="margin:0 0 16px;font-size:18px;font-weight:700;color:{p["textHeading"]};">Your Fix List</h2>
    <ul style="margin:0;padding:0;list-style:none;">
      {tip_items}
    </ul>

    <div style="margin-top:32px;padding:24px;background:{p["promoBg"]};border-radius:8px;text-align:center;">
      <p style="margin:0 0 4px;font-size:15px;color:{p["textHeading"]};font-weight:600;">Want weekly monitoring?</p>
      <p style="margin:0 0 16px;font-size:14px;color:{p["textMuted"]};">Get alerted when your scores drop. Track all 20 dimensions over time.</p>
      <a href="https://alpo.ai" style="display:inline-block;padding:12px 28px;background:{p["brandCta"]};color:{p["cardBg"]};font-size:15px;font-weight:600;text-decoration:none;border-radius:8px;">Coming Soon — Join Waitlist</a>
    </div>
  </td></tr>
  <tr><td style="text-align:center;padding-top:24px;">
    <p style="color:{p["textSecondary"]};font-size:12px;">alpo.ai by alpo.ai — Stop losing sales to fixable page issues.</p>
  </td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def _category_row(key: str, cat_score: int) -> str:
    """Build a single <tr> for the category table."""
    color = (
        p["success"]
        if cat_score >= 70
        else p["warning"]
        if cat_score >= 40
        else p["error"]
    )
    label = category_labels.get(key, key)
    impact = impact_levels.get(key, "Medium")
    return (
        f"<tr>"
        f'<td style="padding:10px 12px;border-bottom:1px solid {p["tableBorder"]};font-size:14px;color:{p["textBody"]};">{escape_html(label)}</td>'
        f'<td style="padding:10px 12px;border-bottom:1px solid {p["tableBorder"]};text-align:center;">'
        f'<span style="font-weight:700;color:{color};font-size:16px;">{cat_score}</span>'
        f'<span style="color:{p["textSecondary"]};font-size:12px;">/100</span></td>'
        f'<td style="padding:10px 12px;border-bottom:1px solid {p["tableBorder"]};font-size:12px;color:{p["textLabel"]};">{impact}</td>'
        f"</tr>"
    )
