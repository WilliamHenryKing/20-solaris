// biome-ignore-all lint: Standalone browser verification runs DOM probes in Chromium.
const fs = require("node:fs");
const path = require("node:path");
const project = path.resolve(__dirname, "..");
const slug = require(path.join(project, "package.json")).name;
const baseArg = process.argv[2];
const { chromium } = require(path.join(project, "node_modules/playwright"));
const port = Number(slug.slice(0, 2)) + 4610;
const base = baseArg || `http://127.0.0.1:${port}`;
const out = path.join(project, "output/playwright");
fs.mkdirSync(out, { recursive: true });
const report = {
  slug,
  base,
  date: new Date().toISOString(),
  checks: [],
  errors: [],
  routes: [],
  accessibility: [],
  diagnostics: [],
};
let browserInstance;
function check(name, pass, detail) {
  report.checks.push({ name, pass: !!pass, ...(detail ? { detail } : {}) });
}
(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  browserInstance = browser;
  report.browser = browser.version();
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  page.on("pageerror", (e) => report.errors.push(e.message));
  page.on("console", (m) => {
    if (m.type() === "error") report.errors.push(m.text());
  });
  page.on("response", (r) => {
    if (r.status() >= 400) report.errors.push(`${r.status()} ${r.url()}`);
  });
  const diagnostic = () =>
    page.evaluate(
      () =>
        window.__SOLARIS_DIAGNOSTICS__ ||
        window.__AUREL_DIAGNOSTICS__ ||
        window.__STRATA_DIAGNOSTICS__ ||
        null,
    );
  const screenshot = async (name) => page.screenshot({ path: path.join(out, name + ".png") });
  const audit = async (name) => {
    await page.addScriptTag({ path: path.join(project, "node_modules/axe-core/axe.min.js") });
    const violations = await page.evaluate(async () =>
      (
        await window.axe.run(document, {
          runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] },
        })
      ).violations.map((v) => ({
        id: v.id,
        impact: v.impact,
        nodes: v.nodes.map((n) => ({ target: n.target, summary: n.failureSummary })),
      })),
    );
    report.accessibility.push({ name, violations });
    check(name + " axe A/AA", !violations.length);
  };
  await page.goto(base, { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);
  const homeLinks = await page
    .locator('a[href^="#/"]')
    .evaluateAll((es) => es.map((e) => e.getAttribute("href")));
  const nav = [...new Set(homeLinks)].filter((x) => x !== "#/" && x !== "#/home");
  const gallery = slug === "19-strata" ? "#/work" : "#/projects";
  await page.goto(base + gallery, { waitUntil: "networkidle" });
  await page.waitForTimeout(600);
  const details = await page
    .locator(`a[href^="${gallery}/"]`)
    .evaluateAll((es) => es.map((e) => e.getAttribute("href")));
  const routes = [...new Set(["#/", gallery, ...nav, ...details])];
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: width === 1440 ? 900 : 844 });
    for (const route of routes) {
      await page.goto(base + route, { waitUntil: "networkidle" });
      await page.waitForTimeout(500);
      const height = await page.evaluate(() => document.documentElement.scrollHeight);
      for (let y = 0; y < height; y += 650) {
        await page.evaluate((y) => scrollTo({ top: y, behavior: "instant" }), y);
        await page.waitForTimeout(90);
      }
      await page.waitForTimeout(350);
      const broken = await page
        .locator("img")
        .evaluateAll((es) =>
          es.filter((e) => !e.complete || e.naturalWidth === 0).map((e) => e.currentSrc),
        );
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth + 1,
      );
      const title = await page.title();
      const headings = await page.locator("h1").allTextContents();
      check(`${width} ${route} no overflow`, !overflow);
      check(`${width} ${route} images loaded`, !broken.length, broken);
      check(
        `${width} ${route} single nonempty heading`,
        headings.length === 1 && headings[0].trim().length > 0,
      );
      report.routes.push({ width, route, title, headings, broken, overflow });
      await page.evaluate(() => scrollTo({ top: 0, behavior: "instant" }));
      await page.waitForTimeout(800);
      await screenshot(`${width}-${route.replace(/[^a-z0-9]+/gi, "-") || "home"}`);
      if (
        route === "#/" ||
        route === gallery ||
        route.includes("contact") ||
        route.includes("enquiry")
      )
        await audit(`${width} ${route}`);
    }
  }
  // Filters are real buttons; selecting one must change the gallery and preserve usable cards.
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(base + gallery, { waitUntil: "networkidle" });
  const filterButtons = page.locator(
    ".filters button,.project-filters button,.filter-bar button,.filter-list button",
  );
  if ((await filterButtons.count()) > 1) {
    await filterButtons.nth(1).click();
    check(
      "Gallery filter selects",
      (await filterButtons.nth(1).getAttribute("aria-pressed")) === "true" ||
        (await filterButtons.nth(1).getAttribute("aria-selected")) === "true",
    );
    check(
      "Filtered gallery retains a project",
      (await page.locator(`a[href^="${gallery}/"]`).count()) > 0,
    );
  }
  // The downloadable brief is the actual enquiry outcome; inspect downloaded text.
  const contact = routes.find((r) => /contact|enquiry|brief/.test(r));
  if (contact) {
    await page.goto(base + contact, { waitUntil: "networkidle" });
    const selects = page.locator("select");
    const expected = [];
    for (let i = 0; i < (await selects.count()); i++) {
      const sel = selects.nth(i);
      const val =
        (await sel.locator("option").last().getAttribute("value")) ||
        (await sel.locator("option").last().textContent());
      await sel.selectOption({ label: await sel.locator("option").last().textContent() });
      expected.push(val);
    }
    const textarea = page.locator("textarea");
    if (await textarea.count()) {
      await textarea.fill("A quiet reading room with tactile stone and natural light.");
      expected.push("A quiet reading room");
    }
    if (slug === "19-strata") await page.locator('form button[type="submit"]').click();
    const downloadPromise = page.waitForEvent("download");
    if (slug === "19-strata") await page.getByRole("button", { name: /download.*brief/i }).click();
    else await page.locator('form button[type="submit"]').click();
    const download = await downloadPromise;
    const file = path.join(out, download.suggestedFilename());
    await download.saveAs(file);
    const text = fs.readFileSync(file, "utf8");
    check("Brief downloads text file", download.suggestedFilename().endsWith(".txt"));
    check(
      "Brief includes selected choices",
      expected.every((s) => text.includes(s)),
    );
    check("Brief confirms local demo", /nothing|no.*sent|not.*sent|concept|fictional/i.test(text));
  }
  // Phone menu and keyboard dismissal.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(base, { waitUntil: "networkidle" });
  await page.waitForTimeout(2200);
  const menu = page.locator("header button[aria-expanded]").first();
  if (await menu.isVisible()) {
    await menu.click();
    check("Phone menu opens", (await menu.getAttribute("aria-expanded")) === "true");
    await screenshot("mobile-menu");
    await audit("mobile menu");
    await page.keyboard.press("Escape");
    check("Escape closes phone menu", (await menu.getAttribute("aria-expanded")) === "false");
    await menu.click();
    const navLink = page
      .locator("header nav a")
      .filter({ hasText: /project|work/i })
      .first();
    if (await navLink.count()) {
      await navLink.click();
      check("Phone menu navigation changes route", page.url().includes(gallery));
      check(
        "Phone menu closes after navigation",
        (await menu.getAttribute("aria-expanded")) === "false",
      );
    }
  }
  // Native motion preference remains functional while app is running.
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(base, { waitUntil: "networkidle" });
  await page.waitForTimeout(350);
  await screenshot("reduced-motion");
  check("Reduced-motion home remains readable", await page.locator("h1").isVisible());
  const motion = page.getByRole("button", { name: /motion|animation/i }).first();
  if (await motion.count()) report.reducedMotionControl = await motion.textContent();
  // Inspect actual Three controls; render must respond then pause when out of view.
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(base, { waitUntil: "networkidle" });
  if (slug === "20-solaris") {
    await page.locator(".pavilion-lazy,.pavilion-section").first().scrollIntoViewIfNeeded();
    await page.locator(".scene-host canvas").waitFor();
    await page.locator(".pavilion-section").scrollIntoViewIfNeeded();
    await page.waitForTimeout(600);
    const sun = page.getByRole("slider");
    await sun.focus();
    await page.keyboard.press("End");
    await page.waitForTimeout(250);
    check("Sun changes to evening", (await diagnostic()).sun === 100);
    await screenshot("pavilion-evening");
    await page.getByRole("button", { name: "Courtyard", exact: true }).click();
    await page.waitForTimeout(400);
    check("Courtyard camera selected", (await diagnostic()).view === 1);
    await screenshot("pavilion-courtyard");
    await page.getByRole("button", { name: "Above", exact: true }).click();
    await page.waitForTimeout(400);
    check("Above camera selected", (await diagnostic()).view === 2);
    await screenshot("pavilion-above");
  } else if (slug === "19-strata") {
    for (const name of ["Clay plaster", "Smoked walnut", "Brushed metal"]) {
      const b = page.getByRole("button", { name: "Explore " + name, exact: true }).first();
      await b.click();
      await page.waitForTimeout(1200);
      check("Material " + name + " selected", (await b.getAttribute("aria-pressed")) === "true");
      await screenshot("material-" + name.toLowerCase().replace(/ /g, "-"));
    }
  } else {
    const lightRoute = routes.find((r) => /light/.test(r));
    if (lightRoute) {
      await page.goto(base + lightRoute, { waitUntil: "networkidle" });
      await page.waitForTimeout(1500);
      await screenshot("light-study-active");
      await page.getByRole("button", { name: "Daylight", exact: false }).click();
      await page.waitForTimeout(650);
      check("Daylight mode changes", (await diagnostic()).mode === "daylight");
      await page.getByRole("button", { name: "Basalt", exact: true }).click();
      await page.waitForTimeout(650);
      check("Basalt finish changes", (await diagnostic()).finish === "basalt");
      await page.getByRole("button", { name: "View pavilion from further right" }).click();
      await page.waitForTimeout(500);
      await page
        .locator(".light-experience")
        .screenshot({ path: path.join(out, "light-basalt-day.png") });
    }
  }
  report.diagnostics.push(await diagnostic());
  await page.evaluate(() =>
    scrollTo({ top: document.documentElement.scrollHeight, behavior: "instant" }),
  );
  await page.waitForTimeout(500);
  report.diagnostics.push(await diagnostic());
  await page.goto(base + "#/unknown-review-page", { waitUntil: "networkidle" });
  check(
    "Unknown hash route is handled",
    /not found|outside|lost|404|not.*plan|unopened/i.test(
      (await page.locator("main").textContent()) + " " + (await page.title()),
    ),
  );
  await browser.close();
  check("No browser/network errors", report.errors.length === 0, report.errors);
  fs.writeFileSync(path.join(out, "verification.json"), JSON.stringify(report, null, 2));
  console.log(
    JSON.stringify(
      {
        checks: report.checks.length,
        failed: report.checks.filter((x) => !x.pass),
        errors: report.errors,
        accessibility: report.accessibility.filter((x) => x.violations.length),
        diagnostics: report.diagnostics,
      },
      null,
      2,
    ),
  );
  if (report.checks.some((x) => !x.pass)) process.exitCode = 1;
})().catch(async (e) => {
  fs.writeFileSync(
    path.join(out, "verification-incomplete.json"),
    JSON.stringify({ ...report, fatal: String(e) }, null, 2),
  );
  console.error(e);
  await browserInstance?.close();
  process.exitCode = 1;
});
