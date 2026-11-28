# FPP request recorder

These run on the show's FPP player (fpp-player, 192.168.5.41) and record song requests from
Remote Falcon into `stats.json`, which the viewer page uses for "Hot tonight" and "Fan favorites".

| File | What it is |
|---|---|
| `rrl_recorder.py` | The recorder. Polls Remote Falcon every 15 s during the show and saves to `stats.json` every 10 min. |
| `rrl_recorder.sh` | Launcher the FPP schedule runs (Run Script, 4:50 PM nightly). Starts the recorder in the background, one copy at a time. Argument `test` checks the token and Remote Falcon without recording. |
| `rrl_token.sh` | Holds the GitHub token. **The copy here is a blank template. Never commit the real token.** |

## Setting up a fresh Pi

1. Upload all three files in FPP: Content Setup → File Manager → Scripts.
2. Create a fine-grained GitHub token: only this repo, permission **Contents: Read and write**.
   Paste it into `rrl_token.sh` on the Pi.
3. In FPP's Scheduler, add a **Command** entry for every show night: `Run Script`, script `rrl_recorder.sh`,
   start 4:50 PM (end time the same), before the 4:55 PM "Turn Viewer Control On" entry.
4. Test: run `rrl_recorder.sh` with argument `test`, then read
   `/home/fpp/media/logs/rrl_recorder.log` (File Manager → Logs). It should end with `TEST PASSED`.

The recorder stops 20 minutes after Viewer Control turns off, or at 10:30 PM if the show never turned on.
Requests are counted per show night (rolling over at 6 AM Eastern) and per month.
