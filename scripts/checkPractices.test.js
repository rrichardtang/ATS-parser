const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { violations } = require('./checkPractices');

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'practices-'));
const write = (name, body) => {
  const file = path.join(dir, name);
  fs.writeFileSync(file, body);
  return file;
};

test('flags the markers CLAUDE.md forbids', () => {
  for (const marker of ['// TODO: finish', '// FIXME later', '/* XXX */', '// HACK around it', "throw new Error('not implemented')"]) {
    const found = violations(write('m.js', `const a = 1;\n${marker}\n`));
    assert.equal(found.length, 1, marker);
    assert.equal(found[0].line, 2);
  }
});

test('leaves clean code alone', () => {
  assert.deepEqual(violations(write('clean.js', 'const sum = (a, b) => a + b;\n')), []);
});

test('does not fire on words that merely contain a marker', () => {
  // "todos" and "hackathon" are ordinary content; a checker that trips on them
  // gets switched off, taking the real check with it.
  assert.deepEqual(violations(write('words.js', 'const todos = [];\nconst hackathonEntry = 1;\n')), []);
});

test('ignores files it has no opinion about', () => {
  assert.deepEqual(violations(write('notes.md', '# TODO: write this\n')), []);
  assert.deepEqual(violations(path.join(dir, 'missing.js')), []);
});

test('reports every occurrence with its line number', () => {
  const found = violations(write('many.js', 'const a = 1;\n// TODO one\nconst b = 2;\n// FIXME two\n'));
  assert.deepEqual(found.map((v) => v.line), [2, 4]);
});

test('the repo it guards currently passes it', () => {
  // 'src' doesn't exist yet on a fresh project — only scan source dirs that are actually there.
  const sources = ['src', 'scripts']
    .map((d) => path.join(__dirname, '..', d))
    .filter((d) => fs.existsSync(d))
    .flatMap((d) => fs.readdirSync(d).map((f) => path.join(d, f)))
    .filter((f) => f.endsWith('.js'));
  const offenders = sources.flatMap((f) => violations(f).map((v) => `${path.basename(f)}:${v.line}`));
  assert.deepEqual(offenders, []);
});
