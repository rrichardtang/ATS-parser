const test = require('node:test');
const assert = require('node:assert/strict');
const { isPushCommand, reviewIsCurrent } = require('./prePushReview');

const HEAD = 'a'.repeat(40);
const receipt = (sha) => JSON.stringify({ sha, branch: 'x', reviewedAt: '2026-08-17T00:00:00Z' });

test('recognises a push however it is written', () => {
  for (const command of [
    'git push',
    'git push -u origin feature/x',
    'git push --force-with-lease',
    'git -C /repo push',
    'git --no-pager push',
    '  git push  ',
    'cd /tmp && git push',
    'npm test; git push',
    'git fetch origin && git rebase main && git push -u origin hotfix'
  ]) {
    assert.equal(isPushCommand(command), true, command);
  }
});

test('leaves every other command alone', () => {
  for (const command of [
    'git status',
    'git fetch origin',
    'git log --oneline',
    'npm test',
    'pushd /tmp',
    // The word appearing as data is not an invocation — a guard that trips on these gets
    // switched off, taking the real check with it.
    'echo "run git push when ready"',
    'grep -r "git push" docs/',
    // Chaining operators inside a quoted string must not be split on: this exact shape blocked a
    // command that never pushed, because the split exposed the tail as its own segment.
    "node -e \"const cases=['a && git push origin main']\"",
    'echo "deploy: build && git push"',
    ''
  ]) {
    assert.equal(isPushCommand(command), false, command);
  }
});

test('still sees a real push that carries quoted arguments', () => {
  assert.equal(isPushCommand('git push origin "main"'), true);
  assert.equal(isPushCommand('cd "/my dir" && git push'), true);
});

test('handles a missing or malformed command without throwing', () => {
  assert.equal(isPushCommand(undefined), false);
  assert.equal(isPushCommand(null), false);
});

test('accepts a receipt only when it matches the exact commit being pushed', () => {
  assert.equal(reviewIsCurrent(receipt(HEAD), HEAD), true);
});

test('rejects a receipt left behind by an earlier commit', () => {
  assert.equal(reviewIsCurrent(receipt('b'.repeat(40)), HEAD), false);
});

test('rejects a missing, empty, or unreadable receipt', () => {
  assert.equal(reviewIsCurrent('', HEAD), false);
  assert.equal(reviewIsCurrent('not json at all', HEAD), false);
  assert.equal(reviewIsCurrent('{}', HEAD), false);
  assert.equal(reviewIsCurrent(receipt(HEAD), ''), false);
});
