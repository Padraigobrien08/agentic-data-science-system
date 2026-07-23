import { expect, test } from "@playwright/test";

import { getFixture } from "./fixture";

test("run answer, deep dive, and artifact delivery stay reachable", async ({ page }) => {
  const fixture = getFixture();
  const chatPath = `/projects/${fixture.project_id}/chat`;
  const runPath = `/projects/${fixture.project_id}/runs/${fixture.run_id}`;
  const tracePath = `${runPath}/trace`;

  // The run answer is reachable in the conversation-first chat surface, where
  // completed runs hydrate into answer cards.
  await page.goto(chatPath);
  await expect(page.getByText("Seeded browser fixture takeaway.")).toBeVisible();

  // The standalone run page now redirects to the deep-dive trace surface.
  await page.goto(runPath);
  await expect(page).toHaveURL(new RegExp(`${tracePath}$`));
  await expect(page.getByRole("heading", { name: "Deep dive" })).toBeVisible();

  const artifactPage = await page.context().newPage();
  await artifactPage.goto(`/api/artifacts/${fixture.artifact_id}/content?disposition=inline`);
  await expect(artifactPage.locator("body")).toContainText(
    "Seeded artifact content for CI browser test.",
  );
  await artifactPage.close();
});
