"""
AURELIA — synthetic data generator.

Produces six CSV tables plus a manifest for a 26-week backfill.
Deterministic: same seed in, same files out.

The simulation is causal, not cosmetic:
  demand -> constrained by stock -> units sold -> stock falls -> reorder arrives
so stock-outs genuinely suppress sales and the decomposition can prove it.

Scenarios deliberately embedded (see sales_drop_scenarios.pdf):
  B5 + C3  MRL-CB-TAN  reorder never placed, then campaign ends   <- hero
  A2       Eyewear     whole department softens, targets unchanged
  B3       NAD-LF-*    broken size curve, total stock looks fine
  E1       SIE-TT-NVY  returns spike from a sizing fault
  G1       NOV-ST-GLD  genuine drop with no internal explanation
"""
import csv, json, hashlib, random, datetime as dt
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data"
OUT.mkdir(exist_ok=True)

FIRST_WEEK, LAST_WEEK, YEAR = 6, 31, 2026
WEEKS = [(YEAR, w) for w in range(FIRST_WEEK, LAST_WEEK + 1)]

CAMPAIGN = set(range(21, 27))          # Mid-Year Sale, W21-W26 inclusive
CAMPAIGN_END = 26

def monday(year, week):
    return dt.date.fromisocalendar(year, week, 1)

def wkey(year, week):
    return f"{year}-W{week:02d}"

def month_of(year, week):
    return monday(year, week).strftime("%Y-%m")

def rnd(*parts):
    h = hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF

# ---------------------------------------------------------------- catalogue
# (model, department, [(colour, size, price, cost, base_weekly_demand)])
CAT = [
 ("Marlow Crossbody", "Bags", [
    ("Tan",    None, 310, 118,  95), ("Black",  None, 310, 118, 120),
    ("Cream",  None, 296, 112,  78), ("Olive",  None, 250,  96,  42)]),
 ("Sienna Tote", "Bags", [
    ("Black",  None, 420, 160,  70), ("Tan",    None, 420, 160,  54),
    ("Navy",   None, 420, 160,  38)]),
 ("Piper Clutch", "Bags", [
    ("Black",  None, 220,  84,  44), ("Gold",   None, 240,  92,  27)]),
 ("Astrid Backpack", "Bags", [
    ("Black",  None, 380, 145,  58), ("Grey",   None, 380, 145,  34)]),
 ("Juno Bucket Bag", "Bags", [
    ("Tan",    None, 340, 130,  47), ("Black",  None, 340, 130,  52)]),
 ("Elle Mini Bag", "Bags", [
    ("Black",  None, 260,  99,  63), ("Pink",   None, 260,  99,  31)]),

 ("Nadia Loafer", "Footwear", [
    (c, s, 290, 110, d) for c, base in [("Black", 82), ("Tan", 58)]
    for s, d in zip([35,36,37,38,39,40],
                    [base*f for f in (.10,.22,.26,.22,.14,.06)])]),
 ("Vera Heel", "Footwear", [
    (c, s, 330, 126, d) for c, base in [("Black", 50), ("Red", 24)]
    for s, d in zip([35,36,37,38,39,40],
                    [base*f for f in (.11,.23,.27,.21,.13,.05)])]),
 ("Cleo Sandal", "Footwear", [
    (c, s, 210,  80, d) for c, base in [("Tan", 68), ("White", 44)]
    for s, d in zip([35,36,37,38,39,40],
                    [base*f for f in (.12,.24,.26,.20,.13,.05)])]),

 ("Lune Pendant", "Jewellery", [
    ("Gold",   None, 180,  62,  92), ("Silver", None, 165,  57,  70)]),
 ("Orla Hoop", "Jewellery", [
    ("Gold",   None, 140,  48, 112), ("Silver", None, 130,  45,  86)]),
 ("Ivy Cuff", "Jewellery", [
    ("Gold",   None, 240,  84,  40)]),
 ("Nova Studs", "Jewellery", [
    ("Gold",   None, 110,  38,  95), ("Silver", None, 100,  35,  74)]),
 ("Thea Chain", "Jewellery", [
    ("Gold",   None, 210,  73,  48)]),

 ("Sol Aviator", "Eyewear", [
    ("Gold",   None, 195,  70,  54), ("Black",  None, 195,  70,  44)]),
 ("Mira Cat-Eye", "Eyewear", [
    ("Black",  None, 210,  76,  50), ("Tortoise", None, 210, 76, 33)]),
 ("Kai Round", "Eyewear", [
    ("Gold",   None, 185,  67,  36), ("Black",  None, 185,  67,  29)]),

 ("Rowan Belt", "Small leather goods", [
    ("Black",  None, 150,  56,  64), ("Tan",    None, 150,  56,  50)]),
 ("Quinn Cardholder", "Small leather goods", [
    ("Black",  None, 110,  41,  90), ("Tan",    None, 110,  41,  60)]),
 ("Faye Wallet", "Small leather goods", [
    ("Black",  None, 190,  71,  55), ("Tan",    None, 190,  71,  38)]),
 ("Iris Pouch", "Small leather goods", [
    ("Black",  None,  95,  36,  47)]),

 ("Tilda Charm", "Keychains", [
    ("Gold",   None,  65,  23, 118), ("Multi",  None,  65,  23,  88)]),
 ("Bo Tassel", "Keychains", [
    ("Tan",    None,  55,  20,  72)]),
]

CODE = {"Marlow Crossbody":"MRL-CB","Sienna Tote":"SIE-TT","Piper Clutch":"PIP-CL",
        "Astrid Backpack":"AST-BP","Juno Bucket Bag":"JUN-BK","Elle Mini Bag":"ELL-MN",
        "Nadia Loafer":"NAD-LF","Vera Heel":"VER-HL","Cleo Sandal":"CLE-SD",
        "Lune Pendant":"LUN-PD","Orla Hoop":"ORL-HP","Ivy Cuff":"IVY-CF",
        "Nova Studs":"NOV-ST","Thea Chain":"THE-CH","Sol Aviator":"SOL-AV",
        "Mira Cat-Eye":"MIR-CE","Kai Round":"KAI-RD","Rowan Belt":"ROW-BT",
        "Quinn Cardholder":"QUI-CH","Faye Wallet":"FAY-WL","Iris Pouch":"IRI-PC",
        "Tilda Charm":"TIL-CM","Bo Tassel":"BO-TSL"}
CC = {"Tan":"TAN","Black":"BLK","Cream":"CRM","Olive":"OLV","Navy":"NVY","Gold":"GLD",
      "Grey":"GRY","Pink":"PNK","Red":"RED","White":"WHT","Silver":"SLV",
      "Tortoise":"TOR","Multi":"MIX"}

products = []
for model, dept, variants in CAT:
    for colour, size, price, cost, base in variants:
        sku = f"{CODE[model]}-{CC[colour]}" + (f"-{size}" if size else "")
        products.append(dict(sku=sku, model=model, department=dept, colour=colour,
                             size=size or "", price=price, cost=cost,
                             base=max(base, 2.0), status="active"))

# lifecycle
for p in products:
    if p["sku"] == "MRL-CB-OLV": p["status"] = "clearance"      # scenario A1
    p["launch_date"] = ("2024-03-04" if p["department"] != "Keychains" else "2024-09-02")
products_by_sku = {p["sku"]: p for p in products}

# ---------------------------------------------------------------- shape of demand
def seasonal(week):
    """Singapore has no weather seasons. Shape comes from paydays and the Great Singapore Sale."""
    base = 1.0 + 0.05 * ((week % 4) in (0, 1))          # month-start payday lift
    if week in CAMPAIGN: base *= 1.0                     # campaign lift applied per-SKU
    if week in (9, 10):  base *= 1.06                    # Chinese New Year tail
    return base

FEATURED = {"MRL-CB-TAN", "MRL-CB-BLK", "SIE-TT-BLK", "LUN-PD-GLD", "ORL-HP-GLD",
            "QUI-CH-BLK", "TIL-CM-GLD"}

def campaign_lift(sku, week):
    if week not in CAMPAIGN: return 1.0
    return 1.40 if sku in FEATURED else 1.15

def discount(sku, week, status):
    if status == "clearance": return 0.25
    if week in CAMPAIGN:
        return 0.20 if sku in FEATURED else 0.10
    return 0.0

def scenario_factor(sku, dept, week):
    """Deliberate distortions. Everything else is background."""
    f = 1.0
    # A2 — whole of Eyewear softens steadily from W18, targets unchanged
    if dept == "Eyewear" and week >= 18:
        f *= max(0.62, 1.0 - 0.030 * (week - 17))
    # G1 — genuine unexplained fall, stock fine, no price change
    if sku == "NOV-ST-GLD" and week >= 26:
        f *= 0.62
    # D1 — Juno Bucket Bag Black absorbs demand from Elle Mini Black
    if sku == "ELL-MN-BLK" and week >= 20: f *= 0.70
    if sku == "JUN-BK-BLK" and week >= 20: f *= 1.34
    return f

def return_rate(sku, dept, week):
    base = {"Bags": .07, "Footwear": .14, "Jewellery": .04,
            "Eyewear": .06, "Small leather goods": .03, "Keychains": .01}[dept]
    if sku == "SIE-TT-NVY" and week >= 24:      # E1 — strap fault
        return 0.34
    return base

# ---------------------------------------------------------------- simulation
sales, stock_rows, receipts, returns = [], [], [], []
COVER_TARGET, REORDER_AT, LEAD = 7, 2.5, 2     # weeks

pending = {}          # (sku, arrival_week) -> units
opening = {}
for p in products:
    o = round(p["base"] * 7)
    # B3 - Nadia Loafer was bought on a flat size curve, so the ends are overstocked
    if p["sku"].startswith("NAD-LF") and str(p["size"]) in ("35", "39", "40"):
        o = round(p["base"] * 45)
    opening[p["sku"]] = o

for p in products:
    sku, dept, base = p["sku"], p["department"], p["base"]
    stock = opening[sku]
    for (yr, wk) in WEEKS:
        # deliveries arriving this week
        arriving = pending.pop((sku, wk), 0)
        if arriving:
            exp = monday(yr, wk) - dt.timedelta(days=7 * LEAD) + dt.timedelta(days=7 * LEAD)
            late = 7 if sku.startswith("CLE-SD") and wk == 21 else 0   # B4 — one late delivery
            receipts.append(dict(week=wkey(yr, wk), sku=sku, units_received=arriving,
                                 expected_date=str(monday(yr, wk) - dt.timedelta(days=late)),
                                 actual_date=str(monday(yr, wk))))
        stock += arriving

        # latent demand
        noise = 0.90 + 0.20 * rnd(sku, wk, "d")
        demand = base * seasonal(wk) * campaign_lift(sku, wk) * scenario_factor(sku, dept, wk) * noise
        demand = max(0.0, demand)

        # C3 — post-campaign fall for featured SKUs
        if sku in FEATURED and wk > CAMPAIGN_END:
            demand *= 0.74

        sold = int(min(round(demand), stock))
        stock -= sold

        disc = discount(sku, wk, p["status"])
        unit_price = p["price"] * (1 - disc)
        rev = round(sold * unit_price, 2)

        # split by channel
        share = 0.58 + 0.06 * (rnd(sku, wk, "c") - 0.5)
        st_u = int(round(sold * share)); ec_u = sold - st_u
        for ch, u in (("store", st_u), ("ecom", ec_u)):
            sales.append(dict(week=wkey(yr, wk), sku=sku, channel=ch, units=u,
                              revenue=round(u * unit_price, 2), discount_pct=round(disc, 3)))

        stock_rows.append(dict(week=wkey(yr, wk), sku=sku, units_on_hand=int(stock)))

        # returns land one week after the sale
        rr = return_rate(sku, dept, wk)
        if sold and (sku == "SIE-TT-NVY" or rnd(sku, wk, "r") < 0.45):
            ru = int(round(sold * rr * (0.7 + 0.6 * rnd(sku, wk, "rr"))))
            if ru > 0:
                reason = ("sizing" if dept == "Footwear" else
                          "strap fault" if sku == "SIE-TT-NVY" and wk >= 24 else
                          "colour differs" if rnd(sku, wk, "why") < .4 else "changed mind")
                returns.append(dict(week=wkey(yr, wk), sku=sku, units_returned=ru, reason=reason))

        # reorder policy
        recent = max(1.0, base * seasonal(wk))
        cover = stock / recent
        cover_target = 4 if sku == "MRL-CB-TAN" else COVER_TARGET
        already = any(k[0] == sku and k[1] > wk for k in pending)
        block = False
        # B5 — the reorder for Tan is never placed (buying committee, 12 May)
        if sku == "MRL-CB-TAN" and wk >= 26: block = True
        # B3 — Nadia Loafer mid sizes are not replenished; ends and total look fine
        if sku.startswith("NAD-LF") and sku.split("-")[-1] in ("36", "37", "38") and wk >= 17:
            block = True
        if cover < REORDER_AT and not already and not block and wk + LEAD <= LAST_WEEK:
            pending[(sku, wk + LEAD)] = int(round(recent * (cover_target - cover)))

# ---------------------------------------------------------------- targets (monthly)
months = sorted({month_of(y, w) for (y, w) in WEEKS})
targets = []
for p in products:
    for m in months:
        wks = [w for (y, w) in WEEKS if month_of(y, w) == m]
        if not wks: continue
        planned = sum(p["base"] * seasonal(w) * campaign_lift(p["sku"], w) for w in wks)
        stretch = 1.03
        tu = int(round(planned * stretch))
        targets.append(dict(month=m, sku=p["sku"], target_units=tu,
                            target_revenue=round(tu * p["price"] * 0.94, 2),
                            source_document=f"Monthly_Trading_Meeting_{m}.pdf"))

# ---------------------------------------------------------------- write
def write(name, rows, cols):
    path = OUT / name
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows: w.writerow({c: r.get(c, "") for c in cols})
    return len(rows)

counts = {}
counts["products"] = write("products.csv", products,
    ["sku","model","department","colour","size","price","cost","launch_date","status"])
counts["sales"]    = write("sales.csv", sales, ["week","sku","channel","units","revenue","discount_pct"])
counts["stock"]    = write("stock.csv", stock_rows, ["week","sku","units_on_hand"])
counts["returns"]  = write("returns.csv", returns, ["week","sku","units_returned","reason"])
counts["receipts"] = write("receipts.csv", receipts, ["week","sku","units_received","expected_date","actual_date"])
counts["targets"]  = write("targets.csv", targets, ["month","sku","target_units","target_revenue","source_document"])

manifest = dict(
    backfill=True,
    first_week=wkey(*WEEKS[0]), last_week=wkey(*WEEKS[-1]),
    weeks=len(WEEKS), skus=len(products),
    files=[f"{k}.csv" for k in counts],
    row_counts=counts,
    generated_at=dt.datetime.now().isoformat(timespec="seconds"),
)
(OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))

print(json.dumps(counts, indent=2))
print("weeks", manifest["first_week"], "->", manifest["last_week"])
