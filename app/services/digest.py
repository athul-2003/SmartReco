"""
Phase 6 bonus (FR-6): the daily digest job's logic - runs the same
recommendation pipeline used by the manual refresh button (agent/graph.py)
for every active user, and emails each of them the result. Kept separate
from scheduler.py so tests can invoke run_daily_digest() directly against a
real Session, without needing to run the actual APScheduler loop (per
CLAUDE.md's testing bar for this phase).
"""

import logging
from html import escape

from sqlmodel import Session, select

from app.agent.graph import run_recommendation_graph
from app.config import get_settings
from app.models.event import Event
from app.models.product import Product
from app.models.user import User
from app.services.email import send_email
from app.services.ui import category_cover

logger = logging.getLogger(__name__)

DIGEST_SUBJECT = "Your SmartReco picks for today"

# Email clients can't load the app's CSS, so this mirrors category_cover's
# 6-tone palette (app/services/ui.py) as fixed hex values, keyed by the
# same "cover-N" class it returns - the same category gets the same accent
# color in the email as it does on a product card in the app.
_TONE_HEX = {
    "cover-0": "#1e3a8a",
    "cover-1": "#006f66",
    "cover-2": "#6e2c00",
    "cover-3": "#3a3f52",
    "cover-4": "#264191",
    "cover-5": "#005049",
}


def _active_user_ids(session: Session) -> list[int]:
    """Active = has tracked at least one behavioral event - nothing to
    recommend from otherwise, matching the same premise as the cold-start
    empty state on GET /recommendations."""
    return list(session.exec(select(Event.user_id).distinct()).all())


def _ordered_products(session: Session, product_ids: list[int]) -> list[Product]:
    products = session.exec(select(Product).where(Product.id.in_(product_ids))).all()
    by_id = {p.id: p for p in products}
    return [by_id[pid] for pid in product_ids if pid in by_id]


def _dashboard_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/recommendations"


def _course_url(base_url: str, product: Product) -> str:
    return f"{base_url.rstrip('/')}/catalog/{product.id}"


_INTRO_LINE = (
    "Based on your recent activity on SmartReco, here are today's picks - "
    "chosen specifically for you."
)


def render_digest_email(narrative: str, products: list[Product], base_url: str) -> str:
    lines = [
        _INTRO_LINE,
        "",
        "Why these courses:",
        narrative,
        "",
        "Recommended for you:",
    ]
    for product in products:
        price = "Free" if product.price == 0 else f"INR {product.price:.2f}"
        lines.append(f"- {product.title} ({product.category}) - {price}")
        lines.append(f"  {_course_url(base_url, product)}")
    lines.append("")
    lines.append(f"View your full dashboard: {_dashboard_url(base_url)}")
    return "\n".join(lines)


def _product_row_html(product: Product, base_url: str) -> str:
    accent = _TONE_HEX[category_cover(product.category)["tone_class"]]
    price = "Free" if product.price == 0 else f"&#8377;{product.price:,.2f}"
    href = escape(_course_url(base_url, product))
    return f"""
      <tr>
        <td style="padding:14px 0;border-top:1px solid #e6e8ea;">
          <a href="{href}" style="display:block;text-decoration:none;color:inherit;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td width="4" style="background:{accent};border-radius:4px;" bgcolor="{accent}">&nbsp;</td>
              <td style="padding-left:14px;">
                <span style="display:inline-block;font-family:Arial,Helvetica,sans-serif;font-size:11px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;color:{accent};background:#f2f4f6;border-radius:999px;padding:3px 10px;margin-bottom:6px;">{escape(product.category)}</span>
                <div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;font-weight:700;color:#191c1e;line-height:1.4;">{escape(product.title)}</div>
              </td>
              <td width="90" align="right" style="font-family:Arial,Helvetica,sans-serif;font-size:14px;font-weight:700;color:#191c1e;white-space:nowrap;">{price} &rarr;</td>
            </tr>
          </table>
          </a>
        </td>
      </tr>"""


def render_digest_email_html(
    narrative: str, products: list[Product], base_url: str
) -> str:
    """Styled HTML alternative to render_digest_email() - inline-styled,
    table-based layout (broad email-client compatibility, since clients
    can't load the app's own stylesheet), mirroring the app's own gradient
    branding and tonal product covers. `base_url` is needed because an
    email is opened outside any browser session tied to the app's own
    host - every link here must be absolute (the "View Dashboard" button
    and each course row both need a real, real login-gated destination)."""
    rows = "".join(_product_row_html(product, base_url) for product in products)
    dashboard_href = escape(_dashboard_url(base_url))
    return f"""<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#f2f4f6;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f2f4f6;padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border-radius:16px;overflow:hidden;border:1px solid #e6e8ea;">
            <tr>
              <td style="background:#00236f;background-image:linear-gradient(135deg,#00236f,#2e4fa8);padding:32px 32px 26px;">
                <table role="presentation" cellpadding="0" cellspacing="0">
                  <tr>
                    <td style="width:34px;height:34px;background:rgba(255,255,255,0.16);border-radius:8px;text-align:center;vertical-align:middle;font-family:Arial,Helvetica,sans-serif;font-size:15px;font-weight:700;color:#ffffff;">S</td>
                    <td style="padding-left:10px;font-family:Arial,Helvetica,sans-serif;font-size:17px;font-weight:700;color:#ffffff;">SmartReco</td>
                  </tr>
                </table>
                <div style="font-family:Arial,Helvetica,sans-serif;font-size:13px;color:rgba(255,255,255,0.75);margin-top:14px;">Your daily picks, grounded in what you've actually browsed.</div>
              </td>
            </tr>
            <tr>
              <td style="padding:26px 32px 6px;">
                <p style="margin:0 0 16px;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.6;color:#191c1e;font-weight:600;">{escape(_INTRO_LINE)}</p>
                <span style="display:inline-block;font-family:Arial,Helvetica,sans-serif;font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#006a61;margin-bottom:8px;">Why these courses</span>
                <p style="margin:0 0 18px;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.6;color:#2f3437;">{escape(narrative)}</p>
                <a href="{dashboard_href}" style="display:inline-block;background:#00236f;background-image:linear-gradient(135deg,#00236f,#2e4fa8);color:#ffffff;text-decoration:none;font-family:Arial,Helvetica,sans-serif;font-size:14px;font-weight:700;padding:11px 22px;border-radius:999px;">View in Dashboard &rarr;</a>
              </td>
            </tr>
            <tr>
              <td style="padding:8px 32px 28px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:18px 32px;background:#f7f9fb;border-top:1px solid #e6e8ea;font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#757682;">
                You're receiving this because you've been browsing SmartReco. Every course above is real and already in the catalog - nothing here is invented. Not signed in? Clicking a link above will ask you to log in first, then take you straight there.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


def run_daily_digest(session: Session) -> int:
    """Runs the pipeline for every active user and emails a digest. Returns
    the number of digests actually sent (users with no grounded
    recommendations are skipped, not emailed an empty one).

    Logs progress per user (INFO) - each iteration runs a real LangGraph
    pipeline (Mesh + Qdrant calls), so a run across many users can take a
    while; without this, both the scheduled job's logs and a manual
    `make digest` run would show nothing at all until the very end."""
    base_url = get_settings().public_base_url
    user_ids = _active_user_ids(session)
    total = len(user_ids)
    sent = 0
    for index, user_id in enumerate(user_ids, start=1):
        user = session.get(User, user_id)
        if user is None:
            continue

        narrative, product_ids = run_recommendation_graph(session, user)
        if not product_ids:
            logger.info(
                "Digest %d/%d: skipping user_id=%s (no grounded candidates)",
                index,
                total,
                user_id,
            )
            continue

        products = _ordered_products(session, product_ids)
        body = render_digest_email(narrative, products, base_url)
        html_body = render_digest_email_html(narrative, products, base_url)
        send_email(user.email, DIGEST_SUBJECT, body, html_body=html_body)
        sent += 1
        logger.info(
            "Digest %d/%d: sent to %s (%d product(s))",
            index,
            total,
            user.email,
            len(product_ids),
        )

    logger.info("Digest complete: %d/%d email(s) sent", sent, total)
    return sent
