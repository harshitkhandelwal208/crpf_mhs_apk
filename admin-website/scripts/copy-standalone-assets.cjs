const fs = require("node:fs");
const path = require("node:path");

const projectRoot = path.resolve(__dirname, "..");
const standaloneRoot = path.join(projectRoot, ".next", "standalone");

if (!fs.existsSync(path.join(standaloneRoot, "server.js"))) {
  throw new Error(
    "Next standalone output is missing. Run this script after `next build`.",
  );
}

const copies = [
  {
    source: path.join(projectRoot, ".next", "static"),
    destination: path.join(standaloneRoot, ".next", "static"),
  },
  {
    source: path.join(projectRoot, "public"),
    destination: path.join(standaloneRoot, "public"),
  },
];

for (const { source, destination } of copies) {
  if (!fs.existsSync(source)) {
    throw new Error(`Required build asset directory is missing: ${source}`);
  }

  fs.rmSync(destination, { recursive: true, force: true });
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  fs.cpSync(source, destination, { recursive: true, force: true });
}

console.log("Copied static and public assets into .next/standalone.");
