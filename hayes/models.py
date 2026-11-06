from dataclasses import asdict, dataclass, field


@dataclass
class Item:
    id: str
    source: str
    author: str
    title: str
    text: str
    url: str
    published_at: str  # ISO 8601 UTC
    metrics: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)
