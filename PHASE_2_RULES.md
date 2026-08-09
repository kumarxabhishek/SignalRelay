# Phase 2 rule contract

These are descriptive evidence flags, not recommendations, price targets, or
claims of causation. Each rule is deterministic Python and returns no signal
when its required evidence is absent.

## 1. Insider–bulk-deal divergence

- Trigger: a disclosed insider sale and a reported bulk-deal **buy** for the
  same symbol occur within five calendar days.
- Evidence: the insider disclosure date/mode and the bulk-deal date/client.
- Deliberate limit: a bulk-deal client is not automatically an institution.
  This project therefore does not claim "institutional buying" without a
  separately verified counterparty classification source.

## 2. Delivery spike with a bulk deal

- Trigger: latest delivery percentage is greater than 1.5 times the mean of
  its preceding 30 observations, with a bulk deal on that same date.
- Status: implemented and unit-tested as a pure function, but disabled for live
  output because the verified data layer does not expose delivery percentage.
- This will be enabled only after adding a source that genuinely provides
  delivery quantity/percentage.

## 3. FII–index divergence

- Trigger: same-day FII net selling while Nifty 50 is positive, or same-day
  FII net buying while Nifty 50 is negative.
- Evidence: the FII net value and Nifty 50 percentage change for exactly the
  same IST date.
- Limit: this is a broad-market flow contrast; it cannot establish a
  stock-specific or sector-specific cause.

## Event context

Announcements and corporate actions are classified only when their disclosed
text includes a known keyword: results, dividend, split, bonus, rights issue,
or merger/acquisition. Events add context but never fire a signal by themselves.

NSE defines bulk-deal reporting around the 0.5% issue-size threshold; see the
[NSE circular](https://nsearchives.nseindia.com/content/circulars/cmtr7864.htm).

