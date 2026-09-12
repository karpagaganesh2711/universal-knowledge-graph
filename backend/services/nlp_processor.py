import re

import spacy


nlp = spacy.load("en_core_web_sm")


TECHNICAL_PERSON_FALSE_POSITIVES = {
    "cloud computing",
    "machine learning",
    "artificial intelligence",
    "knowledge graph",
    "knowledge graphs",
    "database architecture",
    "cloud computing services",
}


def normalize_input(text: str) -> str:
    lines = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        if re.fullmatch(r"\[PAGE \d+\]", line, re.IGNORECASE):
            continue

        if line.upper().startswith("[HEADING]"):
            heading = re.sub(
                r"^\[HEADING\]\s*",
                "",
                line,
                flags=re.IGNORECASE,
            ).strip()

            if heading:
                lines.append(f"{heading}.")

            continue

        lines.append(line)

    return "\n\n".join(lines)


def is_heading_sentence(sentence: str) -> bool:
    return bool(
        re.match(
            r"^\s*\[HEADING\]",
            sentence,
            re.IGNORECASE,
        )
    )


def analyze_text(text: str) -> dict:
    text = normalize_input(text)
    doc = nlp(text)

    sentences = [
        sentence.text.strip()
        for sentence in doc.sents
        if sentence.text.strip()
    ]

    entities = []
    seen_entities = set()

    for entity in doc.ents:
        value = entity.text.strip()
        key = value.lower()

        if not value or key in seen_entities:
            continue

        # spaCy can occasionally misclassify technical terms as PERSON.
        if (
            entity.label_ == "PERSON"
            and key in TECHNICAL_PERSON_FALSE_POSITIVES
        ):
            continue

        seen_entities.add(key)

        entities.append({
            "text": value,
            "label": entity.label_,
            "description": spacy.explain(entity.label_) or "",
            "source": "named_entity",
        })

    concepts = []
    seen_concepts = set()

    for chunk in doc.noun_chunks:
        value = chunk.text.strip()

        if not value:
            continue

        words = [
            token.text
            for token in chunk
            if token.dep_ != "det"
        ]

        value = " ".join(words).strip()

        if not value:
            continue

        key = value.lower()

        if key not in seen_concepts:
            seen_concepts.add(key)

            concepts.append({
                "text": value,
                "label": "CONCEPT",
                "description": "Concept or noun phrase",
                "source": "noun_phrase",
            })

    for token in doc:
        if token.pos_ not in {"NOUN", "PROPN"}:
            continue

        if token.is_stop or token.is_punct:
            continue

        inside_chunk = any(
            token.i >= chunk.start
            and token.i < chunk.end
            and len(chunk) > 1
            for chunk in doc.noun_chunks
        )

        if inside_chunk:
            continue

        value = token.text.strip()
        key = value.lower()

        if key not in seen_concepts:
            seen_concepts.add(key)

            concepts.append({
                "text": value,
                "label": "CONCEPT",
                "description": "Concept",
                "source": "noun",
            })

    dependencies = []

    for sentence in doc.sents:
        dependencies.append([
            {
                "text": token.text,
                "lemma": token.lemma_,
                "pos": token.pos_,
                "dep": token.dep_,
                "head": token.head.text,
            }
            for token in sentence
        ])

    return {
        "sentences": sentences,
        "entities": entities,
        "concepts": concepts,
        "dependencies": dependencies,
        "sentence_count": len(sentences),
        "entity_count": len(entities),
        "concept_count": len(concepts),
        "token_count": len(doc),
    }
