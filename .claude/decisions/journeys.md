# Journeys

## A journey is one one-way segment with one transport
- Minsk → Moscow → Istanbul → Minsk is three journeys; a round trip is two. Origin and destination
  differ.
- Why: why not recorded.
- Rejected: a whole trip (several legs, a round trip) as one record — why not recorded.
- Revisit when: chain input or a `Trip` grouping gets designed (`.plan/ideas/chain-input.md`).
- Source: journeys design, 2026-06

## The only date of a journey is the year
- `traveled_year`; a future year is rejected — plans belong to the future wishlist.
- Why: month and day were never used, and the order within a year will be set by hand.
- Rejected: month and day with a precision marker (`ApproximateDate`, until 2026-10-02) — same
  reason.
- Source: PR #121, 2026-10-02
