#!/usr/bin/env python3
"""PostToolUse hook: after Claude writes the job list, check it straight away.

When a Write or Edit touches a file named pipeline.json, runs job-tracker's
validate on it. Errors go back to Claude as a block with the list, so they're
fixed before anything else; warnings are passed on as context.

    echo '{"tool_name": "Write", "tool_input": {"file_path": "jobsearch/pipeline.json"}}' | python3 check_joblist.py
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "skills", "job-tracker"))

import pipeline  # noqa: E402


def check(payload, cwd=None):
    """Return the hook's JSON reply as a dict, or None when there's nothing to say."""
    tool_input = payload.get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("path") or ""
    if os.path.basename(path) != "pipeline.json":
        return None
    if not os.path.isabs(path):
        path = os.path.join(cwd or payload.get("cwd") or os.getcwd(), path)
    try:
        data = pipeline.load(path)
    except Exception as exc:  # unreadable JSON is an error worth fixing now
        return {"decision": "block", "reason": "The job list no longer loads: %s. Fix it before anything else." % exc}
    errors, warnings = pipeline.validate(data)
    if errors:
        return {"decision": "block",
                "reason": "The job list has %d error(s) after that change; fix them now:\n- %s"
                          % (len(errors), "\n- ".join(errors[:20]))}
    if warnings:
        return {"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                       "additionalContext": "Job list warnings:\n- " + "\n- ".join(warnings[:20])}}
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    reply = check(payload)
    if reply:
        print(json.dumps(reply))
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    sys.exit(main())
