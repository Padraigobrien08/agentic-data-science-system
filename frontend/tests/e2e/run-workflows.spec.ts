import { expect, test } from "@playwright/test";

import { getFixture } from "./fixture";

test("run answer, deep dive, and artifact delivery stay reachable", async ({ page }) => {
  const fixture = getFixture();
  const runPath = `/projects/${fixture.project_id}/runs/${fixture.run_id}`;
  const tracePath = `${runPath}/trace`;

  // The standalone run page now redirects to the deep-dive trace surface, which
  // renders the "Deep dive" heading.
  await page.goto(runPath);
  await expect(page).toHaveURL(new RegExp(`${tracePath}$`));
  await expect(page.getByRole("heading", { name: "Deep dive" })).toBeVisible();

  // Artifact delivery streams the run's report inline. That report content is the
  // run answer itself (the takeaway) plus the delivery marker, so it verifies both
  // the run answer content and artifact delivery are reachable after auth.
  const artifactPage = await page.context().newPage();
  await artifactPage.goto(`/api/artifacts/${fixture.artifact_id}/content?disposition=inline`);
  const body = artifactPage.locator("body");
  await expect(body).toContainText("Seeded browser fixture takeaway.");
  await expect(body).toContainText("Seeded artifact content for CI browser test.");
  await artifactPage.close();
});
