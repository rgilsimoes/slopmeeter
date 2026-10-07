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
