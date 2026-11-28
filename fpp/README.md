# FPP request recorder

The recorder that fills `stats.json` (for the page's "Hot tonight" and "Fan favorites") is an FPP plugin
running on the show player (fpp-player, 192.168.5.41). Its code lives in its own repo:

**https://github.com/mryan231991/fpp-plugin-rrl-recorder**

To set it up on a fresh Pi: FPP → Content Setup → Plugin Manager, load
`https://github.com/mryan231991/fpp-plugin-rrl-recorder`, install, then paste a GitHub token on
Content Setup → Request Recorder. Full steps are in that repo's README.

The GitHub Actions recorder in `.github/workflows/recorder.yml` is the older backup.
