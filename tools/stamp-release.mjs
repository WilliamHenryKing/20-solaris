import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";

const project = JSON.parse(readFileSync("package.json", "utf8")).name;
const sourceCommit = execFileSync("git", ["rev-parse", "HEAD"], { encoding: "utf8" }).trim();
const release = { project, sourceCommit, builtAt: new Date().toISOString() };
writeFileSync("dist/release.json", `${JSON.stringify(release, null, 2)}\n`);
console.log(`Release source: ${sourceCommit}`);
