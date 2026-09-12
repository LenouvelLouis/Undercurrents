from dataclasses import dataclass
from enum import Enum, auto


class Intent(Enum):
    FACT = auto()
    PREDICT = auto()
    CLUSTER = auto()
    CHAT = auto()


PREDICT_KEYWORDS = [
    "predict", "prochain concert", "next show", "will play", "va jouer",
    "vont-ils jouer", "vont probablement jouer",
]
CLUSTER_KEYWORDS = ["cluster", "era", "ère", "tournée", "tour", "type of show", "type de concert"]
FACT_KEYWORDS = [
    "last time", "dernière fois", "quand", "when", "most played", "le plus joué",
    "how many shows", "combien de concerts", "depuis quand", "period", "période",
]


@dataclass(frozen=True)
class ClassifiedIntent:
    intent: Intent
    mentioned_song_name: str | None = None


def classify(question: str, known_song_names: list[str]) -> ClassifiedIntent:
    lowered = question.lower()
    mentioned_song = _find_mentioned_song(lowered, known_song_names)

    if any(keyword in lowered for keyword in PREDICT_KEYWORDS):
        return ClassifiedIntent(Intent.PREDICT)
    if any(keyword in lowered for keyword in CLUSTER_KEYWORDS):
        return ClassifiedIntent(Intent.CLUSTER)
    if mentioned_song is not None or any(keyword in lowered for keyword in FACT_KEYWORDS):
        return ClassifiedIntent(Intent.FACT, mentioned_song_name=mentioned_song)

    return ClassifiedIntent(Intent.CHAT)


def _find_mentioned_song(lowered_question: str, known_song_names: list[str]) -> str | None:
    candidates = [name for name in known_song_names if name.lower() in lowered_question]
    if not candidates:
        return None
    # Longest match wins, so a short title that happens to be a substring of a longer one
    # (e.g. "Happen" inside "Let It Happen") doesn't shadow the more specific match.
    return max(candidates, key=len)
