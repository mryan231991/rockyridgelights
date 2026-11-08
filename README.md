# Rocky Ridge Lights viewer page

Self-hosted song request page for Rocky Ridge Lights (Leesburg, VA).

- `index.html` is the whole site. It talks to Remote Falcon's public viewer API from the visitor's
  phone, so Remote Falcon's own request/vote limits still apply.
- Edit the `SETTINGS` block near the bottom of `index.html` for show hours, season dates and text.
  Songs, categories and album art come from Remote Falcon automatically.
- Hosted on GitHub Pages. To send visitors here, set Remote Falcon → Control Panel → Viewer Page →
  **Self Hosted Redirect URL** to this site's address. Clear that field to fall back to the Remote Falcon page.

## Request recorder

`.github/workflows/recorder.yml` runs every day from September through January, starting at 4:30 PM EST
(5:30 PM during daylight time). `scripts/recorder.mjs` checks Remote Falcon's public queue every 15 seconds,
counts each new request and each song played, and commits the totals to `stats.json` every ~10 minutes.
It stops 20 minutes after the show turns off (or after 3 hours if the show never turns on).
The page uses `stats.json` for the 🔥 Hot tonight and ⭐ Fan favorites badges and filters.
Run it by hand from the repo's **Actions** tab → *Record song requests* → **Run workflow**.
