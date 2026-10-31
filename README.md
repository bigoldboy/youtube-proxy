# youtube-proxy
Play YouTube live streams in any IPTV player. A small Flask server uses
[yt-dlp](https://github.com/yt-dlp/yt-dlp) to pull the live stream and pipes it to the player.

Forked from [purplescorpion1/youtube-to-m3u](https://github.com/purplescorpion1/youtube-to-m3u).

## Important note
Stream links only play on clients with the same public IP (same local network) as the server.
To watch from another network, restream through an m3u proxy such as Threadfin.

## Run with Docker
The image is published to `ghcr.io/bigoldboy/youtube-proxy:latest` (amd64 and arm64)
on every push to `main`, and rebuilt weekly so yt-dlp stays current.

```yaml
services:
  youtube-proxy:
    image: ghcr.io/bigoldboy/youtube-proxy:latest
    container_name: youtube-proxy
    ports:
      - "6095:6095"
    volumes:
      - ./cookies:/cookies:ro
    restart: unless-stopped
```

To update: `docker compose pull && docker compose up -d`.

## YouTube cookies
YouTube often answers home IPs with "Sign in to confirm you're not a bot", and the log shows
`[YT-DLP ERROR] ... Sign in to confirm you're not a bot`. The fix is to give the server the
cookies from a browser that is signed in to YouTube.

> **Never commit `cookies.txt` or share it.** It works like a password for that Google account.
> `.gitignore` already excludes it from this repo.

### Export the cookies (Firefox)
1. Install the [cookies.txt](https://addons.mozilla.org/firefox/addon/cookies-txt/) add-on and
   tick **Allow in private windows** when asked (or later: Add-ons → cookies.txt →
   Run in Private Windows → Allow).
2. Open a **private window** (Ctrl+Shift+P) and sign in to youtube.com. A spare Google account
   is safer, because YouTube can flag accounts used this way.
3. In that same tab, go to `https://www.youtube.com/robots.txt`. This stops YouTube from
   changing the cookies while you export.
4. Click the cookies.txt icon, choose **Current site**, and save.
5. Close the private window. Don't sign out, or the cookies stop working.

In Chrome or Edge, the "Get cookies.txt LOCALLY" extension does the same job.

### Put the file in place
- The add-on saves private-window cookies as `cookies.firefox-private.txt`. **Rename it to exactly
  `cookies.txt`.** On Windows, turn on View → Show → File name extensions first, so you don't
  end up with `cookies.txt.txt`.
- Open it in Notepad to check it. It should have lines starting with `.youtube.com`, including
  `SID` or `__Secure-3PSID`. If it's nearly empty, you exported from the wrong window.
- Put it in a folder on the Docker host and mount that folder at `/cookies` in the compose file:

  ```yaml
      volumes:
        - D:/docker/youtube-proxy/cookies:/cookies:ro   # folder that holds cookies.txt
  ```

- Restart the container. The log should say `Using cookies from /cookies/cookies.txt`.

### When the bot error comes back
The cookies have expired. Repeat the export above, replace `cookies.txt`, and restart the
container. You don't need a new image for this. More detail is in the
[yt-dlp guide](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies).

### Other errors
If a stream fails, the error from yt-dlp is in the container log and in the `/stream` response.
If it isn't the bot check, YouTube has usually changed something and a newer yt-dlp fixes it:
pull the latest image, or run the workflow manually from the Actions tab.

## Playlist
Edit `youtubelive.m3u`: change the IP address to the machine running the server, then load
the file into your player. Add streams in this format:

```
#EXTINF:-1 tvg-name="Channel Name" tvg-id="24.7.Dummy.us" tvg-logo="https://example.com/logo.png" group-title="YouTube",Channel Name
http://192.168.1.123:6095/stream?url=https://www.youtube.com/@ChannelName/live
```

Use `@ChannelName/live` links where possible. `/watch?` links also work, but they change whenever
the channel stops and restarts a broadcast. Set `tvg-id` to match your EPG's id for the channel.

## Run without Docker
Requires Python 3.10+, ffmpeg and deno on the path, and:

```
pip install flask "yt-dlp[default]"
COOKIES_FILE=/path/to/cookies.txt python3 youtube-live.py
```
