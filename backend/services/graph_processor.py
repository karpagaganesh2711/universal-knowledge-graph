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


def node_key(text: str) -> str:
    return normalize_text(text).lower()


def build_knowledge_graph(analysis: dict) -> dict:
    graph = nx.MultiDiGraph()

    entities = analysis.get("entities", [])
    concepts = analysis.get("concepts", [])
    sentences = analysis.get("sentences", [])
    dependencies = analysis.get("dependencies", [])

    unique_nodes = {}

    # ---------------------------------------------------------
    # NODE DATABASE
    # ---------------------------------------------------------
    for item in entities + concepts:
        original_text = clean_text(item.get("text", ""))

        if not original_text:
            continue

        if original_text.startswith("["):
            continue

        normalized = normalize_text(original_text)

        if not normalized:
            continue

        key = node_key(normalized)

        if key not in unique_nodes:
            unique_nodes[key] = {
                "id": normalized,
                "label": normalized,
                "type": item.get("label", "CONCEPT"),
                "description": item.get(
                    "description",
                    "Concept or entity",
                ),
            }

        elif item.get("source") == "named_entity":
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
        )

    # ---------------------------------------------------------
    # SENTENCE → NODE INDEX
    # ---------------------------------------------------------
    sentence_nodes = []

    for sentence in sentences:
        sentence_lower = sentence.lower()

        found = []

        for node in unique_nodes.values():
            label = node["label"]

            if label.lower() in sentence_lower:
                found.append(node)

        seen = set()
        filtered = []

        for node in found:
            key = node_key(node["id"])

            if key not in seen:
                seen.add(key)
                filtered.append(node)

        filtered.sort(
            key=lambda node: sentence_lower.find(
                node["label"].lower()
            )
        )

        sentence_nodes.append(filtered)

    # ---------------------------------------------------------
    # DEPENDENCY RELATIONSHIPS
    # ---------------------------------------------------------
    for sentence_index, token_data in enumerate(dependencies):
        if sentence_index >= len(sentence_nodes):
            break

        nodes_in_sentence = sentence_nodes[sentence_index]

        if len(nodes_in_sentence) < 2:
            continue

        sentence_text = sentences[sentence_index]

        verbs = [
            token
            for token in token_data
            if token.get("pos") in {"VERB", "AUX"}
        ]

        for verb in verbs:
            verb_text = verb.get("text", "").lower()
            verb_lemma = verb.get("lemma", "").lower()

            relationship = (
                RELATION_MAP.get(verb_lemma)
                or RELATION_MAP.get(verb_text)
            )

            if not relationship:
                continue

            subjects = []
            objects = []

            for token in token_data:
                if token.get("head", "").lower() != verb_text:
                    continue

                dependency = token.get("dep", "")

                if dependency in {
                    "nsubj",
                    "nsubjpass",
                    "csubj",
                }:
                    subjects.append(token["text"])

                elif dependency in {
                    "dobj",
                    "obj",
                    "attr",
                    "pobj",
                    "dative",
                }:
                    objects.append(token["text"])

            source = find_best_node(
                subjects,
                nodes_in_sentence,
            )

            target = find_best_node(
                objects,
                nodes_in_sentence,
            )

            if source and target and source["id"] != target["id"]:
                add_relationship(
                    graph=graph,
                    source=source["id"],
                    target=target["id"],
                    relationship=relationship,
                    confidence=0.95,
                    sentence=sentence_text,
                    method="dependency",
                )

    # ---------------------------------------------------------
    # HIGH-CONFIDENCE PATTERN RELATIONSHIPS
    # ---------------------------------------------------------
    for index, sentence in enumerate(sentences):
        if index >= len(sentence_nodes):
            break

        nodes_in_sentence = sentence_nodes[index]

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

        if source and target and source["id"] != target["id"]:
            add_relationship(
                graph=graph,
                source=source["id"],
                target=target["id"],
                relationship=relationship,
                confidence=0.90,
                sentence=sentence,
                method="pattern",
            )

    # ---------------------------------------------------------
    # SERIALIZATION
    # ---------------------------------------------------------
    nodes = [
        {
            "id": node_id,
            "label": data.get("label", node_id),
            "type": data.get("type", "UNKNOWN"),
            "description": data.get("description", ""),
        }
        for node_id, data in graph.nodes(data=True)
    ]

    relationships = [
        {
            "source": source,
            "target": target,
            "relationship": data.get(
                "relationship",
                "mentioned_with",
            ),
            "weight": data.get("weight", 1),
            "confidence": data.get("confidence", 0.5),
            "sentence": data.get("sentence", ""),
            "method": data.get("method", "unknown"),
        }
        for source, target, data in graph.edges(data=True)
    ]

    semantic_relationships = [
        item
        for item in relationships
        if item["relationship"] != "mentioned_with"
    ]

    return {
        "nodes": nodes,
        "relationships": relationships,
        "node_count": len(nodes),
        "relationship_count": len(relationships),
        "semantic_relationship_count": len(
            semantic_relationships
        ),
        "average_relationship_confidence": (
            round(
                sum(
                    item["confidence"]
                    for item in semantic_relationships
                )
                / len(semantic_relationships),
                3,
            )
            if semantic_relationships
            else 0
        ),
    }


def find_best_node(token_texts, nodes):
    for token_text in token_texts:
        token_normalized = node_key(token_text)

        if not token_normalized:
            continue

        exact = []

        for node in nodes:
            node_normalized = node_key(node["label"])

            if token_normalized == node_normalized:
                exact.append(node)

        if exact:
            return exact[0]

        for node in nodes:
            node_normalized = node_key(node["label"])

            if (
                token_normalized in node_normalized
                and len(token_normalized) >= 4
            ):
                return node

    return None


def detect_pattern_relationship(sentence: str):
    lowered = sentence.lower()

    for pattern, relationship in RELATION_PATTERNS:
        if re.search(pattern, lowered):
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

        match = re.search(pattern, lowered)

        if not match:
            continue

        before = lowered[:match.start()]
        after = lowered[match.end():]

        source_candidates = [
            node
            for node in nodes
            if node["label"].lower() in before
        ]

        target_candidates = [
            node
            for node in nodes
            if node["label"].lower() in after
        ]

        if source_candidates and target_candidates:
            return (
                longest_node(source_candidates),
                longest_node(target_candidates),
            )

    return nodes[0], nodes[1]


def longest_node(nodes):
    return max(
        nodes,
        key=lambda node: len(node["label"]),
    )


def relationship_exists(
    graph,
    source,
    target,
    relationship,
):
    if not graph.has_edge(source, target):
        return False

    edges = graph.get_edge_data(source, target)

    for _, data in edges.items():
        if data.get("relationship") == relationship:
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
