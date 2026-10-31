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
YouTube often answers home IPs with "Sign in to confirm you're not a bot". Giving the server
cookies from a signed-in browser gets past it:

1. In a private/incognito window, sign in to YouTube, ideally with a spare Google account
   (YouTube can flag accounts used this way).
2. Export the youtube.com cookies in Netscape `cookies.txt` format with an extension such as
   "Get cookies.txt LOCALLY", then close the private window without signing out.
3. Save the file as `cookies/cookies.txt` next to `docker-compose.yml` and restart the container.

The file is optional and mounted read-only; the log says at startup whether it was found.
Export fresh cookies if the bot check comes back. See the
[yt-dlp guide](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies).

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
