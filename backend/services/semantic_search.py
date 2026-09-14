from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer


MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_model():
    return SentenceTransformer(MODEL_NAME)


def normalize(value):
    return " ".join(
        str(value).lower().strip().split()
    )


def build_node_text(node, relationships):
    parts = [
        node.get("label", ""),
        node.get("description", ""),
        " ".join(node.get("aliases", [])),
    ]

    node_id = node.get("id")

    related_context = []

    for relationship in relationships:
        source = relationship.get("source")
        target = relationship.get("target")

        if source == node_id:
            related_context.append(
                relationship.get("relationship", "")
            )
            related_context.append(
                target or ""
            )

        elif target == node_id:
            related_context.append(
                relationship.get("relationship", "")
            )
            related_context.append(
                source or ""
            )

    if related_context:
        parts.append(
            "Related concepts: "
            + " ".join(related_context)
        )

    return " ".join(
        part.strip()
        for part in parts
        if part and part.strip()
    )


def lexical_score(query, node):
    query_normalized = normalize(query)

    if not query_normalized:
        return 0.0

    values = [
        normalize(node.get("label", "")),
        normalize(node.get("id", "")),
        normalize(node.get("description", "")),
    ]

    values.extend(
        normalize(alias)
        for alias in node.get("aliases", [])
    )

    if query_normalized in values:
        return 1.0

    if any(
        query_normalized in value
        for value in values
        if value
    ):
        return 0.85

    query_words = set(
        query_normalized.split()
    )

    if not query_words:
        return 0.0

    best_overlap = 0.0

    for value in values:
        if not value:
            continue

        value_words = set(value.split())

        overlap = len(
            query_words & value_words
        ) / len(query_words)

        best_overlap = max(
            best_overlap,
            overlap,
        )

    return round(best_overlap, 4)


def importance_score(node):
    importance = float(
        node.get("importance", 0) or 0
    )

    return min(
        max(importance, 0.0),
        1.0,
    )


@lru_cache(maxsize=8)
def cached_profile_embeddings(node_signature):
    model = get_model()

    if not node_signature:
        return np.empty((0, 384))

    embeddings = model.encode(
        list(node_signature),
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    return np.asarray(embeddings)


@lru_cache(maxsize=8)
def cached_label_embeddings(label_signature):
    model = get_model()

    if not label_signature:
        return np.empty((0, 384))

    embeddings = model.encode(
        list(label_signature),
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    return np.asarray(embeddings)


def semantic_search(
    query,
    nodes,
    relationships=None,
    limit=10,
):
    query = query.strip()

    if not query or not nodes:
        return []

    relationships = relationships or []

    model = get_model()

    query_embedding = model.encode(
        [query],
        normalize_embeddings=True,
        show_progress_bar=False,
    )[0]

    node_profiles = tuple(
        build_node_text(
            node,
            relationships,
        )
        for node in nodes
    )

    node_labels = tuple(
        node.get("label", "")
        for node in nodes
    )

    profile_embeddings = cached_profile_embeddings(
        node_profiles
    )

    label_embeddings = cached_label_embeddings(
        node_labels
    )

    profile_similarities = np.dot(
        profile_embeddings,
        query_embedding,
    )

    label_similarities = np.dot(
        label_embeddings,
        query_embedding,
    )

    results = []

    query_words = set(
        normalize(query).split()
    )

    for index, node in enumerate(nodes):
        profile_similarity = max(
            float(
                profile_similarities[index]
            ),
            0.0,
        )

        label_similarity = max(
            float(
                label_similarities[index]
            ),
            0.0,
        )

        lexical = lexical_score(
            query,
            node,
        )

        importance = importance_score(
            node
        )

        label = normalize(
            node.get("label", "")
        )

        label_words = set(
            label.split()
        )

        word_match = 0.0

        if query_words and label_words:
            word_match = len(
                query_words & label_words
            ) / len(query_words)

        semantic_similarity = (
            label_similarity * 0.60
            + profile_similarity * 0.40
        )

        relevance = (
            semantic_similarity * 0.55
            + lexical * 0.15
            + word_match * 0.20
            + importance * 0.10
        )

        results.append(
            {
                "id": node.get("id"),
                "label": node.get("label"),
                "type": node.get("type"),
                "description": node.get(
                    "description",
                    "",
                ),
                "importance": node.get(
                    "importance",
                    0,
                ),
                "degree": node.get(
                    "degree",
                    0,
                ),
                "semantic_similarity": round(
                    semantic_similarity,
                    4,
                ),
                "lexical_score": round(
                    lexical,
                    4,
                ),
                "relevance_score": round(
                    relevance,
                    4,
                ),
            }
        )

    results.sort(
        key=lambda item: item[
            "relevance_score"
        ],
        reverse=True,
    )

    return results[:limit]