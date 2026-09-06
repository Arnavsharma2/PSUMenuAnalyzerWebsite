# PSUMenu

[Live app](https://psumenu.com) · [Penn State's official menus](https://www.absecom.psu.edu/menus/user-pages/daily-menu.cfm)

Find meal ideas at Penn State by dining location, menu date, and dietary preference. PSUMenu reads the published menus, uses Penn State's dietary labels for vegan and vegetarian filtering, and optionally asks Gemini to suggest up to five items per meal. If Gemini is unavailable, students can still browse the filtered, published menu.

## What it does

- Lists current dining locations and published dates directly from Penn State.
- Fetches breakfast, lunch, and dinner concurrently, with independent HTTP sessions and bounded timeouts.
- Checks the returned location/date and keeps only official nutrition links.
- Uses source dietary labels instead of guessing whether an item is vegan or vegetarian from its name.
- Constrains Gemini to JSON and validates every suggested item against the corresponding meal before returning it.
- Shares a 15-minute SQLite menu cache across requests. Successful rankings are cached separately by location, full date, preferences, model, and cache version.
- Keeps partial menu failures visible and avoids caching a failed AI ranking as a successful result.
- Remembers preferences locally, prevents overlapping submissions, and works on narrow mobile screens without a frontend build step.

Suggestions are based on menu names and dietary labels, not a complete nutritional analysis. Internal model scores only sort suggestions; the UI does not present them as measured health scores. Beef/pork exclusions use source labels plus conservative word matching and are not an allergy guarantee. Always check Penn State's official ingredient and allergen information.

## Run locally

Use Python 3.12 and an optional Gemini API key. Without a key, the app shows published menu items without AI ranking.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
# Set GEMINI_API_KEY in .env if AI ranking is wanted.
python main.py
```

Open http://127.0.0.1:5001. The frontend uses relative API URLs, so other ports work too.

| Variable               | Purpose                                                                          |
| ---------------------- | -------------------------------------------------------------------------------- |
| `GEMINI_API_KEY`       | Server-side Gemini credential. Never commit it or put it in frontend JavaScript. |
| `GEMINI_MODEL`         | Defaults to `gemini-3.5-flash-lite`; choose a model available to your project.   |
| `CACHE_DIR`            | Optional cache directory; defaults to `cache/` beside `main.py`.                 |
| `CACHE_ADMIN_PASSWORD` | Optional. When unset, cache administration is disabled.                          |
| `PORT`                 | Local server port, default `5001`. Docker defaults to `8080`.                    |

The Gemini integration uses the supported REST API with JSON-schema output and authentication in the request header, not the URL. The model can be changed without editing code. See Google's [model catalog](https://ai.google.dev/gemini-api/docs/models), [structured output documentation](https://ai.google.dev/gemini-api/docs/structured-output), and [API key guide](https://ai.google.dev/gemini-api/docs/api-key).

## Tests

```sh
python -m pytest -q
python -m pip check
node --check static/app.js
node --check sw.js
```

Tests block external network access. They cover scraping, exact date/location selection, dietary labels, cache expiration and concurrent writes, hallucinated items, malformed responses, bounded retries, AI fallback, request validation, and cache administration. GitHub Actions also builds the Docker image.

## Deployment

The existing application runs as a Docker web service on Render. Keep credentials in the service's environment settings. There is no need to expose the key to browsers or commit a `.env` file. The image copies only runtime application files; local environment files and caches are excluded.

```sh
docker build -t psumenu .
docker run --rm -p 8080:8080 --env-file .env -e PORT=8080 psumenu
```

The Docker command starts one Gunicorn worker with four threads, a 90-second worker timeout, and the optional control socket disabled. Duplicate-request suppression is per process; SQLite entries are shared on the same local disk. This is not a distributed cache or a global quota system. Render's ephemeral cache is sufficient; a restart simply causes fresh requests.

- `GET /health`: application liveness, version `2.0.0`; it does not promise that upstream services are available.
- `GET /api/options`: currently published locations and dates.
- `POST /api/analyze`: location, optional ISO date, and boolean preferences. Returns meal arrays plus `_meta` with date, source, cache status, warnings, and whether Gemini ranking was used.
- `POST /api/clear-cache`: authenticated maintenance endpoint, disabled by default. The public page does not expose an admin button.

Old pickle caches are not read. The retirement service worker removes only this app's old caches and unregisters itself, avoiding stale offline menu pages.

## Stack

Python · Flask · Requests · BeautifulSoup · SQLite · Gemini REST API · vanilla JavaScript/CSS · Gunicorn · Docker

No Node runtime, third-party browser scripts, database service, or frontend framework is required for production.
