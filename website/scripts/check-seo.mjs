import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";

const root = fileURLToPath(new URL("../public/", import.meta.url));
const html = readFileSync(join(root, "index.html"), "utf8");
const canonicalUrl = "https://slopmeeter.pages.dev/";
const imageUrl = `${canonicalUrl}assets/slopmeeter-og.png`;

function requireMatch(pattern, message) {
  if (!pattern.test(html)) {
    throw new Error(message);
  }
}

for (const property of [
  "og:type",
  "og:site_name",
  "og:locale",
  "og:url",
  "og:title",
  "og:description",
  "og:image",
  "og:image:secure_url",
  "og:image:type",
  "og:image:width",
  "og:image:height",
  "og:image:alt",
]) {
  requireMatch(new RegExp(`<meta property="${property}" content="[^"]+">`), `Missing ${property} metadata`);
}

for (const name of ["description", "robots", "twitter:card", "twitter:title", "twitter:description", "twitter:image", "twitter:image:alt"]) {
  requireMatch(new RegExp(`<meta name="${name}" content="[^"]+">`), `Missing ${name} metadata`);
}

requireMatch(new RegExp(`<link rel="canonical" href="${canonicalUrl}">`), "Canonical URL is missing or incorrect");
requireMatch(new RegExp(`<meta property="og:image" content="${imageUrl}">`), "Open Graph image URL is incorrect");

const jsonLdMatch = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/);
if (!jsonLdMatch) {
  throw new Error("Missing JSON-LD structured data");
}
JSON.parse(jsonLdMatch[1]);

const jsonLdHash = `sha256-${createHash("sha256").update(jsonLdMatch[1]).digest("base64")}`;
const headers = readFileSync(join(root, "_headers"), "utf8");
if (!headers.includes(`script-src 'self' '${jsonLdHash}'`)) {
  throw new Error("The Content Security Policy must allow the current JSON-LD hash");
}

const png = readFileSync(join(root, "assets/slopmeeter-og.png"));
if (png.toString("ascii", 1, 4) !== "PNG" || png.readUInt32BE(16) !== 1200 || png.readUInt32BE(20) !== 630) {
  throw new Error("Open Graph image must be a 1200×630 PNG");
}

const robots = readFileSync(join(root, "robots.txt"), "utf8");
if (!robots.includes("Allow: /") || !robots.includes(`Sitemap: ${canonicalUrl}sitemap.xml`)) {
  throw new Error("robots.txt must allow crawling and advertise the sitemap");
}

const sitemap = readFileSync(join(root, "sitemap.xml"), "utf8");
if (!sitemap.includes(`<loc>${canonicalUrl}</loc>`)) {
  throw new Error("sitemap.xml must contain the canonical home page");
}

JSON.parse(readFileSync(join(root, "site.webmanifest"), "utf8"));
console.log("SEO metadata, structured data, crawler files and social image are valid.");
