#!/usr/bin/env python3
"""Extract inline browser JavaScript so CI can validate it with Node."""
from html.parser import HTMLParser
import sys

class InlineScripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.current = []
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script" and not dict(attrs).get("src"):
            self.active = True
            self.current = []

    def handle_data(self, data):
        if self.active:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self.active:
            self.scripts.append("".join(self.current))
            self.active = False

parser = InlineScripts()
parser.feed(open("index.html", encoding="utf-8").read())
if not parser.scripts:
    raise SystemExit("No inline JavaScript found in index.html")
sys.stdout.write("\n;\n".join(parser.scripts))
