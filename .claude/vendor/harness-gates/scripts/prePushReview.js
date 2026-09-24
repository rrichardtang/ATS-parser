#!/usr/bin/env node
// PreToolUse hook: holds `git push` until the felix-the-fixer subagent has looked at the exact
// code being pushed. The receipt is keyed on HEAD, so a new commit invalidates it automatically —
// what gets reviewed is a code state, not a session.
//
// This is a nudge, not enforcement: anyone can write the receipt without a review, and it never
// leaves this clone. Enforcement belongs on the server (branch protection, a required PR review).
//
// Reads the hook payload on stdin, exits 2 with instructions when the receipt is missing or stale,
// which feeds the block back into the session. `--record` writes the receipt for the current HEAD.
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

// The receipt lives inside the repository's git directory, so it is per-clone and can never be
// committed, whatever the project's .gitignore says. Resolved from the project, not from this
// script, which ships inside a plugin.
const RECEIPT_NAME = 'claude-pre-push-review.json';

// Global git flags that consume the token after them, so `git -C /repo push` still resolves to
// `push` rather than stopping at the path.
const FLAGS_TAKING_A_VALUE = new Set(['-C', '-c', '--git-dir', '--work-tree', '--namespace', '--exec-path', '--config-env']);

function firstGitSubcommand(segment) {
  const tokens = segment.trim().split(/\s+/);
  if (tokens[0] === 'sudo') tokens.shift();
  if (tokens.shift() !== 'git') return '';
  while (tokens.length) {
    const token = tokens[0];
    if (!token.startsWith('-')) return token;
    tokens.shift();
    if (FLAGS_TAKING_A_VALUE.has(token)) tokens.shift();
  }
  return '';
}

// Split on the operators that chain commands so `cd x && git push` is still seen as a push. A
// narrower prefix check reads fine and fails silently, which is the worst property for a guard.
// Quoted spans go first: without that, splitting cuts through a string that merely contains
// "&& git push" and blocks a command that never pushes. A guard that cries wolf gets switched off,
// taking the real check with it.
function isPushCommand(command) {
  return String(command || '')
    .replace(/'[^']*'|"[^"]*"/g, ' ')
    .split(/&&|\|\||;|\||\n/)
    .some((segment) => firstGitSubcommand(segment) === 'push');
}

function reviewIsCurrent(receiptText, headSha) {
  if (!receiptText || !headSha) return false;
  try {
    return JSON.parse(receiptText).sha === headSha;
  } catch {
    return false;
  }
}

function git(...args) {
  return execFileSync('git', args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
}

function receiptPath() {
  return path.resolve(git('rev-parse', '--git-path', RECEIPT_NAME));
}

function readReceipt() {
  const file = receiptPath();
  return fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : '';
}

function record() {
  const receipt = { sha: git('rev-parse', 'HEAD'), branch: git('rev-parse', '--abbrev-ref', 'HEAD'), reviewedAt: new Date().toISOString() };
  fs.writeFileSync(receiptPath(), `${JSON.stringify(receipt, null, 2)}\n`);
  process.stdout.write(`Recorded pre-push review for ${receipt.sha.slice(0, 8)} on ${receipt.branch}.\n`);
}

function main(payload) {
  if (!isPushCommand(payload?.tool_input?.command)) return 0;

  let headSha = '';
  let range = 'main..HEAD';
  try {
    headSha = git('rev-parse', 'HEAD');
    range = `${git('rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}')}..HEAD`;
  } catch {
    // No upstream yet, or not a git dir — the main..HEAD default already covers the first case.
  }
  let receipt = '';
  try {
    receipt = readReceipt();
  } catch {
    // No git directory to read from: treat as unreviewed. A guard that fails open is no guard.
  }
  if (reviewIsCurrent(receipt, headSha)) return 0;

  process.stderr.write(
    `Push blocked: ${headSha.slice(0, 8) || 'HEAD'} has not been reviewed.\n` +
    `Run the felix-the-fixer subagent (harness:felix-the-fixer) over ${range}, act on anything it finds, then record it:\n` +
    `  node "${__filename}" --record\n` +
    'Run --record as its own command: this check runs before the whole command line, so a record\n' +
    'chained in front of the push is not seen until the next attempt.\n' +
    'Record without a review only when the push carries no code (notes, docs) — and say so.\n'
  );
  return 2;
}

if (require.main === module) {
  if (process.argv.includes('--record')) {
    record();
  } else {
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
}

module.exports = { isPushCommand, reviewIsCurrent };
