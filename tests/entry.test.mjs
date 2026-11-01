import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { browserExecutable, skillsDirectory, apply } from '../index.js';

test('skill directory resolves relative to the installed package', () => {
  assert.ok(existsSync(join(skillsDirectory, 'dsh-image-service/SKILL.md')));
  assert.ok(existsSync(join(skillsDirectory, 'dsh-visualize/SKILL.md')));
});
test('explicit browser paths must exist', () => {
  assert.throws(() => browserExecutable({ executablePath: '/missing/dsh-browser-test' }));
  const dir = mkdtempSync(join(tmpdir(), 'dsh-capabilities-'));
  try {
    const executablePath = join(dir, 'browser'); writeFileSync(executablePath, 'test fixture');
    assert.equal(browserExecutable({ executablePath }), executablePath);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});
test('invalid feature flags fail before plugins are mounted', async () => {
  await assert.rejects(apply({}, { enableDesktop: 'true' }), /must be boolean/);
});
