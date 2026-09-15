# Career Platform Implementation Plan

Status: Draft awaiting approval
Date: 2026-09-15

## 1. Planning assumptions

This plan assumes the following implementation direction:
- Python backend: FastAPI
- Templating: Jinja2
- Styling: plain CSS
- Database: SQLite for production deployment, with future portability kept in mind for later migration if needed
- Deployment flow: local Codespace first, then eventual Azure VM deployment
- Public profile visibility is a priority even when the database is unavailable

This plan is for implementation planning only. No build work is included in this document.

## 2. Product goal

Build a database-driven resume and portfolio website that:
- presents a polished public profile to employers and recruiters
- supports structured, admin-controlled edits to resume content
- keeps the public profile visible even during database outages via a degraded-read fallback
- remains flexible enough to expand into a broader career platform later

## 3. Proposed architecture

### 3.1 Runtime
- FastAPI application
- Jinja2 templates for server-rendered HTML pages
- Plain CSS for responsive styling
- SQLite as the primary database for this plan
- Optional cached snapshot or static fallback payload for degraded-read mode

### 3.2 Public-facing flow
- A public page request is served by the FastAPI app.
- If SQLite is available, the app reads live data from the database.
- If SQLite is unavailable, the app serves a last-known-good or static fallback version of profile content.
- End users receive a readable profile instead of a blank page or an internal error.

### 3.3 Admin flow
- Authenticated admin users can access a protected admin dashboard.
- The admin area handles updates to resume content, projects, skills, and profile metadata.
- Public pages render live changes after successful save.

## 4. Task breakdown

### Task 1: Scaffold the FastAPI project structure

Goal:
Create the base app skeleton, dependency setup, runtime config, and local startup flow.

Done looks like:
- The repo has a clean FastAPI app layout.
- A local development server starts without errors.
- Configuration values are externalized into environment settings.
- A basic health route confirms the server is alive.

How to check it:
- Run the app locally.
- Visit the health endpoint and confirm HTTP 200.
- Confirm the app starts with no missing dependency or import errors.

Dependencies:
None.

### Task 2: Create the SQLite schema and data foundation

Goal:
Define the database tables for the profile data model.

Done looks like:
- SQLite database file and schema are created.
- Tables exist for profile, experience, projects, skills, education, certifications, contact methods, and content sections.
- Basic constraints and columns match the spec.
- A setup or migration command exists for recreating the schema.

How to check it:
- Open the database and list tables.
- Confirm the expected schema and essential columns exist.
- Run the schema setup command successfully.

Dependencies:
Task 1.

### Task 3: Build the data access layer

Goal:
Create repository/service logic for reading and writing profile content.

Done looks like:
- Data access functions exist for each entity in the model.
- The backend can create, read, update, and archive records.
- The presentation layer depends on service functions rather than raw SQL scattered across templates.

How to check it:
- Insert sample profile data via the app or SQLite shell.
- Fetch records through the service layer.
- Confirm each entity returns expected values in a structured form.

Dependencies:
Task 2.

### Task 4: Implement admin authentication and authorization

Goal:
Protect admin editing while keeping the public profile accessible.

Done looks like:
- There is a protected admin area requiring authentication.
- Public pages remain readable without login.
- Unauthenticated admin requests are denied or redirected.

How to check it:
- Open the public homepage without logging in and confirm it loads.
- Hit an admin route without credentials and confirm denial.
- Log in and confirm the admin area loads correctly.

Dependencies:
Task 1, Task 3.

### Task 5: Build the admin dashboard

Goal:
Allow the content owner to manage the profile through form-based editing.

Done looks like:
- The admin dashboard includes sections for profile, work experience, projects, skills, education, and contact information.
- The owner can create, edit, publish, and archive records.
- The public site reflects updates after successful save.

How to check it:
- Create a new project or experience entry in admin.
- Confirm it appears on the public site.
- Edit an item and verify the updated content appears without a manual refresh of the application code.
- Archive an item and confirm it disappears from public pages.

Dependencies:
Task 3, Task 4.

### Task 6: Build the public resume and portfolio pages

Goal:
Create the public-facing site that recruiters and employers can view.

Done looks like:
- Public pages exist for home, about, experience, projects, skills, education, and contact.
- Content is rendered from database records rather than static file-only copy.
- Layout is responsive and readable on desktop and mobile.
- Styling is consistent and uses plain CSS.

How to check it:
- Load each public route and confirm its content is displayed correctly.
- Check that all core sections render real content from the database.
- Resize the browser and verify the layout remains readable.

Dependencies:
Task 3, Task 5.

### Task 7: Add degraded-read fallback mode for SQLite outages

Goal:
Ensure the public profile stays visible when the database becomes unavailable.

Done looks like:
- The app can serve a cached or last-known-good snapshot of profile data when SQLite is unreachable.
- Public visitors can still view a readable profile page instead of a blank or broken page.
- No technical error messages are exposed to the public.
- Admin editing may temporarily fail, but public profile visibility stays online.

How to check it:
- Stop or simulate a database outage.
- Request a public page and confirm the fallback content still loads.
- Confirm the page shows readable profile information and no stack trace or raw error output.

Dependencies:
Task 3, Task 6.

### Task 8: Seed realistic content for first-time launch

Goal:
Populate the site with enough data to demonstrate the system before launch.

Done looks like:
- Seed data includes profile summary, experience entries, skill categories, projects, education, and contact links.
- The home and section pages render complete content without requiring manual setup for every item.
- Seed content is clearly separated from production management flows.

How to check it:
- Run the seed step or application startup data load.
- Load the homepage and key pages and verify content appears as expected.
- Confirm the app remains stable even with realistic sample data.

Dependencies:
Task 2, Task 6.

### Task 9: Add validation, sanitization, and edit safety checks

Goal:
Protect the site from malformed content and unsafe input.

Done looks like:
- Required fields and invalid formats are validated before save.
- URLs, dates, and text content are sanitized or rejected when invalid.
- Profiles render safely even with user-supplied text.

How to check it:
- Submit invalid or incomplete data via the admin form.
- Confirm validation errors appear and no bad data is saved.
- Submit valid data and confirm it renders cleanly.

Dependencies:
Task 4, Task 5.

### Task 10: Prepare local and Azure VM deployment readiness

Goal:
Ensure the app can be run locally in Codespaces and later moved to Azure VM hosting.

Done looks like:
- The app can run successfully in the local Codespace environment.
- Configuration is externalized through environment variables and settings files.
- The repo includes deployment notes for how the app would run on an Azure VM later.
- There is a clear separation between local dev, SQLite usage, and future deployment behavior.

How to check it:
- Start the app locally and confirm it serves pages successfully.
- Review the deployment instructions and verify they target future Azure VM hosting.
- Confirm no hard-coded secrets or local-only assumptions remain in the app config.

Dependencies:
All prior tasks.

### Task 11: Run smoke tests and quality pass

Goal:
Verify the app meets the core functional requirements before any broader feature work.

Done looks like:
- The public pages load and render correct data.
- Admin flows work without errors.
- Fallback mode works during a database outage.
- The app is stable enough for a first review.

How to check it:
- Execute end-to-end smoke tests for home page, experience, projects, admin login, and profile editing.
- Simulate a database outage and ensure the public profile remains visible.
- Confirm there are no broken routes, missing sections, or severe UI issues.

Dependencies:
Tasks 5-10.

## 5. Phase plan

### Phase 1: Foundation
- Task 1: scaffold the app
- Task 2: define SQLite schema
- Task 3: build the data access layer

### Phase 2: Editing and public experience
- Task 4: admin auth
- Task 5: admin dashboard
- Task 6: public site pages

### Phase 3: Resilience and readiness
- Task 7: degraded-read fallback mode
- Task 8: seed realistic profile data
- Task 9: validation and safety checks

### Phase 4: Deployment prep
- Task 10: local and Azure VM deployment readiness
- Task 11: smoke tests and final quality pass

## 6. Risks and mitigations

### Risk: SQLite limits scale or durability
Mitigation:
Keep the schema and service design portable, and document a migration path for future database expansion if needed.

### Risk: Public profile fails during database issues
Mitigation:
Use a last-known-good or cached fallback snapshot to preserve site visibility.

### Risk: Admin editing gets too complex too early
Mitigation:
Keep v1 focused on essential resume content and simple admin forms.

### Risk: The product grows beyond MVP scope
Mitigation:
Limit v1 to profile, experience, projects, skills, education, and contact information.

## 7. Exit criteria for approval

This implementation plan is ready to move into build mode when:
- the stack choice is finalized
- the production database decision is approved
- the fallback-read requirement is accepted as a required feature
- local Codespace and Azure VM deployment goals are accepted

## 8. Approval gate

This plan is not a build instruction yet. It is a reviewable implementation plan and requires approval before coding begins.

If you approve this plan, I will begin implementation in the next step.
