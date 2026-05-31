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

await waitForApp(page);
await page.screenshot({ path: `${outputDir}/sample_audit_false_consensus.png`, fullPage: true });

await clickText(page, "Aggregate Statistics");
await page.screenshot({ path: `${outputDir}/aggregate_statistics.png`, fullPage: true });

await clickText(page, "Submission Readiness");
await page.screenshot({ path: `${outputDir}/submission_readiness.png`, fullPage: true });

await browser.close();

console.log(`English screenshots written to ${outputDir}`);
