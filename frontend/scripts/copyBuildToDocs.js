#!/usr/bin/env node
// Copy CRA build output into repository-level docs/ for GitHub Pages
// Creates docs/404.html and .nojekyll

const fs = require('fs');
const path = require('path');

const repoRoot = path.resolve(__dirname, '..', '..');
const buildDir = path.resolve(__dirname, '..', 'build');
const docsDir = path.resolve(repoRoot, 'docs');

function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

function emptyDir(dirPath) {
  if (fs.existsSync(dirPath)) {
    fs.rmSync(dirPath, { recursive: true, force: true });
  }
}

function copyRecursive(src, dest) {
  fs.cpSync(src, dest, { recursive: true });
}

function main() {
  if (!fs.existsSync(buildDir)) {
    console.error('Build directory not found. Run "npm run build" first.');
    process.exit(1);
  }

  emptyDir(docsDir);
  ensureDir(docsDir);
  copyRecursive(buildDir, docsDir);

  const indexPath = path.join(docsDir, 'index.html');
  const notFoundPath = path.join(docsDir, '404.html');
  if (fs.existsSync(indexPath)) {
    fs.copyFileSync(indexPath, notFoundPath);
  }

  const noJekyllPath = path.join(docsDir, '.nojekyll');
  fs.writeFileSync(noJekyllPath, '');

  console.log('Copied build/ to docs/ for GitHub Pages.');
}

main();


