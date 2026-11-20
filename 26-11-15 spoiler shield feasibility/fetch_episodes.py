"""Fetch Andor's episodes (order, title, overview) from TMDB into data/episodes.json.

The TMDB key is read from continuity/.env and never printed.
Run: py -3.13 fetch_episodes.py
"""
import json
from pathlib import Path

import httpx

HERE = Path(__file__).parent
ENV = HERE.parent.parent / 'continuity' / '.env'
SHOW_QUERY = 'Andor'


def tmdb_key() -> str:
    for line in ENV.read_text(encoding='utf-8').splitlines():
        if line.startswith('TMDB_API_KEY='):
            return line.split('=', 1)[1].strip().strip('"')
    raise SystemExit('TMDB_API_KEY not found in continuity/.env')


def main() -> None:
    params = {'api_key': tmdb_key()}
    with httpx.Client(base_url='https://api.themoviedb.org/3', params=params, timeout=20) as c:
        show = c.get('/search/tv', params={'query': SHOW_QUERY}).raise_for_status().json()['results'][0]
        detail = c.get(f'/tv/{show["id"]}').raise_for_status().json()
        episodes = []
        for s in detail['seasons']:
            if s['season_number'] == 0:
                continue
            season = c.get(f'/tv/{show["id"]}/season/{s["season_number"]}').raise_for_status().json()
            for e in season['episodes']:
                episodes.append({
                    'order': len(episodes) + 1,
                    'season': e['season_number'],
                    'episode': e['episode_number'],
                    'code': f'S{e["season_number"]}E{e["episode_number"]}',
                    'title': e['name'],
                    'air_date': e['air_date'],
                    'overview': e['overview'],
                })
    out = {'tmdb_id': show['id'], 'name': show['name'], 'overview': detail['overview'], 'episodes': episodes}
    (HERE / 'data' / 'episodes.json').write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')
    words = [len(e['overview'].split()) for e in episodes]
    print(f'{show["name"]} (tmdb {show["id"]}): {len(episodes)} episodes, overview words min/avg/max '
          f'{min(words)}/{sum(words) // len(words)}/{max(words)}')


if __name__ == '__main__':
    main()
