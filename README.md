# Rocky Ridge Lights viewer page

Self-hosted song request page for Rocky Ridge Lights (Leesburg, VA).

- `index.html` is the whole site. It talks to Remote Falcon's public viewer API from the visitor's
  phone, so Remote Falcon's own request/vote limits still apply.
- Edit the `SETTINGS` block near the bottom of `index.html` for show hours, season dates and text.
  Songs, categories and album art come from Remote Falcon automatically.
- Hosted on GitHub Pages. To send visitors here, set Remote Falcon → Control Panel → Viewer Page →
  **Self Hosted Redirect URL** to this site's address. Clear that field to fall back to the Remote Falcon page.
