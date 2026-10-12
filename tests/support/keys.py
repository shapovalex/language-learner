"""Keyboard differences between the browsers the E2E suite runs on."""

# WebKit's Tab skips buttons and links by default (as Safari does); Alt+Tab reaches every control
_TAB = {"webkit": "Alt+Tab"}
_SHIFT_TAB = {"webkit": "Alt+Shift+Tab"}


def tab(browser_name: str) -> str:
    return _TAB.get(browser_name, "Tab")


def shift_tab(browser_name: str) -> str:
    return _SHIFT_TAB.get(browser_name, "Shift+Tab")
