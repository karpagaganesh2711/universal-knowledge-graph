import spacy

nlp = spacy.load("en_core_web_sm")


def analyze_text(text: str) -> dict:
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

        if value and key not in seen_entities:
            seen_entities.add(key)

            entities.append({
                "text": value,
                "label": entity.label_,
                "description": spacy.explain(entity.label_) or "",
                "source": "named_entity",
            })

    concepts = []
    seen_concepts = set()

    # Extract noun chunks first.
    for chunk in doc.noun_chunks:
        value = chunk.text.strip()

        if not value:
            continue

        # Remove determiners.
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

    # Add important standalone nouns only when they were not
    # already represented by a noun phrase.
    for token in doc:

        if token.pos_ not in {"NOUN", "PROPN"}:
            continue

        if token.is_stop or token.is_punct:
            continue

        # Skip nouns that are already part of a larger noun chunk.
        inside_chunk = False

        for chunk in doc.noun_chunks:
            if token.i >= chunk.start and token.i < chunk.end:
                if len(chunk) > 1:
                    inside_chunk = True
                    break

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
