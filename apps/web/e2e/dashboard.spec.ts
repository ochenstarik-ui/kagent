import { test, expect } from '@playwright/test';

test.describe('E2E Dashboard', () => {
  const uniqueId = Date.now();
  const testEmail = `testuser_${uniqueId}@example.com`;
  const testPassword = 'password1234';

  test('Unavailable control-plane shows error to user, not blank page', async ({ page }) => {
    // Intercept API to return 503
    await page.route('**/api/control-plane/v1/projects*', async route => {
      await route.fulfill({ status: 503, body: 'Service Unavailable' });
    });

    await page.goto('/');
    
    // Register
    await page.fill('input[type="email"]', `user${uniqueId}@test.com`);
    await page.fill('input[type="password"]', 'pass1234');
    await page.click('button:has-text("Register")');
    
    // Expect error message to be visible
    await expect(page.locator('.error-message')).toBeVisible();
    await expect(page.locator('.error-message')).toContainText('Error');
  });

  test('Wrong password login shows error', async ({ page }) => {
    await page.goto('/');
    await page.fill('input[type="email"]', 'wrong@example.com');
    await page.fill('input[type="password"]', 'wrongpass');
    await page.click('button:has-text("Login")');
    
    await expect(page.locator('.error-message')).toBeVisible();
  });

  test('Full happy path: register, project, task, run', async ({ page }) => {
    await page.goto('/');

    // Register
    await page.fill('input[type="email"]', testEmail);
    await page.fill('input[type="password"]', testPassword);
    await page.click('button:has-text("Register")');

    // Land on dashboard
    await expect(page.locator('text=Project List')).toBeVisible();

    // Create a project
    await page.click('button:has-text("Create Project")');
    await expect(page.locator('.project-item').first()).toBeVisible();

    // Select project and create task
    await page.click('.project-item button:has-text("Select")');
    await expect(page.locator('text=Task List')).toBeVisible();
    
    await page.click('button:has-text("Create Task")');
    await expect(page.locator('.task-item').first()).toBeVisible();

    // Select task and create run
    await page.click('.task-item button:has-text("Select for Run")');
    await expect(page.locator('text=Run View')).toBeVisible();

    // Mock pipeline execute to return a run with human decision required
    await page.route('**/api/pipeline/pipelines/execute', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: `task_${uniqueId}`,
          project_id: `proj_${uniqueId}`,
          status: 'human_required',
          steps: [{ phase: 'planning', description: 'desc', status: 'done' }],
          total_duration_ms: 1000,
          repair_cycles: 0
        })
      });
    });

    await page.click('button:has-text("Create Run")');
    
    // Verify run appears
    await expect(page.locator('.run-item').first()).toBeVisible();
    
    // Check for tokens, cost, steps text
    await expect(page.locator('.run-item').first()).toContainText('Tokens: 0');
    await expect(page.locator('.run-item').first()).toContainText('Cost: $0');
    await expect(page.locator('.run-item').first()).toContainText('Steps: 1');

    // Check for human decision required
    await expect(page.locator('.run-item').first()).toContainText('(Human decision required)');
  });

  test('Create task in nonexistent project does not crash UI', async ({ page }) => {
    await page.goto('/');

    // Register
    await page.fill('input[type="email"]', `erruser${uniqueId}@test.com`);
    await page.fill('input[type="password"]', 'pass1234');
    await page.click('button:has-text("Register")');

    await expect(page.locator('text=Project List')).toBeVisible();

    // Go to Tasks view without selecting a project
    await page.click('button:has-text("Tasks")');
    
    // Click create task
    await page.click('button:has-text("Create Task")');
    
    // UI should not crash, it should just return (we handle it by `if (!selectedProjectId) return;`)
    // Just verify the task list is still there
    await expect(page.locator('text=Task List')).toBeVisible();
  });
});
