# Geo: cities, places and the gazetteer

## A city and a place are separate entities and tables
- A city (`geo_cities`, `CityEntity`) is a route endpoint and has exactly one country: `country_code`
  is NOT NULL, and a dataset row without one fails the load (`MissingCountryCodeError`).
- A place (`geo_places`, natural objects first) is somewhere the user has been, with no "from" and no
  transport, and may span several countries; the user picks one of them.
- A place has at least one country (`ck_geo_places_country_codes_not_empty`); an object without one
  is left out of the dataset.
- Why: the two answer different questions with different invariants (one country vs. a list), and the
  city search must not slow down under tens of thousands of lakes and mountains.
- Rejected: one entity and table with `kind` and a country array — route endpoints would need a
  `kind = city` check everywhere and share the search with non-cities.
- Rejected: `geo_natural_features` — places will also hold man-made sights; `geo_landmarks` — owner
  declined the name; `geo_points` — clashes with the journeys `GeoPoint` and a range is not a point.
- Source: 2026-10-26

## A journey stores a city as `city_id` plus country and coordinates from geo, never the name
- The client sends only city ids. journeys asks geo once, before its own transaction, for the
  country and coordinates of each city (`CitiesClientPort.find_city_locations`) and matches the
  answer by `city_id`, never by position. geo knows nothing about its consumers.
- The frontend gets names from geo (`/v1/geo/cities/resolve/`) in the UI language.
- Why: journeys must not know about languages, and storing every language in a journey does not
  scale. A city is identified by `city_id`, not by coordinates or name.
- Rejected: a name snapshot in the autocomplete's language (until 2026-09-29) — one city added in EN
  and in RU lived as two cities (Moscow / Москва) and did not follow a UI language switch.
- Rejected: a snapshot in both en and ru — a migration per language, translations frozen at
  creation.
- Rejected: country and coordinates sent by the client (until 2026-10-10) — journeys stored the
  client's numbers instead of geo's.
- Source: PR #116, 2026-09-29; PR #137, 2026-10-10

## Gazetteer names are one column per language
- `name_en` is required, other languages are nullable; a new language is a new column
  (`LocalizedNames`).
- Why: alternative names ("Питер") and the source of a translation are not needed.
- Rejected: a separate names table (until 2026-09-30) — built, measured 4–9× slower on short
  prefixes, rolled back.
- Source: 2026-09-30

## The gazetteer is our own dataset loaded into Postgres
- Cities (GeoNames + Wikidata labels) and places (Wikidata) come from our own datasets, published as
  `geo-data-vN` release assets and loaded into Postgres; no geocoder at runtime.
- A geodata provider must allow storing coordinates and codes indefinitely — that is the criterion
  for choosing one.
- Why: journeys keep city ids and coordinates forever.
- Rejected: Google Places — coordinates may be kept for at most 30 days and names not cached, so
  every read would need a request.
- Rejected: self-hosted Photon — ~90–95 GB of disk, and the prebuilt index has no Russian (a Russian
  index means a full Nominatim import of the planet).
- Revisit when: the Russian coverage of the dataset proves insufficient — a freemium geocoder is the
  fallback.
- Source: 2026-06-16; provider criterion 2026-09-29; places from Wikidata 2026-10-27
