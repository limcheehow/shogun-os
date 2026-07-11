# Content Extraction Troubleshooting

## Fallback Chain (priority order)

```
web_extract(url)         — fast, try first
  ↓ fail?
browser_navigate(url)
  → browser_snapshot     — text extraction, works on most pages
  → browser_vision()     — visible-content extraction, works on SPAs
    ↓ fail?
skip → note in person file
```

## Common web_extract Failure Patterns

### Firecrawl Gateway: AUTH_ERROR / Unauthorized

The Nous-managed Firecrawl gateway may return `Unauthorized` even when
`check_firecrawl_api_key()` reports the tool as available. This happens
when the subscription token isn't routed correctly through the gateway.

**Fix:** Don't retry `web_extract` — switch immediately to browser
navigation. The error is consistent per session.

### Firecrawl Gateway: timeout

Occasional timeouts on large or slow pages. Retry once with browser
fallback if the failure persists.

### Firecrawl Gateway: rate limited

If multiple `web_extract` calls in quick succession start returning
`429` or `rate_limit_exceeded`, insert 2-second pauses between calls
or switch to browser fallback for subsequent pages.

## Browser Extraction Per Site Type

| Site Type | Best Method | Notes |
|-----------|-------------|-------|
| Static HTML site | `browser_navigate` → `browser_snapshot` | Fast, complete text |
| SPA (React/Vue) | `browser_navigate` → `browser_vision` | snapshot truncates; vision reads visible content only |
| Paywall / login wall | `browser_vision` only | text extraction blocked; vision sees what user sees |
| CAPTCHA/Cloudflare | Skip | Neither web_extract nor browser will work |
