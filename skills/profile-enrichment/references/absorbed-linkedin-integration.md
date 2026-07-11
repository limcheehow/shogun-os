# LinkedIn Integration — Historical Reference (Absorbed)

Three LinkedIn skills were consolidated into `profile-enrichment` as the canonical pipeline:

## `linkedin-integration` (social-media category, archived)
Old comprehensive LinkedIn integration with mock data, daily connections/followers tracking, API setup. **DEPRECATED** — all mock data was harmful. LinkedIn enrichment now happens via browser-use CDP (real Chrome session) on a per-person basis, not aggregate daily files.

Key takeaway: **Do NOT create aggregate LinkedIn daily files.** Profile info belongs in individual person files, not daily rollups.

## `linkedin-composio-integration` (social-media category, archived)
Composio CLI setup for LinkedIn. Noted limitations:
- `LINKEDIN_GET_PERSON` often returns 403 (target member's privacy settings)
- Personal connections, followers, and contact lists are NOT available
- Only works reliably: `GET_MY_INFO`, `CREATE_ARTICLE_OR_URL_SHARE`, `GET_NETWORK_SIZE`

**Replaced by** browser-use CDP which provides full logged-in LinkedIn access.

## `linkedin-brain-integration` (productivity category, archived)
v2 integration that v1's approach was deprecated. Now LinkedIn enrichment is handled by `profile-enrichment` skill (v1.2.0+) which uses browser-use CDP. All brain-enrichment cron jobs (email digest, calendar sync, meeting agent) load `profile-enrichment`.

References for more detail:
- `profile-enrichment` skill's `references/friends-family-enrichment.md` for Facebook/social export enrichment
- `browser-use` skill for CDP setup and LinkedIn profile extraction