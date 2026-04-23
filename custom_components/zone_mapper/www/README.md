# Bundled frontend assets

`zone-mapper-card.js` in this directory is a pinned copy of
[`dist/zone-mapper-card.js`](https://github.com/ApolloAutomation/zone-mapper-card/blob/main/dist/zone-mapper-card.js)
from the card repo, bundled here so a single HACS install of the integration
also installs the card.

On every card release:

1. Tag the card repo.
2. Copy `dist/zone-mapper-card.js` from the card repo to this directory.
3. Bump `version` in `../manifest.json`.
4. Cut a new integration release.

The URL served to the frontend is versioned from `manifest.json`, so browser
caches invalidate automatically on integration upgrade.
