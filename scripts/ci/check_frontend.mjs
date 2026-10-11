import { readdir } from 'node:fs/promises';
import { resolve, dirname, extname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
async function sourceFiles(folder) {
  const result = [];
  for (const entry of await readdir(folder, { withFileTypes: true })) {
    if (['node_modules', '.git'].includes(entry.name)) continue;
    const path = resolve(folder, entry.name);
    if (entry.isDirectory()) result.push(...await sourceFiles(path));
    else if (['.js', '.mjs'].includes(extname(entry.name))) result.push(path);
  }
  return result;
}
const files = await sourceFiles(resolve(root, 'frontend'));
for (const path of files) {
  const checked = spawnSync(process.execPath, ['--check', path], { stdio: 'inherit' });
  if (checked.error || checked.status !== 0) {
    console.error('JavaScript syntax check failed:', path);
    process.exit(1);
  }
}
console.log('JavaScript syntax checked:', files.length, 'files; application build is not configured.');
