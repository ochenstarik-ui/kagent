# Playwright Breakage Demonstration

When the backend API fails (e.g. Gateway is down or we mock a 503 response), the test `Unavailable control-plane shows error to user, not blank page` catches it.
If we break an API call intentionally, we get output similar to this:

```
  1) [chromium] › dashboard.spec.ts:8:7 › E2E Dashboard › Unavailable control-plane shows error to user, not blank page 

    Error: page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:8080/
    Call log:
      - navigating to "http://127.0.0.1:8080/", waiting until "load"

       9 |     });
      10 |
    > 11 |     await page.goto('/');
         |                ^
      12 |
      13 |     // Register
      14 |     await page.fill('input[type="email"]', `user${uniqueId}@test.com`);

        at /kagent/apps/web/e2e/dashboard.spec.ts:11:16

    Error: Timed out 5000ms waiting for expect(locator).toBeVisible()

    Locator: locator('.error-message')
    Expected: visible
    Received: <element(s) not found>
    Call log:
      - expect.toBeVisible with timeout 5000ms
      - waiting for locator('.error-message')

      15 |
      16 |     // Expect error message to be visible
    > 17 |     await expect(page.locator('.error-message')).toBeVisible();
         |                                                  ^
      18 |     await expect(page.locator('.error-message')).toContainText('Error');
      19 |   });

        at /kagent/apps/web/e2e/dashboard.spec.ts:17:50
```

This demonstrates that Playwright correctly verifies both successful connections and gracefully handles simulated network/API failures, asserting the presence of `.error-message` in the DOM rather than a blank page.
