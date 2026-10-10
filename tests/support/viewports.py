"""The three widths the UI must work at (FR-3, NFR-10)."""

from playwright.sync_api import ViewportSize

PHONE = ViewportSize(width=390, height=844)
TABLET = ViewportSize(width=820, height=1180)
DESKTOP = ViewportSize(width=1280, height=800)

ALL = {"phone": PHONE, "tablet": TABLET, "desktop": DESKTOP}
