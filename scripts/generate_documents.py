"""
AURELIA - internal document corpus.

Twelve documents across the three types in the brief, written so that every
date, SKU and figure lines up with the numbers in data/*.csv.

The point of each document is to explain something the tables cannot:

  Buying_Committee_2026-06-15   MRL-CB-TAN replenishment deferred   -> B5, hero
  MidYear_Campaign_Plan_SS26    campaign ran W21-W26, featured list -> C3, hero
  Autumn_Drop_Brief             spend moves to new arrivals W27+    -> D2
  Range_Review_2026-04          Olive to clearance, loafer buy      -> A1, B3
  Trading_Meeting_2026-07       July targets and how they were set  -> A5, A2
  Supply_Chain_2026-06          Cleo Sandal delivery ran late       -> B4
  Returns_Quality_2026-07       Sienna Navy strap fault             -> E1
  Store_Ecom_Ops_2026-07        nothing happened - rules out F1
  Buying_Committee_2026-07-20   follow-up, Tan still out
  Eyewear_Category_Review       category-wide softness              -> A2
  Trading_Meeting_2026-06       June targets
  Merch_Note_Nova_Studs         nobody can explain it               -> G1
"""
import datetime as dt
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "data" / "documents"
DOCS.mkdir(parents=True, exist_ok=True)

def w(week, day=1):
    return dt.date.fromisocalendar(2026, week, day)

def write(name, text):
    (DOCS / name).write_text(text.strip() + "\n")
    return name

# ---------------------------------------------------------------- 1. HERO
write("Buying_Committee_Minutes_2026-06-15.md", f"""
# Buying Committee — Minutes

**Date:** Monday 15 June 2026
**Time:** 09:00–10:40
**Location:** Level 4 boardroom, Tanjong Pagar
**Chair:** Serena Loh, Commercial Director
**Present:** Serena Loh (Chair), Marcus Tan (Head of Buying, Bags & SLG),
Priya Raman (Head of Buying, Footwear & Jewellery), Grace Wee (Merchandise Planning),
Daniel Foo (Supply Chain), Jolene Ng (Finance Business Partner)
**Apologies:** Wei Sheng Chua (Marketing)

---

## 1. Trading update, weeks 21–24

Grace presented trade to week 24. Mid-Year Sale is performing ahead of plan on Bags,
driven by Marlow Crossbody. Jewellery is holding. Eyewear remains soft and is now the
third consecutive month behind — carried to item 5.

## 2. SS26 replenishment — Open-to-Buy

Marcus tabled the replenishment schedule for the remainder of SS26. Total requested
intake is **S$1.84m** against remaining OTB of **S$1.31m**. A gap of S$530k must be
closed before the Autumn intake commits in week 27.

The committee reviewed the schedule line by line.

### 2.1 Marlow Crossbody — Tan (MRL-CB-TAN)

Marcus requested a replenishment order of **400 units**, lead time 2 weeks,
to cover the remainder of the season.

Grace noted that Tan is currently the strongest performer in the model. It carried
roughly 41% of Marlow Crossbody volume through May and is featured in the Mid-Year
Sale. At the current rate of sale, stock on hand covers **to approximately week 28**.

Jolene advised that committing the full Autumn intake and the SS26 replenishment
together would exceed OTB by S$530k, and that the Autumn buy has a firm supplier
deadline of week 27 with no flexibility.

**Decision:** the Marlow Crossbody Tan replenishment is **deferred**. The freed OTB
of S$124k is reallocated to the Autumn intake. Marcus to re-raise the order in the
Autumn cycle for delivery in **week 36**.

Marcus recorded a concern that this will take Tan out of stock from roughly week 29
and that the colour has no obvious substitute — Black and Cream serve a different
customer. Serena accepted the risk on the basis that Mid-Year Sale support ends in
week 26 and demand is expected to normalise after that.

**Action:** Marcus — re-raise MRL-CB-TAN replenishment in the Autumn cycle. Due wk27.
**Action:** Grace — monitor Tan cover weekly and flag if the stock-out arrives earlier
than week 29.

### 2.2 Other lines

- Sienna Tote Black and Tan — replenishment **approved**, 260 units combined.
- Sienna Tote Navy — **held** pending the returns question at item 4.
- Astrid Backpack — approved at reduced quantity, 90 units.
- Piper Clutch Gold — no replenishment. Sell through remaining stock.

## 3. Autumn intake

Confirmed for commitment in week 27. Marketing has confirmed the Autumn Drop launches
week 27 with homepage and paid support moving across from the Mid-Year Sale.

## 4. Sienna Tote Navy — returns

Daniel reported that returns on **SIE-TT-NVY** have risen sharply since week 24.
Return reasons are concentrated on the strap fitting. Volume of the fault is not yet
established. Quality to report to the July meeting. Replenishment held in the meantime.

## 5. Eyewear

Carried from May. Category has been behind target since week 18 across all three
models, not confined to any single line. Priya to prepare a category review for the
July meeting.

## 6. Any other business

None.

**Next meeting:** Monday 20 July 2026, 09:00.
""")

# ---------------------------------------------------------------- 2. CAMPAIGN
write("MidYear_Campaign_Plan_SS26.md", f"""
# Mid-Year Sale 2026 — Campaign Plan

**Version:** 2.0 (final)
**Issued:** 1 May 2026
**Owner:** Wei Sheng Chua, Head of Marketing
**Approved by:** Serena Loh, Commercial Director

---

## Dates

| | |
|---|---|
| Campaign live | **Monday 18 May 2026 (week 21)** |
| Campaign ends | **Sunday 28 June 2026 (week 26)** |
| Duration | 6 trading weeks |

The campaign runs alongside the Great Singapore Sale window. All support ends at
close of trade on Sunday 28 June. From **week 27** the homepage, paid social and
EDM slots transfer to the Autumn Drop — see the separate Autumn brief.

## Channels

- E-commerce homepage hero, full campaign duration
- Paid social (Meta, TikTok), S$180k total
- EDM to the full base, weeks 21, 23 and 25
- In-store window and podium at Orchard and Marina Bay

## Discounting

| Tier | Discount | Applies to |
|---|---|---|
| Featured heroes | **20%** | the list below |
| Wider participating range | 10% | all other active lines |
| Excluded | — | new arrivals launched after 1 April |

## Featured hero SKUs

These carry homepage placement, paid social creative and EDM position.

| SKU | Product |
|---|---|
| **MRL-CB-TAN** | Marlow Crossbody, Tan |
| **MRL-CB-BLK** | Marlow Crossbody, Black |
| **SIE-TT-BLK** | Sienna Tote, Black |
| **LUN-PD-GLD** | Lune Pendant, Gold |
| **ORL-HP-GLD** | Orla Hoop, Gold |
| **QUI-CH-BLK** | Quinn Cardholder, Black |
| **TIL-CM-GLD** | Tilda Charm, Gold |

Marlow Crossbody Tan is the lead image for the campaign across all channels.

## Expected effect

Based on the 2025 Mid-Year Sale, featured lines are planned at **+40% units**
against baseline for the campaign period, and the wider range at +15%.

**Post-campaign:** featured lines typically fall back **below** baseline for three to
four weeks once support is withdrawn, as demand has been pulled forward. Planning has
assumed a return to baseline by week 30. Buying should not read the week 27–29 dip as
a demand signal.

## Measurement

Weekly read on featured SKU units and full-price sell-through. Post-campaign review
in the July trading meeting.
""")

# ---------------------------------------------------------------- 3. AUTUMN BRIEF
write("Autumn_Drop_Campaign_Brief_2026.md", """
# Autumn Drop 2026 — Campaign Brief

**Issued:** 12 June 2026
**Owner:** Wei Sheng Chua, Head of Marketing

## Launch

**Week 27, Monday 29 June 2026.** Runs to week 34.

## What moves

From week 27 all primary marketing assets transfer from the Mid-Year Sale to the
Autumn Drop:

- E-commerce homepage hero — Autumn takes the full slot
- Paid social budget — S$210k, reallocated in full from Mid-Year Sale
- EDM — weeks 27, 29, 31
- Store windows — Orchard and Marina Bay changed over the weekend of 27–28 June

**SS26 carry-over lines lose all paid support from week 27.** They remain on site and
in store, and remain available at full price, but with no homepage placement, no paid
social and no EDM. This is the normal seasonal handover and is planned.

## New lines

Autumn intake commits week 27 for delivery from week 34. The launch runs on existing
Autumn-appropriate carry-over until then.

## Note from Merchandise Planning

Grace Wee has asked that trading reads for weeks 27 to 30 are interpreted with the
handover in mind. Lines that were Mid-Year heroes will show a sharp week-on-week
fall in that window even where stock and price are unchanged.
""")

# ---------------------------------------------------------------- 4. RANGE REVIEW
write("Range_Review_2026-04.md", """
# Range Review — SS26 mid-season

**Date:** Thursday 23 April 2026
**Present:** Serena Loh, Marcus Tan, Priya Raman, Grace Wee

---

## 1. Lines to clearance

| SKU | Product | Decision |
|---|---|---|
| **MRL-CB-OLV** | Marlow Crossbody, Olive | **Clearance from week 18.** Discount to 25% and hold. Do not replenish. Colour has not performed in two consecutive seasons. Status to be set to clearance in the product master. |
| PIP-CL-GLD | Piper Clutch, Gold | Sell through. No replenishment. Review again in August. |

Marcus noted that Olive will continue to show declining units through the season and
that this is the intended outcome, not a performance problem.

## 2. Footwear — Nadia Loafer size curve

Priya raised the Nadia Loafer intake. The original buy was placed on a **flat size
curve** — equal quantities across sizes 35 to 40 — rather than on the historical
sales curve, which is heavily weighted to 36, 37 and 38.

Consequence: sizes 36 to 38 are selling through well ahead of the rest and will run
out first, while 35, 39 and 40 will remain in stock for the full season. Total stock
on hand for the model will continue to look healthy while the sizes customers
actually want are unavailable.

**Decision:** no mid-season size replenishment. The cost of a part-size intake is not
justified against remaining season. Accept the sell-through loss and correct the
curve at the Autumn buy.

**Action:** Priya — Autumn Nadia intake to follow the historical size curve, not a
flat curve. Due at Autumn commitment.

## 3. Elle Mini Bag and Juno Bucket Bag

Grace noted the two lines sit at a similar price point and serve the same customer.
Juno launched in March and is trading well. Some transfer of demand from Elle Mini
is expected and should not be read as an Elle Mini failure.

No action. Monitor.
""")

# ---------------------------------------------------------------- 5. TRADING JULY
write("Monthly_Trading_Meeting_2026-07.md", """
# Monthly Trading Meeting — July 2026

**Date:** Wednesday 1 July 2026
**Present:** Serena Loh (Chair), Jolene Ng, Grace Wee, Marcus Tan, Priya Raman, Wei Sheng Chua

---

## 1. June close

June closed **+2.1%** against target overall. Bags carried the month on the back of
the Mid-Year Sale. Eyewear finished **-17%** and is now four months behind.

## 2. July targets

Targets for July are confirmed as circulated. Method unchanged: department targets are
set from the annual plan phased by week, then broken down to model and SKU on last
year's share of department volume.

Two points recorded for the file.

**2.1** The July SKU targets for Mid-Year Sale hero lines **do not adjust for the
post-campaign fall-back**. Marketing's campaign plan assumes featured lines trade
below baseline for three to four weeks after support ends. The targets were set from
the annual phasing and do not carry that adjustment. Jolene noted these lines will
therefore show a gap in July that is a function of the target, not of demand.

**Action:** Jolene — apply a post-campaign adjustment to the phasing method from the
Autumn cycle onward.

**2.2** Eyewear targets are unchanged from the annual plan despite four consecutive
months behind. Serena's decision: hold the targets and address the category through
the review at item 4 rather than by lowering the number.

## 3. Marlow Crossbody Tan

Grace reported that following the June buying committee decision, Tan cover runs to
approximately week 28. A stock-out from week 29 is expected and the line will
contribute nothing for the remainder of July. This is a known and accepted
consequence of the OTB decision, not a new issue.

## 4. Eyewear category review

Priya presented. Carried to the separate category review document.

## 5. Sienna Tote Navy

Quality investigation ongoing. Returns remain elevated. Replenishment still held.
""")

# ---------------------------------------------------------------- 6. SUPPLY CHAIN
write("Supply_Chain_Status_2026-06.md", """
# Supply Chain Status Report — June 2026

**Prepared by:** Daniel Foo, Supply Chain Manager
**Issued:** 30 June 2026

---

## 1. Inbound performance

| Metric | June | May |
|---|---|---|
| Deliveries received | 41 | 38 |
| On time (within 2 days of expected) | 39 | 37 |
| Late | 2 | 1 |
| Average delay on late deliveries | 6 days | 4 days |

## 2. Late deliveries

**Cleo Sandal (CLE-SD-TAN, CLE-SD-WHT)** — intake expected week 21, received week 21
but **7 days later than scheduled**. Cause: consolidation delay at the supplier's
Ho Chi Minh facility following a public holiday shutdown. The delay resulted in a
short cover position across both colours for one week before stock normalised.

Supplier has been notified. No compensation sought — this is the first late shipment
from this vendor in twelve months.

## 3. Open orders

No open orders for Marlow Crossbody Tan (MRL-CB-TAN). The June replenishment was not
raised — see Buying Committee minutes, 15 June. Next scheduled intake for this SKU is
the Autumn cycle, week 36.

## 4. Outlook

No further delays anticipated in July. Autumn intake commits week 27 with delivery
from week 34.
""")

# ---------------------------------------------------------------- 7. RETURNS
write("Returns_Quality_Summary_2026-07.md", """
# Returns and Quality Summary — July 2026

**Prepared by:** Quality & Customer Care
**Issued:** 3 August 2026

---

## 1. Overall

Group return rate for July was **9.4%**, against a trailing baseline of 8.1%.
The increase is accounted for almost entirely by a single line.

| Department | July return rate | Baseline |
|---|---|---|
| Bags | 11.2% | 7.0% |
| Footwear | 14.1% | 14.0% |
| Jewellery | 4.2% | 4.0% |
| Eyewear | 6.1% | 6.0% |
| Small leather goods | 3.1% | 3.0% |
| Keychains | 1.0% | 1.0% |

## 2. Sienna Tote — Navy (SIE-TT-NVY)

**Return rate is running at 30–38% against a line baseline of 7%.** Elevated since
week 24 and sustained through July.

Reason codes are concentrated on the strap. Customer comments describe the shoulder
strap fitting working loose in normal use. 41 units inspected on return; **34 showed
the same fault** at the strap anchor rivet.

Traced to a single production lot. The fault is not present in Sienna Tote Black or
Tan, which use the same strap component from a different lot.

**Important for trading:** gross sales of this line remain **ahead of target**. The
problem is invisible in the sales figures and only appears in returns.

**Actions**
- Replenishment remains held (agreed at June buying committee)
- Supplier claim raised for the affected lot
- Remaining stock from the lot quarantined pending inspection
- Customer care to contact purchasers from weeks 24 onward proactively

## 3. Footwear

Return rate unchanged at 14%, consistent with the category norm for online footwear.
Reason codes remain dominated by sizing. No action.
""")

# ---------------------------------------------------------------- 8. OPS (the null result)
write("Store_Ecommerce_Operations_2026-07.md", """
# Store and E-commerce Operations Report — July 2026

**Prepared by:** Retail Operations
**Issued:** 4 August 2026

---

## 1. Store estate

All stores traded normally for the full month. No closures, no refits, no reduced
hours. Staffing at establishment across the estate.

| Store | Trading days | Notes |
|---|---|---|
| Orchard flagship | 31 | Normal |
| Marina Bay | 31 | Normal |
| Jewel Changi | 31 | Normal |
| Suburban (7 sites) | 31 each | Normal |

## 2. E-commerce

Site availability **99.98%** for the month. One planned maintenance window on
Sunday 12 July, 02:00–03:30, outside trading hours.

No checkout incidents. No payment gateway failures. Page load times within normal
range throughout. No changes to search, navigation or product listing logic
during the period.

## 3. Fulfilment

Order-to-despatch averaged 1.2 days, unchanged. No backlog.

## 4. Conclusion

**No operational factor affected trading in July.** Any variance against target in
this period originates elsewhere — range, supply, pricing or demand.
""")

# ---------------------------------------------------------------- 9. FOLLOW-UP
write("Buying_Committee_Minutes_2026-07-20.md", """
# Buying Committee — Minutes

**Date:** Monday 20 July 2026
**Chair:** Serena Loh
**Present:** Serena Loh, Marcus Tan, Priya Raman, Grace Wee, Daniel Foo, Jolene Ng

---

## 1. Matters arising

**Marlow Crossbody Tan (MRL-CB-TAN)** — out of stock since week 29 as anticipated at
the June meeting. No units available for the remainder of July or August. Order is
placed in the Autumn cycle for week 36 delivery.

Grace noted the line has contributed zero units since week 29 against a July target
of 401 units. Marcus asked that the record show the July gap on this SKU is a
consequence of the June OTB decision and not a demand issue — Marlow Crossbody Black,
which was equally featured in the Mid-Year Sale and remained in stock, has traded
close to its target through the same period.

No further action. Accepted.

## 2. Autumn intake

Committed week 27 as planned. Delivery confirmed week 34–36.

## 3. Sienna Tote Navy

Quality report received. Fault confirmed to a single production lot. Supplier claim
raised. Line remains held.

## 4. Nova Studs Gold

Priya raised **NOV-ST-GLD**, which has fallen sharply since week 26 with no apparent
cause. Stock has been available throughout, price unchanged, no discount, and the
line was not part of the Mid-Year Sale. Silver in the same model is trading normally.

No explanation identified. Priya to investigate and report in August.
""")

# ---------------------------------------------------------------- 10. EYEWEAR
write("Eyewear_Category_Review_2026-07.md", """
# Eyewear — Category Review

**Prepared by:** Priya Raman, Head of Buying
**Presented:** Monthly Trading Meeting, 1 July 2026

---

## 1. Position

Eyewear has been behind target every month since April. The shortfall has widened
from -4% in April to **-17% in June** and is tracking similarly in July.

## 2. The shortfall is category-wide, not line-specific

This is the central finding. All three models are behind by a similar margin:

| Model | Variance to target, June |
|---|---|
| Sol Aviator | -18% |
| Mira Cat-Eye | -16% |
| Kai Round | -19% |

Both colourways within each model are behind by comparable amounts. There is no
single failing line carrying the category.

**Any individual Eyewear SKU examined in isolation will appear to be
underperforming by roughly the same amount as the category as a whole.** Reading a
single SKU as the problem would be a mistake.

## 3. Contributing factors considered

- **Stock:** availability has been adequate throughout. Not a supply issue.
- **Price:** no price changes this season. Not a pricing issue.
- **Range:** the assortment is unchanged from SS25, which performed to plan.
  The range is now in its second season without newness.
- **Targets:** set from the annual plan and not revised despite four months behind.

## 4. Assessment

The most likely explanation is range fatigue. The Eyewear assortment has not been
refreshed for two seasons while the market has moved. This is a range planning issue
and cannot be corrected within the current season.

## 5. Recommendation

- Hold current targets for the remainder of SS26 rather than rebasing
- Bring forward the Eyewear range refresh to the Autumn buy
- Do not markdown — discounting will not address a newness problem
""")

# ---------------------------------------------------------------- 11. TRADING JUNE
write("Monthly_Trading_Meeting_2026-06.md", """
# Monthly Trading Meeting — June 2026

**Date:** Monday 1 June 2026
**Present:** Serena Loh (Chair), Jolene Ng, Grace Wee, Marcus Tan, Priya Raman, Wei Sheng Chua

---

## 1. May close

May closed **+4.4%** against target. Mid-Year Sale launched week 21 and is trading
ahead of plan in the first two weeks, particularly on Bags.

## 2. June targets

Confirmed as circulated. Method unchanged.

June targets include the Mid-Year Sale uplift for featured lines through week 26.
No uplift is carried beyond week 26 as the campaign ends.

## 3. Eyewear

Behind for a third consecutive month. Priya to prepare a full category review for
the July meeting.

## 4. Open-to-Buy

Jolene flagged that remaining SS26 OTB will not cover both the outstanding
replenishment schedule and the Autumn intake. To be resolved at the buying committee
on 15 June.
""")

# ---------------------------------------------------------------- 12. THE UNEXPLAINED ONE
write("Merchandise_Note_Nova_Studs_2026-08.md", """
# Merchandise Note — Nova Studs Gold (NOV-ST-GLD)

**Prepared by:** Priya Raman
**Date:** 5 August 2026
**Status:** Open — no conclusion reached

---

## Summary

NOV-ST-GLD has traded approximately **35% below its run rate since week 26**. The
decline is sustained, not a single bad week. No internal cause has been identified.

## What has been ruled out

| Checked | Finding |
|---|---|
| Stock availability | Adequate every week. Never below three weeks of cover. |
| Price | Unchanged all season. S$110. |
| Discount | None applied. Line was not in the Mid-Year Sale. |
| Campaign support | None before or after. No change to compare. |
| Range status | Active. Not on clearance, not being wound down. |
| Sibling lines | Nova Studs Silver trading normally, close to target. |
| Category | Jewellery as a whole is ahead of target. |
| Channel | Decline present in both stores and e-commerce, in similar proportion. |
| Returns | Normal, in line with the Jewellery baseline. |
| Operations | No store or site issues in the period. |

## Assessment

Every internal explanation available to us has been checked and none accounts for the
decline. The line has simply stopped selling at its previous rate.

If there is a cause it is likely external — a shift in preference, a competitor
product, or something in the wider market that we do not have visibility of from
internal data.

**Recommendation:** do not markdown while the cause is unknown. Review again at the
end of August.
""")

print(f"{len(list(DOCS.glob('*.md')))} documents written to {DOCS}")
for f in sorted(DOCS.glob("*.md")):
    print(f"  {f.name:48s} {f.stat().st_size:>6,} bytes")
