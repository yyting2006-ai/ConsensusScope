const PLAYWRIGHT_PATH =
  "/Users/youtingrui/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs";

async function loadPlaywright() {
  try {
    return await import("playwright");
  } catch {
    return await import(PLAYWRIGHT_PATH);
  }
}

const { chromium } = await loadPlaywright();
const fs = await import("node:fs/promises");

const baseUrl = process.env.CONSENSUS_SCOPE_URL || "http://localhost:8502";
const demoPassword = process.env.CONSENSUS_SCOPE_DEMO_PASSWORD || "";
const outputPath = "docs/demo_video_draft_en.webm";
const demoPages = [
  "Page 2: Single Essay Review",
  "Page 3: Batch Review",
  "Page 4: AI Feedback Comparison",
  "Page 5: Teacher Queue",
  "Page 6: Effectiveness Evaluation",
  "Page 7: Reports",
];

async function pause(ms) {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

async function clickText(page, text) {
  await page.getByText(text, { exact: true }).click();
  await pause(2500);
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1100 },
  recordVideo: {
    dir: "docs",
    size: { width: 1440, height: 1100 },
  },
});
const page = await context.newPage();

await page.goto(baseUrl, { waitUntil: "networkidle", timeout: 60000 });
await page.getByText("ConsensusScope").first().waitFor({ timeout: 60000 });

if (demoPassword) {
  const passwordInput = page.getByLabel("Demo password");
  if (await passwordInput.count()) {
    await passwordInput.fill(demoPassword);
    await page.getByRole("button", { name: "Unlock demo" }).click();
    await page.getByText("Page 1: Review Workspace", { exact: true }).waitFor({ timeout: 60000 });
  }
}
await pause(4500);

for (const label of demoPages) {
  await clickText(page, label);
}
await pause(2500);

const video = page.video();
await context.close();
await browser.close();

if (!video) {
  throw new Error("Playwright did not create a video artifact.");
}

const tempPath = await video.path();
await fs.rename(tempPath, outputPath);
console.log(`English draft video written to ${outputPath}`);
