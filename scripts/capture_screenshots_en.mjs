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
const path = await import("node:path");

const baseUrl =
  process.env.CONSENSUS_SCOPE_URL ||
  `file://${path.resolve("ui_prototype/index.html")}`;
const outputDir = "docs/screenshots_en";

async function waitForApp(page) {
  await page.goto(baseUrl, { waitUntil: "networkidle", timeout: 60000 });
  await page.getByText("ConsensusScope").first().waitFor({ timeout: 60000 });
  await page.waitForTimeout(1200);
}

async function clickText(page, text) {
  await page.getByText(text, { exact: true }).click();
  await page.waitForTimeout(1200);
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
await fs.mkdir(outputDir, { recursive: true });

await waitForApp(page);
await page.screenshot({ path: `${outputDir}/review_workspace.png`, fullPage: true });

await clickText(page, "Page 2: Essay Review");
await page.screenshot({ path: `${outputDir}/essay_review.png`, fullPage: true });

await clickText(page, "Page 3: Feedback Detail");
await page.screenshot({ path: `${outputDir}/feedback_detail.png`, fullPage: true });

await clickText(page, "Page 4: Teacher Queue");
await page.screenshot({ path: `${outputDir}/teacher_queue.png`, fullPage: true });

await clickText(page, "Page 5: Writing Rubric");
await page.screenshot({ path: `${outputDir}/writing_rubric.png`, fullPage: true });

await clickText(page, "Page 6: Reports");
await page.screenshot({ path: `${outputDir}/reports.png`, fullPage: true });

await browser.close();

console.log(`English screenshots written to ${outputDir}`);
