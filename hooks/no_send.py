#!/usr/bin/env python3
"""PreToolUse hook: Claude never sends, replies, forwards or posts for the person.

Blocks any MCP tool on a mail, chat or social server whose action is send,
reply, forward or post (Gmail's send_message, reply and forward; Outlook's
send_email; Slack's send_message...). Drafting tools (create_draft,
update_draft) are untouched, so email still goes in as a draft the person
sends. Calendar invitations to other people need the person's yes in the app.

Reads the hook payload on stdin and prints a decision as JSON. The plugin's
`block_sending` setting (default on) turns it off: CLAUDE_PLUGIN_OPTION_BLOCK_SENDING=false.

    echo '{"tool_name": "mcp__Gmail__send_message", "tool_input": {}}' | python3 no_send.py
"""

import json
import os
import re
import sys

SERVERS = re.compile(r"mail|outlook|slack|teams|whatsapp|telegram|linkedin|reddit|twitter|^x$|discord", re.I)
SENDING = re.compile(r"^(send|reply|forward|post|publish|submit)(_|$)", re.I)
CALENDAR = re.compile(r"calendar", re.I)
INVITING = re.compile(r"^(create|update)_event$|^respond_to_event$", re.I)

DENY = ("The Job Search Assistant never sends anything itself. Save it as a "
        "draft (for email, create_draft) and tell the person it's ready for "
        "them to check and send.")
ASK = "This sends a calendar invitation or reply to other people: check with the person first."


def split(tool_name):
    """mcp__<server>__<tool> -> (server, tool); anything else -> (None, name)."""
    if not tool_name.startswith("mcp__"):
        return None, tool_name
    parts = tool_name[5:].split("__")
    if len(parts) < 2:
        return None, tool_name
    return "__".join(parts[:-1]), parts[-1]


def has_guests(tool_input):
    guests = tool_input.get("attendees") or tool_input.get("guests") or []
    return bool(guests)


def decide(payload, env=os.environ):
    """Return ('deny' | 'ask' | None, reason)."""
    if env.get("CLAUDE_PLUGIN_OPTION_BLOCK_SENDING", "true").lower() in ("false", "0", "no", "off"):
        return None, ""
    server, tool = split(payload.get("tool_name", ""))
    if server is None:
        return None, ""
    # Plugin-bundled servers are named plugin_<plugin>_<server>.
    name = re.sub(r"^plugin_[^_]+(?:-[^_]+)*_", "", server)
    if SERVERS.search(name) and SENDING.search(tool):
        return "deny", DENY
    if CALENDAR.search(name) and INVITING.search(tool):
        tool_input = payload.get("tool_input") or {}
        if tool.lower() == "respond_to_event" or has_guests(tool_input):
            return "ask", ASK
    return None, ""


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    decision, reason = decide(payload)
    if decision:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }}))
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    sys.exit(main())
