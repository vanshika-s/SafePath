# Streetlights methodology patch

Use this text to update `docs/methodology.md` if the team wants to document streetlights.

## Add to the user-question table

| User question | What in the pipeline answers it |
|---|---|
| "Will this route feel visible at night?" | Streetlight count near each edge, converted into a `lighting_score`. This is a visibility proxy, not a guarantee of safety. |

## Add under Datasets and what each contributes

### `streetlights_clean.gpkg` — streetlight points

Each row is a City of San Diego streetlight point. The preprocessing notebook keeps likely usable lights based on status and mapping status fields, removes duplicate asset IDs and duplicate coordinates, and saves the result as a processed GeoPackage.

In scoring this can become:

- **Streetlight count per edge:** a 30m or 50m buffer is drawn around each street segment and nearby streetlights are counted.
- **Nighttime visibility score:** streetlight counts are converted into a capped 0 to 1 score. More nearby lights usually means better visibility, but this should be treated as a proxy.

This strengthens the user-centered safety story because crime and walkability do not fully capture how a route feels after dark.

## Add to limitations

- **Streetlight data is a visibility proxy.** A mapped streetlight does not guarantee that the light is currently working, bright enough, or that users will feel safe there.
