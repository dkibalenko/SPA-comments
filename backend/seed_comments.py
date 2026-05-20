"""
Seed script: 30 top-level comments + nested reply tree.
Run inside the backend container:
    docker compose -f docker-compose.prod.yml exec backend python manage.py shell < seed_comments.py
"""
import uuid
from datetime import timedelta

from django.utils import timezone

from apps.comments.models import Comment
from apps.users.models import User

# ── helpers ──────────────────────────────────────────────────────────────────

def make_user(username, email, home_page=None):
    user, _ = User.objects.get_or_create(
        username=username,
        email=email,
        defaults={
            "home_page": home_page,
            "ip_address": "127.0.0.1",
            "user_agent": "SeedScript/1.0",
        },
    )
    return user


def make_comment(user, text, parent=None, minutes_ago=0):
    c = Comment(
        id=uuid.uuid4(),
        user=user,
        parent=parent,
        text=text,
    )
    c.save()
    if minutes_ago:
        Comment.objects.filter(pk=c.pk).update(
            created_at=timezone.now() - timedelta(minutes=minutes_ago)
        )
        c.refresh_from_db()
    return c


# ── users ─────────────────────────────────────────────────────────────────────

alice   = make_user("Alice42",    "alice@example.com",   "https://alice.dev")
bob     = make_user("BobCoder",   "bob@example.com",     "https://bob.io")
carol   = make_user("Carol99",    "carol@example.com")
dave    = make_user("Dave2025",   "dave@example.com",    "https://dave.blog")
eve     = make_user("EveTech",    "eve@example.com")
frank   = make_user("Frank77",    "frank@example.com",   "https://frank.net")
grace   = make_user("Grace0",     "grace@example.com")
henry   = make_user("HenryX",     "henry@example.com",   "https://henry.com")
iris    = make_user("Iris123",    "iris@example.com")
jack    = make_user("JackDev",    "jack@example.com",    "https://jackdev.io")

users = [alice, bob, carol, dave, eve, frank, grace, henry, iris, jack]

# ── 30 top-level comments ─────────────────────────────────────────────────────

top_level_data = [
    (alice, "Just set up this app for the first time — really clean interface!", 300),
    (bob,   "The <strong>real-time updates</strong> via WebSocket are impressive. Posted from tab 1, appeared in tab 2 instantly.", 295),
    (carol, "Love that nested replies can go infinitely deep. Great for long discussions.", 290),
    (dave,  "Tested the CAPTCHA — refreshes correctly after each submission. Nice UX.", 285),
    (eve,   "The <code>JWT identity token</code> pre-fills the form on page reload. Smart touch.", 280),
    (frank, "Sorted by email descending and it worked perfectly. The column sort is snappy.", 275),
    (grace, "Uploaded a 1920×1080 PNG — the server resized it to 320×240 automatically. ", 270),
    (henry, "Tried posting a <i>TXT file</i> over 100 KB and got the right validation error.", 265),
    (iris,  "The XSS test: entered <code>&lt;script&gt;alert(1)&lt;/script&gt;</code> in the text — it was stripped safely.", 260),
    (jack,  "Pagination kicks in at 26 comments. Confirmed page 2 loads correctly.", 255),
    (alice, "The Celery email task fires on every reply to a different user. Checked the logs.", 250),
    (bob,   "Redis cache invalidates on new comment — cache MISS logged right after posting.", 245),
    (carol, "Home page field is optional — left it blank, comment went through fine.", 240),
    (dave,  "Tried <strong>bold</strong>, <i>italic</i>, and <code>code</code> tags — all rendered correctly in the comment.", 235),
    (eve,   "The <a href=\"https://github.com\" title=\"GitHub\">GitHub link</a> inside a comment renders as a clickable anchor.", 230),
    (frank, "Self-reply test: replied to my own comment — no email notification sent. Correct behavior.", 225),
    (grace, "Username validation: tried entering spaces and special chars — both rejected on the client and server.", 220),
    (henry, "Email format validation caught <code>notanemail</code> immediately before submit.", 215),
    (iris,  "Sorting by date ascending shows oldest comments first. Sorting by date descending restores LIFO. Both work.", 210),
    (jack,  "The lightbox preview for image attachments has a smooth fade animation. Nice visual effect.", 205),
    (alice, "Tested rapid double-submit — only one comment was created. No duplicates.", 200),
    (bob,   "SQL injection attempt in username: <code>'; DROP TABLE--</code> was stored safely as text. ORM parameterization works.", 195),
    (carol, "Unclosed <code>&lt;i&gt;tag</code> in text — it was auto-closed in the rendered output. XHTML valid.", 190),
    (dave,  "The toolbar [a] button inserts the anchor template correctly at the cursor position.", 185),
    (eve,   "Tried attaching a <strong>BMP file</strong> — rejected with the right error message. Only JPG/PNG/GIF accepted.", 180),
    (frank, "The comment tree loads in a single query using recursive CTE. Checked via Django debug toolbar.", 175),
    (grace, "Three Redis logical databases keep cache, channels, and Celery isolated. Flushing one doesn't affect others.", 170),
    (henry, "The app handles 3+ levels of nesting cleanly. Reply to a reply to a reply all render correctly.", 165),
    (iris,  "Preview function renders the comment text (including allowed HTML) without submitting the form.", 160),
    (jack,  "Overall: clean architecture, solid validation, real-time updates work great. Well done!", 155),
]

top_comments = []
for user, text, mins in top_level_data:
    c = make_comment(user, text, minutes_ago=mins)
    top_comments.append(c)

print(f"Created {len(top_comments)} top-level comments.")

# ── reply tree ────────────────────────────────────────────────────────────────
# Thread 1: under top_comments[1] (Bob's WebSocket comment) — 3 levels deep

r1 = make_comment(carol, "Agreed! I had two tabs open and the update was near-instant.", parent=top_comments[1], minutes_ago=293)
r1a = make_comment(bob,   "The channel layer uses Redis DB 2 — completely separate from the cache.", parent=r1, minutes_ago=291)
r1a1 = make_comment(alice, "Makes sense — so a cache flush won't drop pending WebSocket messages.", parent=r1a, minutes_ago=289)
r1a1a = make_comment(dave, "Exactly. Three isolated Redis databases by design.", parent=r1a1, minutes_ago=287)

# Thread 2: under top_comments[4] (Eve's JWT comment)

r2 = make_comment(frank, "Confirmed — closed the tab, reopened, username and email were pre-filled.", parent=top_comments[4], minutes_ago=278)
r2a = make_comment(eve,   "The JWT has a 30-day lifetime. Not an auth token — just identity convenience.", parent=r2, minutes_ago=276)
r2a1 = make_comment(grace, "Smart. No login required but the UX feels personalized.", parent=r2a, minutes_ago=274)

# Thread 3: under top_comments[6] (Grace's image resize comment)

r3 = make_comment(henry, "What library handles the resize? Pillow?", parent=top_comments[6], minutes_ago=268)
r3a = make_comment(grace, "Yes — Pillow with a strategy pattern. ImageProcessor resizes proportionally to 320×240.", parent=r3, minutes_ago=266)
r3a1 = make_comment(iris, "So adding a new file type just needs a new processor class? Clean.", parent=r3a, minutes_ago=264)
r3a1a = make_comment(grace, "Exactly — the service and view don't change.", parent=r3a1, minutes_ago=262)

# Thread 4: under top_comments[9] (Jack's pagination comment)

r4 = make_comment(alice, "25 per page as specified. Top-level only — replies don't count toward the page limit.", parent=top_comments[9], minutes_ago=253)
r4a = make_comment(jack,  "Good call — otherwise a deeply nested thread would eat the whole page quota.", parent=r4, minutes_ago=251)

# Thread 5: under top_comments[19] (Jack's lightbox comment)

r5  = make_comment(bob,   "The fade-in on the lightbox is smooth. Click outside to close also works.", parent=top_comments[19], minutes_ago=203)
r5a = make_comment(carol, "Text file preview works too — opens the content inline.", parent=r5, minutes_ago=201)

print("Created reply threads under comments 2, 5, 7, 10, 20.")
print("Seed complete. Refresh the app to see all comments.")
