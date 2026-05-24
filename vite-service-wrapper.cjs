#!/usr/bin/env node
// vite-service-wrapper.cjs
//
// Service wrapper for Vite. Spawns `node <viteBin> [args...]` and pipes its
// stdout/stderr through a sanitizer that strips ANSI escape sequences and
// any non-printable / non-ASCII characters before writing to the inherited
// stdio. This keeps NSSM/systemd log files clean.
//
// Usage:
//   node vite-service-wrapper.cjs <viteBin> [vite args...]

'use strict';

const { spawn } = require('child_process');

const ANSI_RE = /\x1b\[[0-9;?]*[a-zA-Z]/g;
// Allow TAB (\x09), LF (\x0a), CR (\x0d) and printable ASCII (\x20-\x7e).
const NON_ASCII_RE = /[^\x09\x0a\x0d\x20-\x7e]/g;

function sanitize(chunk) {
    return chunk
        .toString('utf8')
        .replace(ANSI_RE, '')
        .replace(NON_ASCII_RE, '');
}

const [vitePath, ...args] = process.argv.slice(2);
if (!vitePath) {
    process.stderr.write(
        'Usage: node vite-service-wrapper.cjs <viteBin> [args...]\n'
    );
    process.exit(2);
}

const child = spawn(process.execPath, [vitePath, ...args], {
    stdio: ['ignore', 'pipe', 'pipe'],
    env: Object.assign({}, process.env, {
        NO_COLOR: '1',
        FORCE_COLOR: '0',
        TERM: 'dumb',
    }),
});

child.stdout.on('data', (d) => process.stdout.write(sanitize(d)));
child.stderr.on('data', (d) => process.stderr.write(sanitize(d)));

child.on('exit', (code, signal) => {
    process.exit(code != null ? code : (signal ? 1 : 0));
});

const forward = (sig) => {
    try { child.kill(sig); } catch (_) { /* ignore */ }
};
process.on('SIGTERM', () => forward('SIGTERM'));
process.on('SIGINT',  () => forward('SIGINT'));
process.on('SIGHUP',  () => forward('SIGHUP'));
