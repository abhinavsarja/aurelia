"""
AURELIA - external news feed.

What the weekly watch job would have captured. Stored as JSONL because that is the
shape a search API returns, and because news is a feed rather than a set of files.

Design intent:
  - Most items are irrelevant. That is realistic and it is the point - the system
    must not reach for them when internal evidence already explains a drop.
  - Nothing here explains the MRL-CB-TAN case. The gate should stay CLOSED for it.
  - Two items touch gold jewellery around week 26, which is when NOV-ST-GLD falls.
    Neither proves anything. The correct answer is "found something, could not
    confirm it", not "this is the cause".
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "news"
OUT.mkdir(parents=True, exist_ok=True)

N = [
 # ---- background noise: relevant sector, no bearing on any SKU ----
 dict(date="2026-04-14", source="Singapore Business Times",
      title="Retail sales index edges up 1.2% in February",
      entities=dict(brands=[], categories=[], market=["singapore_retail"]),
      body="Singapore's retail sales index rose 1.2% year on year in February, "
           "the Department of Statistics reported. Wearing apparel and footwear "
           "grew 0.8%. Watches and jewellery were flat. Department stores declined 2.1%."),

 dict(date="2026-05-06", source="Inside Retail Asia",
      title="Orchard Road footfall recovers to pre-2020 levels",
      entities=dict(brands=[], categories=[], market=["footfall","singapore_retail"]),
      body="Footfall along Orchard Road reached 98% of 2019 levels in April according "
           "to mall operator data, driven by a recovery in regional tourist arrivals. "
           "Landlords report leasing enquiries at a three-year high."),

 dict(date="2026-05-19", source="Straits Times",
      title="Tourist arrivals up 6% year on year in April",
      entities=dict(brands=[], categories=[], market=["tourism"]),
      body="Singapore received 1.42 million visitors in April, up 6% on the same month "
           "last year. Arrivals from Indonesia and Malaysia led the increase. "
           "Retail and F&B were the largest beneficiaries of visitor spending."),

 # ---- competitor activity: real, but does not explain our numbers ----
 dict(date="2026-06-04", source="Retail Trade Weekly",
      title="Charles & Keith expands crossbody range with lower entry price point",
      entities=dict(brands=["charles_and_keith"], categories=["bags","crossbody"], market=[]),
      body="Charles & Keith has introduced six new crossbody styles in its summer "
           "range, with entry pricing from S$79. The Singapore-founded accessories "
           "brand said the expansion responds to demand for compact everyday bags. "
           "Analysts noted the pricing sits well below the accessible-luxury tier."),

 dict(date="2026-06-11", source="Inside Retail Asia",
      title="Pedro opens third Jewel Changi concept store",
      entities=dict(brands=["pedro"], categories=["footwear","bags"], market=[]),
      body="Pedro has opened a third concept store at Jewel Changi Airport, its "
           "largest format in Singapore. The store carries the full footwear and "
           "small leather goods range."),

 dict(date="2026-06-18", source="Business Times",
      title="Great Singapore Sale opens to strong first weekend",
      entities=dict(brands=[], categories=[], market=["singapore_retail","promotions"]),
      body="Retailers reported a strong opening weekend to the Great Singapore Sale, "
           "with several accessories and apparel brands citing double-digit uplifts "
           "against the prior week. Discounting was broadly in line with last year."),

 # ---- the two that touch gold jewellery, around when NOV-ST-GLD falls ----
 dict(date="2026-06-23", source="Vogue Business",
      title="The quiet return of silver: why gold's decade may be ending",
      entities=dict(brands=[], categories=["jewellery","gold","silver"], market=["trend"]),
      body="After ten years in which yellow gold dominated fine and costume jewellery, "
           "buyers at several European retailers report a marked shift toward silver "
           "and white metals for the coming season. Search interest in silver jewellery "
           "has risen steadily since spring. The shift is most visible in earrings and "
           "smaller pieces. Whether it reaches South-East Asian markets, where gold "
           "carries cultural weight beyond fashion, is not yet clear."),

 dict(date="2026-07-02", source="Retail Trade Weekly",
      title="Fast-fashion entrants push down costume jewellery price expectations",
      entities=dict(brands=[], categories=["jewellery"], market=["pricing"]),
      body="Several fast-fashion retailers have expanded costume jewellery ranges in "
           "Singapore at price points below S$40. Buyers at mid-market brands say the "
           "move is compressing what customers expect to pay for everyday pieces, "
           "particularly studs and small hoops. No formal market data is available yet."),

 # ---- more noise ----
 dict(date="2026-07-07", source="Straits Times",
      title="Consumer confidence steady in second quarter",
      entities=dict(brands=[], categories=[], market=["consumer_confidence"]),
      body="Singapore consumer confidence was broadly unchanged in the second quarter. "
           "Households reported stable spending intentions for discretionary categories, "
           "with no significant change in the outlook for clothing and accessories."),

 dict(date="2026-07-09", source="Inside Retail Asia",
      title="Leather prices ease after two years of increases",
      entities=dict(brands=[], categories=["leather","bags"], market=["commodity"]),
      body="Global bovine leather prices fell 3% in the second quarter, the first "
           "sustained decline since 2024. Manufacturers expect the easing to feed "
           "through to autumn intake costs."),

 dict(date="2026-07-15", source="Business Times",
      title="Marina Bay Sands mall reports record quarter for luxury tenants",
      entities=dict(brands=[], categories=[], market=["footfall"]),
      body="The retail arm at Marina Bay Sands reported its strongest quarter on "
           "record for luxury tenant sales, attributing the result to tourist spending "
           "and a stronger events calendar."),

 dict(date="2026-07-21", source="Retail Trade Weekly",
      title="Coach and Kate Spade lift Asia-Pacific outlook",
      entities=dict(brands=["coach","kate_spade"], categories=["bags"], market=[]),
      body="Tapestry raised its Asia-Pacific outlook, citing accessible-luxury handbag "
           "demand in Singapore and Malaysia. The group said mid-price handbags "
           "continue to take share from both entry and premium tiers."),

 dict(date="2026-07-28", source="Straits Times",
      title="Retail rents in prime malls rise 2.4%",
      entities=dict(brands=[], categories=[], market=["singapore_retail"]),
      body="Prime retail rents rose 2.4% in the second quarter, the fourth consecutive "
           "quarterly increase, as vacancy on Orchard Road fell below 4%."),

 dict(date="2026-07-30", source="Inside Retail Asia",
      title="Online returns rates climb across South-East Asia fashion",
      entities=dict(brands=[], categories=["ecommerce","returns"], market=[]),
      body="Fashion e-commerce return rates across South-East Asia rose to an average "
           "14% in the first half, up from 12%. Footwear and outerwear carry the "
           "highest rates. Retailers cite sizing as the dominant reason code."),

 dict(date="2026-08-04", source="Business Times",
      title="Charles & Keith reports double-digit growth in Singapore",
      entities=dict(brands=["charles_and_keith"], categories=["bags","footwear"], market=[]),
      body="Charles & Keith reported double-digit revenue growth in its home market "
           "for the first half, led by footwear. The company said its lower entry "
           "price points had broadened its customer base without diluting margin."),
]

path = OUT / "news_feed.jsonl"
with path.open("w") as f:
    for i, n in enumerate(N, 1):
        n["id"] = f"news-{n['date']}-{i:02d}"
        n["source_type"] = "external"
        n["doc_type"] = "news"
        n["url"] = f"https://example.com/{n['id']}"
        f.write(json.dumps(n) + "\n")

print(f"{len(N)} news items -> {path}")
print(f"  {path.stat().st_size:,} bytes")
print("\ndate range:", N[0]["date"], "->", N[-1]["date"])
print("\nitems mentioning a competitor brand:",
      sum(1 for n in N if n["entities"]["brands"]))
print("items touching jewellery:",
      sum(1 for n in N if "jewellery" in n["entities"]["categories"]))
