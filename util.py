# -*- coding: utf-8 -*-

# Adapted from https://wiki.python.org/moin/EscapingHtml
html_escape_table = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;",
    ">": "&gt;",
    "<": "&lt;",
    }

def html_escape(text):
    """Produce entities within text."""
    if text is None:
        return None
    return "".join(html_escape_table.get(c, c) for c in text)
