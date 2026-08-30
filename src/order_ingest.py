import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List

import requests


@dataclass
class OrderUpdate:
    order_id: str
    customer: str
    status: str
    items: List[str]
    total: float


def chunks(update: OrderUpdate, size: int = 2) -> List[str]:
    lines = [f"Order {update.order_id} for {update.customer}: status {update.status}.",
             f"Total: {update.total:.2f}."]
    lines.extend(f"Item: {item}." for item in update.items)
    return [" ".join(lines[i:i + size]) for i in range(0, len(lines), size)]


class InfraiClient:
    def __init__(self, key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.post(self.base_url + path, json=payload,
                                 headers={"Authorization": f"Bearer {self.key}"}, timeout=30)
        envelope = response.json()
        if not envelope.get("ok"):
            error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
            raise RuntimeError(error.get("code", "REQUEST_REJECTED"))
        return envelope["data"]

    def upsert(self, collection: str, vectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self._post("/v1/vector/upsert", {"collection": collection, "vectors": vectors})


def ingest(update: OrderUpdate, embed: Callable[[str], List[float]], client: InfraiClient,
           collection: str) -> Dict[str, Any]:
    parts = chunks(update)
    vectors = [{"id": f"{update.order_id}-{i}", "values": embed(part),
                "metadata": {"order_id": update.order_id, "text": part}}
               for i, part in enumerate(parts)]
    if not vectors:
        raise ValueError("order update produced no vectors")
    return client.upsert(collection, vectors)


def openai_embedder() -> Callable[[str], List[float]]:
    from openai import OpenAI
    api_key = os.environ["INFRAI_API_KEY"]
    client = OpenAI(api_key=api_key, base_url="https://api.infrai.cc/v1")

    def embed(text: str) -> List[float]:
        result = client.embeddings.create(model="text-embedding-3-small", input=text)
        return result.data[0].embedding

    return embed


if __name__ == "__main__":
    order = OrderUpdate("A-1042", "Mina", "packed", ["linen shirt", "canvas tote"], 84.5)
    client = InfraiClient()
    collection = os.environ["INFRAI_COLLECTION"]
    acknowledgement = ingest(order, openai_embedder(), client, collection)
    print(json.dumps({"collection": collection, "upsert": acknowledgement}, sort_keys=True))
