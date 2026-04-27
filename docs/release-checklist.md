# Release Checklist

## Security
- [ ] Rotate `SECRET_KEY` for production and keep it outside committed files.
- [ ] Move cloud credentials to deployment secret manager.
- [ ] Ensure CORS allows only frontend domain(s) in production.
- [ ] Verify rate limits for auth, follow, like, comment, upload, and messaging endpoints.
- [ ] Confirm password hashing and token expiry settings are production-safe.

## Backend
- [ ] Run migrations against the single production database target.
- [ ] Verify `/users/login`, `/users/refresh`, and `/users/logout` flows.
- [ ] Verify `/users/search` and `/posts/tag/{tag_name}` responses.
- [ ] Validate media upload for image and video with Cloudinary.
- [ ] Run API smoke tests against deployed environment.

## Frontend
- [ ] Validate login/register/profile/search/tag pages on mobile and desktop.
- [ ] Validate feed infinite scroll and post detail media behavior.
- [ ] Validate moderation actions (mute/block/report) UX messages.
- [ ] Ensure all critical pages show clear empty and error states.
- [ ] Build frontend with no TypeScript errors.

## Testing
- [ ] Run backend test suite:
  - `python -m pytest backend/tests -q`
- [ ] Ensure search and tag tests pass.
- [ ] Add regression tests for bug fixes before release.

## Observability
- [ ] Enable application error tracking (Sentry or equivalent).
- [ ] Enable access/error logs and retention policy.
- [ ] Add uptime and health monitoring for API and frontend.

## Deployment
- [ ] Prepare rollback plan (last known good image/release).
- [ ] Run post-deploy smoke checks (auth, feed, post create, DM, search).
- [ ] Announce release notes and known limitations.
