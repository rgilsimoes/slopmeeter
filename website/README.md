# Slop Meeter website

Static, Cloudflare Pages-ready frontend for Slop Meeter. The current scan flow is an interactive product preview and uses representative report data; it does not yet invoke the Python analyser.

## Local preview

```sh
npm install
npm run dev
```

## Checks

```sh
npm run build
```

## Deploy to Cloudflare Pages

Authenticate once with `npx wrangler login`, then run:

```sh
npm run deploy
```

The live Direct Upload project is named `slopmeeter`, and the deployable directory is `public/`. Cloudflare does not allow a Direct Upload project to be converted to Git integration later. If automatic Git deployments are wanted, create a separate Git-connected Pages project with no build command and set its build output directory to `website/public` from the repository root.

## Search and social previews

The canonical site URL is `https://slopmeeter.pages.dev/`. SEO metadata lives in `public/index.html`, while crawler discovery uses `public/robots.txt` and `public/sitemap.xml`. The Open Graph artwork source is `public/assets/slopmeeter-og.svg`; run `npm run og:image` to regenerate the committed `public/assets/slopmeeter-og.png` for broad social-platform support.

If the production domain changes, update the canonical, Open Graph, Twitter and JSON-LD URLs in `public/index.html`, plus `robots.txt`, `sitemap.xml` and `scripts/check-seo.mjs`.
