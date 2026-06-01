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
await page.screenshot({ path: `${outputDir}/home_system_overview.png`, fullPage: true });

await clickText(page, "Page 2: ESL Feedback Review");
await page.getByText("Run Knowledge-Grounded Feedback", { exact: true }).click();
await page.waitForTimeout(3500);
await page.screenshot({ path: `${outputDir}/esl_feedback_review.png`, fullPage: true });

await clickText(page, "Page 3: Knowledge Grounding & Teacher Queue");
await page.screenshot({ path: `${outputDir}/knowledge_teacher_queue.png`, fullPage: true });

await clickText(page, "Page 5: Risk Dashboard");
await page.screenshot({ path: `${outputDir}/risk_dashboard.png`, fullPage: true });

await clickText(page, "Page 8: Report Export");
await page.screenshot({ path: `${outputDir}/report_export.png`, fullPage: true });

await browser.close();

console.log(`English screenshots written to ${outputDir}`);
