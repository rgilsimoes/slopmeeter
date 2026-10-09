# Slop Meeter website

Static, Cloudflare Pages-ready frontend for Slop Meeter. Public GitHub repositories are acquired at an exact commit and assessed locally in a module Web Worker using a pinned, self-hosted Pyodide runtime and the shared Python analyzer.

## Local preview

```sh
npm install
npm run build
npm run dev
```

## Checks

```sh
npm run build
```

The build copies the pinned Pyodide runtime from `node_modules` and creates a deterministic pure-Python Slop Meeter wheel under `public/vendor/`. These generated assets are served from the same origin as the site.

The browser profile runs 14 of 23 weighted checks plus the informational disclosure check. It does not inspect commit history, package registries, or maintenance signals; every result and failure state links to the complete CLI assessment.

## Browser assessment contract

- Accepts only canonical public `https://github.com/owner/repository` URLs and resolves the default branch to a full commit SHA.
- Rejects truncated trees, symlinks, partial downloads, more than 3,000 eligible files, more than 60 MiB total, or any eligible file over 1 MiB. It never reports a sampled score.
- Downloads at most 12 immutable raw files concurrently, with a 30-second acquisition budget and a 15-second analysis budget.
- Runs the released Python checks inside a module Web Worker. Repository modules, tests, hooks, scripts and installers are never executed.
- Sends requests only to GitHub’s REST API and immutable raw-content URLs. Repository contents and findings are not sent to Slop Meeter infrastructure or analytics.
- Caches at most ten complete successful reports in IndexedDB, isolated by analyzer version, profile version, configuration hash, limit version and full commit SHA. Failures and cancelled scans are not cached.

The browser experience requires WebAssembly, module workers, Fetch streaming and IndexedDB. Current stable Chrome, Firefox and Safari are the supported policy; when a required browser capability or anonymous GitHub quota is unavailable, the UI fails closed and provides the complete CLI route.

## Deploy to Cloudflare Pages

Authenticate once with `npx wrangler login`, then run:

```sh
npm run deploy
```

The live Direct Upload project is named `slopmeeter`, and the deployable directory is `public/`. Cloudflare does not allow a Direct Upload project to be converted to Git integration later. If automatic Git deployments are wanted, create a separate Git-connected Pages project with no build command and set its build output directory to `website/public` from the repository root.

## Search and social previews

The canonical site URL is `https://slopmeeter.pages.dev/`. SEO metadata lives in `public/index.html`, while crawler discovery uses `public/robots.txt` and `public/sitemap.xml`. The Open Graph artwork source is `public/assets/slopmeeter-og.svg`; run `npm run og:image` to regenerate the committed `public/assets/slopmeeter-og.png` for broad social-platform support.

If the production domain changes, update the canonical, Open Graph, Twitter and JSON-LD URLs in `public/index.html`, plus `robots.txt`, `sitemap.xml` and `scripts/check-seo.mjs`.
