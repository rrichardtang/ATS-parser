#!/bin/sh
# Runs the push gate under Node. Without Node the gate cannot parse the command, so it holds
# anything that mentions a git push rather than letting every push through unreviewed: a hook
# that errors any other way is non-blocking, which would turn a missing runtime into an open gate.
if command -v node >/dev/null 2>&1; then
  exec node "$(dirname "$0")/prePushReview.js"
fi
case "$(cat)" in
  *git*push*)
    echo "harness-gates: Node is not installed, so the push gate cannot check this command. Install Node, or disable harness-gates for this project." >&2
    exit 2
    ;;
esac
exit 0
