from src.order_ingest import OrderUpdate, chunks, ingest


class FakeClient:
    def __init__(self):
        self.vectors = []

    def upsert(self, collection, vectors):
        self.vectors.extend(vectors)
        return {"upserted_count": len(vectors)}


def test_packed_order_is_split_into_predictable_chunks():
    order = OrderUpdate("A-1", "Lee", "packed", ["book", "mug", "pen"], 20.0)
    assert chunks(order, 2)[0] == "Order A-1 for Lee: status packed. Total: 20.00."
    client = FakeClient()
    acknowledgement = ingest(order, lambda text: [float(len(text))], client, "orders")
    assert acknowledgement == {"upserted_count": 3}
    assert client.vectors[0]["metadata"]["order_id"] == "A-1"
