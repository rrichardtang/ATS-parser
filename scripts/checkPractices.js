#!/usr/bin/env node
// PostToolUse hook: enforces the one engineering practice in CLAUDE.md that a
// machine can check without guessing — "no dead code, placeholder stubs, or TODO
// markers unless explicitly requested". The rest of the rules (comment necessity,
// readability, function size) are judgement calls; a checker that guesses at them
// cries wolf and gets switched off, taking this check with it.
//
// Reads the hook payload on stdin, exits 2 with a message when the file Claude
// just wrote carries a marker, which feeds the finding back into the session.
const fs = require('fs');

const MARKERS = /\b(TODO|FIXME|XXX|HACK)\b|not implemented|placeholder stub/i;
const CHECKED = /\.(js|mjs|cjs)$/;
// A marker detector and its test are the two files that must contain the markers.
// That is the whole exemption list and it should stay that way — a third entry
// means the rule is being bent rather than the code fixed.
const SELF = /checkPractices(\.test)?\.js$/;

function violations(filePath) {
  if (!CHECKED.test(filePath) || SELF.test(filePath) || !fs.existsSync(filePath)) return [];
  return fs.readFileSync(filePath, 'utf8')
    .split('\n')
    .map((line, i) => ({ line: i + 1, text: line.trim() }))
    .filter(({ text }) => MARKERS.test(text));
}

function main(payload) {
  const filePath = payload?.tool_input?.file_path;
  if (!filePath) return 0;

  const found = violations(filePath);
  if (!found.length) return 0;

  const detail = found.map(({ line, text }) => `  ${filePath}:${line}  ${text.slice(0, 100)}`).join('\n');
  process.stderr.write(
    `CLAUDE.md engineering practices: no TODO markers or placeholder stubs unless explicitly requested.\n${detail}\n` +
    'Finish the work or remove the marker. If the user asked for a stub, say so and proceed.\n'
  );
  return 2;
}

if (require.main === module) {
  let stdin = '';
  process.stdin.on('data', (chunk) => { stdin += chunk; });
  process.stdin.on('end', () => {
    let payload = null;
    try {
      payload = JSON.parse(stdin);
    } catch {
      process.exit(0);
    }
    process.exit(main(payload));
  });
}

module.exports = { violations };
