/**
 * Copies the compiled React build (web/build) into vehicle/public
 * so the FastAPI backend can serve the SPA.
 */
const fs = require('fs');
const path = require('path');

const webDir = path.join(__dirname, '..');
const src = path.join(webDir, 'build');
const dest = path.join(webDir, '..', 'vehicle', 'public');

function copyRecursive(srcDir, destDir) {
  const stat = fs.statSync(srcDir);
  if (stat.isDirectory()) {
    fs.mkdirSync(destDir, { recursive: true });
    for (const entry of fs.readdirSync(srcDir)) {
      copyRecursive(path.join(srcDir, entry), path.join(destDir, entry));
    }
  } else {
    fs.copyFileSync(srcDir, destDir);
  }
}

function main() {
  if (!fs.existsSync(src)) {
    console.error('[copy-build] Source build directory not found:', src);
    process.exit(0); // Do not fail the build
  }

  try {
    fs.rmSync(dest, { recursive: true, force: true });
  } catch (e) {
    // ignore
  }

  copyRecursive(src, dest);
  console.log('[copy-build] Copied React build to', dest);
}

main();
