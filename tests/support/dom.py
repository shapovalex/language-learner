"""Page helpers for style checks: add test-only markup, read computed styles, settle fonts."""

from playwright.sync_api import Locator, Page


def append_to_body(page: Page, html: str) -> None:
    """Add markup at the end of `<body>`, outside `#app`, which `main.js` rewrites."""
    page.evaluate("(html) => document.body.insertAdjacentHTML('beforeend', html)", html)


def prepend_to_body(page: Page, html: str) -> None:
    """Add markup at the start of `<body>`, so it comes first in the Tab order."""
    page.evaluate("(html) => document.body.insertAdjacentHTML('afterbegin', html)", html)


def computed_style(locator: Locator, *props: str) -> dict[str, str]:
    """`getComputedStyle` values by camelCase name, e.g. `computed_style(el, "fontSize")`."""
    return locator.evaluate(
        "(el, props) => Object.fromEntries(props.map((p) => [p, getComputedStyle(el)[p]]))",
        list(props),
    )


def px(value: str) -> float:
    """`"16px"` -> `16.0`."""
    return float(value.removesuffix("px"))


def settle_fonts(page: Page) -> None:
    """Force a layout, so rendered text requests its fonts, then wait for every pending load."""
    page.evaluate(
        "async () => { document.body.getBoundingClientRect(); await document.fonts.ready; }"
    )
