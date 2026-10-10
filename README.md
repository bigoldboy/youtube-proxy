# youtube-proxy
Play YouTube live streams in any IPTV player. A small Flask server uses
[streamlink](https://streamlink.github.io/) to pull the live stream and pipes it to the player.

Forked from [purplescorpion1/youtube-to-m3u](https://github.com/purplescorpion1/youtube-to-m3u).

## Important note
Stream links only play on clients with the same public IP (same local network) as the server.
To watch from another network, restream through an m3u proxy such as Threadfin.

## Run with Docker
The image is published to `ghcr.io/bigoldboy/youtube-proxy:latest` (amd64 and arm64)
on every push to `main`, and rebuilt weekly so streamlink stays current.

```yaml
services:
  youtube-proxy:
    image: ghcr.io/bigoldboy/youtube-proxy:latest
    container_name: youtube-proxy
    ports:
      - "6095:6095"
    restart: unless-stopped
```

To update: `docker compose pull && docker compose up -d`.

If streams start failing with a 400 error, YouTube has usually changed something and a
newer streamlink fixes it: pull the latest image, or run the workflow manually from the Actions tab.

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
Requires Python 3.10+, streamlink on the path, and flask:

```
pip install flask streamlink
python3 youtube-live.py
```
