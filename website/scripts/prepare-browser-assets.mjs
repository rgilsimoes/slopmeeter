import { cp, mkdir, rm } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';

const website = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const destination = join(website, 'public', 'vendor');
const pyodideDestination = join(destination, 'pyodide-0.27.7');
const pyodideSource = join(website, 'node_modules', 'pyodide');
const runtimeFiles = [
  'pyodide.mjs',
  'pyodide.asm.js',
  'pyodide.asm.wasm',
  'python_stdlib.zip',
  'pyodide-lock.json',
  'package.json',
  'README.md',
];

await rm(destination, { recursive: true, force: true });
await mkdir(pyodideDestination, { recursive: true });
await Promise.all(runtimeFiles.map((name) => cp(join(pyodideSource, name), join(pyodideDestination, name))));

await new Promise((resolvePromise, reject) => {
  const build = spawn('python3', [
    join(website, 'scripts', 'build-browser-wheel.py'),
    join(destination, 'slop_meeter-0.4.0-py3-none-any.whl'),
  ], { stdio: 'inherit' });
  build.on('exit', (code) => code === 0 ? resolvePromise() : reject(new Error(`wheel build exited with ${code}`)));
  build.on('error', reject);
});

console.log('Prepared pinned Pyodide runtime and Slop Meeter browser wheel.');
