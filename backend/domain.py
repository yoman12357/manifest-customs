"""Deterministic checks. Financial and weight arithmetic never comes from AI."""

from decimal import Decimal, InvalidOperation

COMMON = [
    "supplier",
    "consignee",
    "packages",
    "gross_weight",
    "net_weight",
    "container",
]
FIELDS = {
    "invoice": COMMON
    + [
        "invoice_number",
        "invoice_date",
        "currency",
        "incoterm",
        "line_items",
        "invoice_total",
    ],
    "packing_list": COMMON + ["description", "quantity"],
    "bill_of_lading": COMMON + ["bl_number"],
}
NUMERIC = {
    "packages",
    "gross_weight",
    "net_weight",
    "quantity",
    "unit_price",
    "invoice_total",
}


def number(value):
    try:
        d = Decimal(str(value).replace(",", "").strip())
        return d if d.is_finite() and 0 <= d <= Decimal("1000000000000") else None
    except (InvalidOperation, ValueError):
        return None


def validate_field(key, value):
    if key == "line_items":
        parse_items(value)
    if key in NUMERIC:
        d = number(value)
        if d is None or d > Decimal("1000000000000"):
            raise ValueError("Enter a non-negative number below 1 trillion")
        if key in {"packages", "quantity"} and d != d.to_integral_value():
            raise ValueError("Enter a whole number")
    if key == "currency" and value not in {
        "USD",
        "EUR",
        "INR",
        "GBP",
        "JPY",
        "CNY",
        "AED",
    }:
        raise ValueError("Use USD, EUR, INR, GBP, JPY, CNY or AED")
    if key == "invoice_date":
        from datetime import date

        date.fromisoformat(value)


def parse_items(value):
    import json

    try:
        items = json.loads(value)
        if not isinstance(items, list) or not 1 <= len(items) <= 100:
            raise ValueError()
        for item in items:
            if (
                not isinstance(item, dict)
                or not str(item.get("description", "")).strip()
                or not str(item.get("hsn", "")).strip()
            ):
                raise ValueError()
            for k in ["quantity", "unit_price"]:
                if number(item.get(k)) is None:
                    raise ValueError()
            if number(item["quantity"]) != number(item["quantity"]).to_integral_value():
                raise ValueError()
        return items
    except (ValueError, TypeError, KeyError):
        raise ValueError(
            "Line items must be a JSON array of description, hsn, quantity and unit_price; quantities are non-negative whole numbers."
        )


def checks(documents):
    by_kind = {d["kind"]: d for d in documents}
    results = []

    def add(code, title, ok, detail):
        results.append(dict(code=code, title=title, passed=bool(ok), detail=detail))

    missing = [k.replace("_", " ") for k in FIELDS if k not in by_kind]
    add(
        "documents",
        "Three-document packet",
        not missing,
        "Missing: " + ", ".join(missing)
        if missing
        else "Invoice, packing list and bill of lading received",
    )
    pending = []
    for d in documents:
        for k in FIELDS[d["kind"]]:
            f = d["fields"].get(k, {})
            if not str(f.get("value", "")).strip() or not f.get("confirmed"):
                pending.append(f"{d['kind']}: {k}")
    add(
        "review",
        "Human verification",
        not pending and not missing,
        f"{len(pending)} fields need confirmation"
        if pending
        else "Every required field confirmed",
    )

    def values(key):
        return [d["fields"].get(key, {}).get("value", "") for d in documents]

    for key, label in [
        ("packages", "Package count"),
        ("gross_weight", "Gross weight"),
        ("net_weight", "Net weight"),
    ]:
        nums = [number(v) for v in values(key)]
        ok = len(nums) == 3 and None not in nums and len(set(nums)) == 1
        add(
            key,
            label + " across documents",
            ok,
            " / ".join(str(v) or "Missing" for v in values(key))
            or "Waiting for documents",
        )
    for key in ["supplier", "consignee", "container"]:
        vals = [v.strip().casefold() for v in values(key)]
        add(
            key,
            key.replace("_", " ").title() + " consistency",
            len(vals) == 3 and all(vals) and len(set(vals)) == 1,
            " / ".join(values(key)) or "Waiting for documents",
        )
    inv = by_kind.get("invoice", {}).get("fields", {})
    get = lambda k: number(inv.get(k, {}).get("value", ""))
    try:
        items = parse_items(inv.get("line_items", {}).get("value", ""))
        qty = sum(number(i["quantity"]) for i in items)
        line_sum = sum(number(i["quantity"]) * number(i["unit_price"]) for i in items)
    except ValueError:
        qty = line_sum = None
    total = get("invoice_total")
    ok = (
        line_sum is not None
        and total is not None
        and abs(line_sum - total) <= Decimal(".01")
    )
    add(
        "total",
        "Invoice total equals line sum",
        ok,
        f"Line sum {line_sum}; declared {total}",
    )
    packing_qty = number(
        by_kind.get("packing_list", {})
        .get("fields", {})
        .get("quantity", {})
        .get("value", "")
    )
    add(
        "quantity",
        "Invoice and packing quantities",
        qty is not None and packing_qty == qty,
        f"Invoice {qty}; packing list {packing_qty}",
    )
    for d in documents:
        gross = number(d["fields"].get("gross_weight", {}).get("value", ""))
        net = number(d["fields"].get("net_weight", {}).get("value", ""))
        add(
            d["kind"] + "_weight",
            d["kind"].replace("_", " ").title() + ": net ≤ gross",
            gross is not None and net is not None and net <= gross,
            f"Net {net} kg / gross {gross} kg",
        )
    return results
