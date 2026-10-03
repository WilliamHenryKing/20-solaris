import { createHash } from "node:crypto";
import { mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import { chromium } from "playwright";

const base = process.argv[2];
if (!base) throw new Error("Supply live URL");
const report = { base, checkedAt: new Date().toISOString(), files: [], errors: [] };
const digest = (data) => createHash("sha256").update(data).digest("hex");
const list = async (dir) =>
  (
    await Promise.all(
      (
        await readdir(dir, { withFileTypes: true })
      )
        .filter((e) => !e.name.startsWith(".") && !e.name.startsWith("_"))
        .map(async (e) => (e.isDirectory() ? list(`${dir}/${e.name}`) : `${dir}/${e.name}`)),
    )
  ).flat();
for (const file of await list("dist")) {
  const route = file.slice(4);
  const response = await fetch(`${base}${route === "/index.html" ? "/" : route}`);
  const bytes = Buffer.from(await response.arrayBuffer());
  const matched = digest(bytes) === digest(await readFile(file));
  report.files.push({ path: route, status: response.status, matched, bytes: bytes.length });
  if (!matched) throw new Error(`Live mismatch: ${route}`);
}
report.notFoundStatus = (await fetch(`${base}/this-page-does-not-exist`)).status;
if (report.notFoundStatus !== 404) throw new Error("Missing route should return 404");
report.release = await (await fetch(`${base}/release.json`)).json();
const browser = await chromium.launch({ channel: "chrome", headless: true });
for (const [label, width, height] of [
  ["desktop", 1440, 900],
  ["phone", 390, 844],
]) {
  const context = await browser.newContext({ viewport: { width, height } });
  const page = await context.newPage();
  page.on("pageerror", (e) => report.errors.push(e.message));
  await page.goto(base, { waitUntil: "networkidle" });
  await page.waitForTimeout(3500);
  report[label] = {
    title: await page.title(),
    overflow: await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1),
    resources: await page.evaluate(() =>
      performance.getEntriesByType("resource").map((r) => ({
        name: new URL(r.name).pathname,
        encoded: r.encodedBodySize,
        transfer: r.transferSize,
      })),
    ),
    paint: await page.evaluate(() =>
      performance.getEntriesByType("paint").map((r) => ({ name: r.name, startTime: r.startTime })),
    ),
  };
  await mkdir("output/playwright", { recursive: true });
  await page.screenshot({ path: `output/playwright/live-${label}.png` });
  await context.close();
}
await browser.close();
if (report.errors.length || report.desktop.overflow || report.phone.overflow)
  throw new Error("Live browser checks failed");
await writeFile("output/playwright/live-report.json", JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
