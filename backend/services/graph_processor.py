import re

import networkx as nx


RELATION_MAP = {
    "use": "uses",
    "uses": "uses",
    "using": "uses",
    "used": "uses",

    "provide": "provides",
    "provides": "provides",
    "providing": "provides",
    "provided": "provides",

    "contain": "contains",
    "contains": "contains",
    "containing": "contains",

    "include": "includes",
    "includes": "includes",
    "including": "includes",

    "store": "stores",
    "stores": "stores",
    "storing": "stores",
    "stored": "stores",

    "manage": "manages",
    "manages": "manages",
    "managing": "manages",
    "managed": "manages",

    "access": "accesses",
    "accesses": "accesses",
    "accessing": "accesses",
    "accessed": "accesses",

    "create": "creates",
    "creates": "creates",
    "creating": "creates",
    "created": "creates",

    "support": "supports",
    "supports": "supports",
    "supporting": "supports",

    "define": "defines",
    "defines": "defines",
    "defining": "defines",
    "defined": "defines",

    "connect": "connects",
    "connects": "connects",
    "connecting": "connects",

    "retrieve": "retrieves",
    "retrieves": "retrieves",
    "retrieving": "retrieves",

    "analyze": "analyzes",
    "analyzes": "analyzes",
    "analyzing": "analyzes",

    "process": "processes",
    "processes": "processes",
    "processing": "processes",

    "represent": "represents",
    "represents": "represents",
    "representing": "represents",

    "maintain": "maintains",
    "maintains": "maintains",
    "maintaining": "maintains",

    "describe": "describes",
    "describes": "describes",
    "describing": "describes",
}


STOPWORDS = {"a", "an", "the"}


CONCEPT_ALIASES = {
    "ai": "artificial intelligence",
    "artificial intelligence systems": "artificial intelligence",
    "artificial intelligence system": "artificial intelligence",

    "ml": "machine learning",
    "machine learning models": "machine learning",
    "machine learning model": "machine learning",

    "knowledge graphs": "knowledge graph",
    "knowledge graph system": "knowledge graph",
    "knowledge graph systems": "knowledge graph",

    "databases": "database",
    "database systems": "database",
    "database system": "database",

    "cloud computing services": "cloud computing",
    "cloud computing service": "cloud computing",
    "cloud applications": "cloud application",
    "cloud services": "cloud service",
}


RELATION_PATTERNS = [
    (r"\bconsists of\b", "consists_of"),
    (r"\bdepends on\b", "depends_on"),
    (r"\bis part of\b", "part_of"),
    (r"\bis used by\b", "used_by"),
    (r"\brefers to\b", "refers_to"),
]


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_text(text: str) -> str:
    text = clean_text(text)

    text = re.sub(
        r"^\[HEADING\]\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    words = text.split()

    while words and words[0].lower() in STOPWORDS:
        words.pop(0)

    return " ".join(words).strip()


def canonical_concept(text: str) -> str:
    normalized = normalize_text(text)
    key = normalized.lower()

    return CONCEPT_ALIASES.get(
        key,
        normalized,
    )


def node_key(text: str) -> str:
    return canonical_concept(text).lower()


def build_knowledge_graph(analysis: dict) -> dict:
    graph = nx.MultiDiGraph()

    entities = analysis.get("entities", [])
    concepts = analysis.get("concepts", [])
    sentences = analysis.get("sentences", [])
    dependencies = analysis.get("dependencies", [])

    unique_nodes = {}

    # =========================================================
    # NODE DATABASE
    # =========================================================

    for item in entities + concepts:
        original_text = clean_text(
            item.get("text", "")
        )

        if not original_text:
            continue

        if original_text.startswith("["):
            continue

        normalized = normalize_text(
            original_text
        )

        if not normalized:
            continue

        canonical = canonical_concept(
            normalized
        )

        key = canonical.lower()

        if key not in unique_nodes:
            unique_nodes[key] = {
                "id": canonical,
                "label": canonical,
                "aliases": [normalized],
                "type": item.get(
                    "label",
                    "CONCEPT",
                ),
                "description": item.get(
                    "description",
                    "Concept or entity",
                ),
            }
        else:
            if normalized not in unique_nodes[key]["aliases"]:
                unique_nodes[key]["aliases"].append(
                    normalized
                )

            if item.get("source") == "named_entity":
                unique_nodes[key]["type"] = item.get(
                    "label",
                    unique_nodes[key]["type"],
                )

                unique_nodes[key]["description"] = item.get(
                    "description",
                    unique_nodes[key]["description"],
                )

    for node in unique_nodes.values():
        graph.add_node(
            node["id"],
            label=node["label"],
            type=node["type"],
            description=node["description"],
            aliases=node["aliases"],
        )

    # =========================================================
    # SENTENCE → NODE INDEX
    # =========================================================

    sentence_nodes = []

    for sentence in sentences:
        sentence_lower = sentence.lower()

        found = []

        for node in unique_nodes.values():
            best_position = None

            values = [
                node["label"],
                *node.get("aliases", []),
            ]

            for value in values:
                position = sentence_lower.find(
                    value.lower()
                )

                if position != -1:
                    if (
                        best_position is None
                        or position < best_position
                    ):
                        best_position = position

            if best_position is not None:
                found.append(
                    (
                        best_position,
                        node,
                    )
                )

        seen = set()
        filtered = []

        for position, node in found:
            key = node_key(node["id"])

            if key in seen:
                continue

            seen.add(key)

            filtered.append(
                {
                    "node": node,
                    "position": position,
                }
            )

        filtered.sort(
            key=lambda item: item["position"]
        )

        sentence_nodes.append(filtered)

    # =========================================================
    # DEPENDENCY RELATIONSHIPS
    # =========================================================

    for sentence_index, token_data in enumerate(
        dependencies
    ):
        if sentence_index >= len(sentence_nodes):
            break

        sentence_entries = sentence_nodes[
            sentence_index
        ]

        if len(sentence_entries) < 2:
            continue

        sentence_text = sentences[
            sentence_index
        ]

        verbs = [
            token
            for token in token_data
            if token.get("pos") in {
                "VERB",
                "AUX",
            }
        ]

        for verb in verbs:
            verb_text = verb.get(
                "text",
                "",
            ).lower()

            verb_lemma = verb.get(
                "lemma",
                "",
            ).lower()

            relationship = (
                RELATION_MAP.get(verb_lemma)
                or RELATION_MAP.get(verb_text)
            )

            if not relationship:
                continue

            subjects = []
            objects = []

            for token in token_data:
                if token.get(
                    "head",
                    "",
                ).lower() != verb_text:
                    continue

                dependency = token.get(
                    "dep",
                    "",
                )

                if dependency in {
                    "nsubj",
                    "nsubjpass",
                    "csubj",
                }:
                    subjects.append(
                        token["text"]
                    )

                elif dependency in {
                    "dobj",
                    "obj",
                    "attr",
                    "pobj",
                    "dative",
                }:
                    objects.append(
                        token["text"]
                    )

            available_nodes = [
                entry["node"]
                for entry in sentence_entries
            ]

            source = find_best_node(
                subjects,
                available_nodes,
            )

            target = find_best_node(
                objects,
                available_nodes,
            )

            # -------------------------------------------------
            # POSITION FALLBACK
            # -------------------------------------------------

            if not source or not target:
                verb_position = sentence_text.lower().find(
                    verb_text
                )

                if verb_position != -1:
                    before = [
                        entry
                        for entry in sentence_entries
                        if entry["position"]
                        < verb_position
                    ]

                    after = [
                        entry
                        for entry in sentence_entries
                        if entry["position"]
                        > verb_position
                    ]

                    if not source and before:
                        source = before[-1]["node"]

                    if not target and after:
                        target = after[0]["node"]

            if (
                source
                and target
                and source["id"] != target["id"]
            ):
                add_relationship(
                    graph=graph,
                    source=source["id"],
                    target=target["id"],
                    relationship=relationship,
                    confidence=0.95,
                    sentence=sentence_text,
                    method="dependency",
                )

    # =========================================================
    # HIGH-CONFIDENCE PATTERN RELATIONSHIPS
    # =========================================================

    for index, sentence in enumerate(sentences):
        if index >= len(sentence_nodes):
            break

        nodes_in_sentence = [
            entry["node"]
            for entry in sentence_nodes[index]
        ]

        if len(nodes_in_sentence) < 2:
            continue

        relationship = detect_pattern_relationship(
            sentence
        )

        if not relationship:
            continue

        source, target = choose_pattern_nodes(
            sentence,
            nodes_in_sentence,
            relationship,
        )

        if (
            source
            and target
            and source["id"] != target["id"]
        ):
            add_relationship(
                graph=graph,
                source=source["id"],
                target=target["id"],
                relationship=relationship,
                confidence=0.90,
                sentence=sentence,
                method="pattern",
            )

                # =========================================================
    # CONTEXTUAL SEMANTIC RELATIONSHIPS
    # =========================================================

    for index, sentence in enumerate(sentences):
        if index >= len(sentence_nodes):
            break

        nodes_in_sentence = [
            entry["node"]
            for entry in sentence_nodes[index]
        ]

        unique_nodes = []
        seen_ids = set()

        for node in nodes_in_sentence:
            node_id = node.get("id")

            if not node_id or node_id in seen_ids:
                continue

            seen_ids.add(node_id)
            unique_nodes.append(node)

        if len(unique_nodes) < 2:
            continue

        sentence_lower = sentence.lower()

        semantic_hints = []

        if any(
            phrase in sentence_lower
            for phrase in [
                "learn from data",
                "learning from data",
                "machine learning",
                "training data",
                "predictive models",
                "make predictions",
            ]
        ):
            semantic_hints.append(
                "learns_from"
            )

        if any(
            phrase in sentence_lower
            for phrase in [
                "knowledge graph",
                "knowledge graphs",
                "semantic connections",
                "related information",
                "entities and relationships",
            ]
        ):
            semantic_hints.append(
                "semantically_connects"
            )

        if any(
            phrase in sentence_lower
            for phrase in [
                "natural language processing",
                "nlp systems",
                "human language",
                "linguistic patterns",
            ]
        ):
            semantic_hints.append(
                "processes_language"
            )

        if any(
            phrase in sentence_lower
            for phrase in [
                "database",
                "databases",
                "structured information",
                "data integrity",
            ]
        ):
            semantic_hints.append(
                "manages_information"
            )

        if any(
            phrase in sentence_lower
            for phrase in [
                "cloud computing",
                "cloud platforms",
                "distributed resources",
            ]
        ):
            semantic_hints.append(
                "provides_computing"
            )

        if semantic_hints:
            contextual_relationship = semantic_hints[0]
        else:
            contextual_relationship = "related_to"

        for source_index, source_node in enumerate(
            unique_nodes
        ):
            for target_node in unique_nodes[
                source_index + 1:
            ]:
                source_id = source_node.get("id")
                target_id = target_node.get("id")

                if not source_id or not target_id:
                    continue

                if source_id == target_id:
                    continue

                add_relationship(
                    graph=graph,
                    source=source_id,
                    target=target_id,
                    relationship=contextual_relationship,
                    confidence=0.78,
                    sentence=sentence,
                    method="semantic-context",
                )

                add_relationship(
                    graph=graph,
                    source=target_id,
                    target=source_id,
                    relationship=contextual_relationship,
                    confidence=0.78,
                    sentence=sentence,
                    method="semantic-context",
                )

    # =========================================================
    # GRAPH INTELLIGENCE METADATA
    # =========================================================

    # =========================================================
    # GRAPH INTELLIGENCE METADATA
    # =========================================================

    for node_id in graph.nodes:
        degree = graph.degree(node_id)

        graph.nodes[node_id]["degree"] = degree
        graph.nodes[node_id]["importance"] = calculate_node_importance(
            graph,
            node_id,
        )

    for source, target, data in graph.edges(
        data=True
    ):
        confidence = data.get(
            "confidence",
            0.5,
        )

        degree_bonus = min(
            (
                graph.degree(source)
                + graph.degree(target)
            )
            * 0.01,
            0.05,
        )

        data["score"] = round(
            min(
                confidence + degree_bonus,
                1.0,
            ),
            3,
        )

    # =========================================================
    # SERIALIZATION
    # =========================================================

    nodes = [
        {
            "id": node_id,
            "label": data.get(
                "label",
                node_id,
            ),
            "type": data.get(
                "type",
                "UNKNOWN",
            ),
            "description": data.get(
                "description",
                "",
            ),
            "aliases": data.get(
                "aliases",
                [],
            ),
            "degree": data.get(
                "degree",
                0,
            ),
            "importance": data.get(
                "importance",
                0,
            ),
        }
        for node_id, data in graph.nodes(
            data=True
        )
    ]

    relationships = [
        {
            "source": source,
            "target": target,
            "relationship": data.get(
                "relationship",
                "mentioned_with",
            ),
            "weight": data.get(
                "weight",
                1,
            ),
            "confidence": data.get(
                "confidence",
                0.5,
            ),
            "score": data.get(
                "score",
                data.get(
                    "confidence",
                    0.5,
                ),
            ),
            "sentence": data.get(
                "sentence",
                "",
            ),
            "method": data.get(
                "method",
                "unknown",
            ),
        }
        for source, target, data in graph.edges(
            data=True
        )
    ]

    semantic_relationships = [
        item
        for item in relationships
        if item["relationship"]
        != "mentioned_with"
    ]

    return {
        "nodes": nodes,
        "relationships": relationships,
        "node_count": len(nodes),
        "relationship_count": len(
            relationships
        ),
        "semantic_relationship_count": len(
            semantic_relationships
        ),
        "average_relationship_confidence": (
            round(
                sum(
                    item["confidence"]
                    for item in semantic_relationships
                )
                / len(
                    semantic_relationships
                ),
                3,
            )
            if semantic_relationships
            else 0
        ),
        "average_relationship_score": (
            round(
                sum(
                    item["score"]
                    for item in semantic_relationships
                )
                / len(
                    semantic_relationships
                ),
                3,
            )
            if semantic_relationships
            else 0
        ),
        "most_important_nodes": sorted(
            [
                {
                    "id": node_id,
                    "importance": data.get(
                        "importance",
                        0,
                    ),
                }
                for node_id, data in graph.nodes(
                    data=True
                )
            ],
            key=lambda item: item["importance"],
            reverse=True,
        )[:10],
    }


def calculate_node_importance(
    graph,
    node_id,
):
    degree = graph.degree(node_id)

    if graph.number_of_nodes() <= 1:
        return 0

    normalized_degree = (
        degree
        / (graph.number_of_nodes() - 1)
    )

    return round(
        normalized_degree,
        3,
    )


def find_best_node(
    token_texts,
    nodes,
):
    for token_text in token_texts:
        token_key = node_key(
            token_text
        )

        if not token_key:
            continue

        for node in nodes:
            values = [
                node.get(
                    "label",
                    "",
                ),
                *node.get(
                    "aliases",
                    [],
                ),
            ]

            for value in values:
                value_key = node_key(
                    value
                )

                if token_key == value_key:
                    return node

                token_words = set(
                    token_key.split()
                )

                value_words = set(
                    value_key.split()
                )

                if (
                    len(token_key) >= 4
                    and token_words
                    and token_words.issubset(
                        value_words
                    )
                ):
                    return node

    return None


def detect_pattern_relationship(
    sentence: str,
):
    lowered = sentence.lower()

    for pattern, relationship in RELATION_PATTERNS:
        if re.search(
            pattern,
            lowered,
        ):
            return relationship

    return None


def choose_pattern_nodes(
    sentence,
    nodes,
    relationship,
):
    lowered = sentence.lower()

    for pattern, relation in RELATION_PATTERNS:
        if relation != relationship:
            continue

        match = re.search(
            pattern,
            lowered,
        )

        if not match:
            continue

        before = lowered[
            :match.start()
        ]

        after = lowered[
            match.end():
        ]

        source_candidates = [
            node
            for node in nodes
            if any(
                value.lower() in before
                for value in [
                    node["label"],
                    *node.get(
                        "aliases",
                        [],
                    ),
                ]
            )
        ]

        target_candidates = [
            node
            for node in nodes
            if any(
                value.lower() in after
                for value in [
                    node["label"],
                    *node.get(
                        "aliases",
                        [],
                    ),
                ]
            )
        ]

        if (
            source_candidates
            and target_candidates
        ):
            return (
                longest_node(
                    source_candidates
                ),
                longest_node(
                    target_candidates
                ),
            )

    return nodes[0], nodes[1]


def longest_node(nodes):
    return max(
        nodes,
        key=lambda node: len(
            node["label"]
        ),
    )


def relationship_exists(
    graph,
    source,
    target,
    relationship,
):
    if not graph.has_edge(
        source,
        target,
    ):
        return False

    edges = graph.get_edge_data(
        source,
        target,
    )

    for _, data in edges.items():
        if data.get(
            "relationship"
        ) == relationship:
            return True

    return False


def add_relationship(
    graph,
    source,
    target,
    relationship,
    confidence,
    sentence,
    method,
):
    if relationship_exists(
        graph,
        source,
        target,
        relationship,
    ):
        return

    graph.add_edge(
        source,
        target,
        relationship=relationship,
        weight=1,
        confidence=confidence,
        sentence=sentence,
        method=method,
    )
