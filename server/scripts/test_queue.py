"""Quick test script for the ERP inbound queue."""
import urllib.request
import json
import sys

BASE = "http://localhost:8082/api/v1"

def get(path):
    resp = urllib.request.urlopen(f"{BASE}{path}")
    return json.loads(resp.read())

if "--orders" in sys.argv:
    orders = get("/orders")
    print(f"Production Orders: {len(orders['data'])}")
    for o in orders['data']:
        pid = o['product_id'][:8]
        print(f"  {o['order_number']:20s} product={pid}.. status={o['status']} qty={o['quantity_ordered']}")

    lots = get("/lots")
    print(f"\nLots: {len(lots['data'])}")
    for lot in lots['data']:
        print(f"  {lot['lot_number']:25s} order={str(lot.get('order_id',''))[:8]}.. qty={lot.get('quantity')}")
    sys.exit(0)

# Default: check queue stats

def post(path, body=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        f"{BASE}{path}", data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method="POST",
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

# Default: check queue stats
stats = get("/erp/inbound/queue/stats")
print("Queue stats:", json.dumps(stats["data"], indent=2))

# Check processed items
processed = get("/erp/inbound/queue?status=processed")
print(f"\nProcessed items: {len(processed['data'])}")
for item in processed["data"]:
    print(f"  {item['erp_reference']} → order={item['order_id']}, wip={item.get('wip_ids')}")

# Check pending items
pending = get("/erp/inbound/queue?status=pending")
print(f"\nPending items: {len(pending['data'])}")
for item in pending["data"]:
    print(f"  {item['erp_reference']} attempts={item['attempts']} err={item.get('last_error', '')[:60]}")

# Check retry items
retry = get("/erp/inbound/queue?status=retry")
print(f"\nRetry items: {len(retry['data'])}")
for item in retry["data"]:
    print(f"  {item['erp_reference']} attempts={item['attempts']} next_retry={item.get('next_retry_at', '')}")
