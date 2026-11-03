# Claude skills for this project

Third-party design skills, copied in (not installed with a package manager) after reading every file. Each folder is unchanged from its source except that UI/UX Pro Max's own test suite was left out.

| Skill | Source | Commit | License |
|---|---|---|---|
| `emil-design-eng`, `mobile-native`, `break-ui`, `review-animations`, `improve-animations` | [emilkowalski/skills](https://github.com/emilkowalski/skills) | `f1090be` | MIT (`LICENSE` in each folder) |
| `web-design-guidelines` | [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) | `1a2c79d` | MIT (stated in the upstream README) |
| `ui-ux-pro-max` | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | `713eef5` | MIT (`LICENSE`) |

## What each is for here

- **web-design-guidelines**: audit pages and components against Vercel's Web Interface Guidelines (fetched fresh from GitHub on each run); findings come out as `file:line`.
- **ui-ux-pro-max**: design-system and layout guidance before (re)designing a page. Its search script is local Python (standard library only, no network). For this site use `--stack nuxtjs` and `--rtl` with the style/product domains.
- **break-ui**: stress a page with worst-case data (empty lists, long Persian names, huge numbers).
- **mobile-native**: phone polish for the site, the PWA and the Android app: 100vh, input zoom, safe areas, tap highlight.
- **emil-design-eng**, **review-animations**, **improve-animations**: motion rules, and audits of the site's animations against them.

## Updating

Re-clone the source repo, read the diff, and copy the folder over. Don't add skills without reading them first: a skill is instructions (and sometimes scripts) that Claude follows.
