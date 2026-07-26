"""Deterministic, offline, text-only extractor.

``HeuristicExtractor`` reads raw episode text (``synopsis`` or ``body``) and
derives a graph using nothing but regular expressions and small hand-written
word lists. It exists so `app/extraction.py`'s ``Extractor`` protocol has an
implementation that can actually be wrong: unlike ``FakeExtractor`` (which
echoes its input) or a hand-authored manifest (which is the answer key), this
module has never seen `data/manifest/last_monsoon.yaml` and was written
purely from the shape of the rules below. Its errors -- missed contradictions,
missed promises, wrong payoff targets -- are exactly what the resolver's
precision/recall numbers are supposed to measure. A rule that misses a real
contradiction is not a bug in this module; it is the instrument working.

No network calls, no model calls, no dependency beyond the standard library.
Identical input text always yields byte-identical output: every collection
this module builds is sorted by a stable key before being returned, and no
step consults wall-clock time, randomness, or dict/set iteration order.

RULES (this is the complete list -- if a behaviour isn't described here, the
extractor doesn't do it):

1. Nodes and excerpts
   Every syntactically valid row becomes exactly one ``NarrativeNode`` (id
   ``n-{episode}``) and one ``Excerpt`` (id ``ex-{episode}``). A row is
   rejected (counted in ``rejected``, no node emitted) if it is not a dict,
   has no usable ``episode`` (missing or not int-convertible), or has no text
   in either ``synopsis`` or ``body``.

2. Promise detection (opens a `promise` LedgerEntry)
   A row's text is scanned for four independent categories of
   obligation-opening language; each category that matches at least once in
   an episode opens at most one promise entry for that episode (so one
   episode can open several promises, one per category, but never two for
   the same category):
     - "promise_verb": /\\bpromises?\\b/, /\\bswears?\\b/, /\\bvows?\\b/,
       /\\bwill return\\b|\\bwill (?:come|be) back\\b/
     - "future_marker": /\\bone day\\b/, /\\bsomeday\\b/
     - "obligation": /\\bmust\\s+\\w+/ (a bare modal "must")
     - "open_question": any sentence in the text ending in "?"
   Each promise entry cites that episode's excerpt and nothing else. This
   catches explicit promise language but not promises implied only by
   narrative structure (e.g. Chekhov's gun with no verbal marker).

3. Contradiction detection (opens a `contradiction` LedgerEntry)
   A row is scanned for a negated capability or fact:
     - /never (?:learned|learnt) to (\\w+)/  -> capability = captured verb
     - /\\bcan(?:not|'t)\\s+(\\w+)/           -> capability = captured verb
     - /\\b(?:is|was)\\s+dead\\b/            -> capability = the pseudo-verb "dead"
   Each hit is remembered (episode, capability, salient words of that
   sentence's episode text) as a pending negation. Every later episode is
   checked against every still-open pending negation: the negation's
   capability is stemmed (crude suffix-stripping: -ing/-ed/-es/-s) and looked
   up in a small hand-written synonym cluster (e.g. "dead" is contradicted
   by verbs implying being alive: "speak",
   "appear", "return", "arrive", "walk", "live"; capabilities outside the
   cluster table only match their own stem). A contradiction entry fires only
   if, in addition to the stem/cluster hit, the two episodes also share at
   least one salient word (see below) -- this is a deliberate precision
   trade-off: it will miss a contradiction about the same character if the
   later episode refers to them only by pronoun, but it avoids firing on
   coincidental verb reuse between unrelated characters. Each pending
   negation is consumed by at most one contradiction (first later episode
   that matches, in episode order), so a single negated claim cannot spawn
   more than one entry. ``episodes`` on the entry is ``[earliest, latest]``.

4. Salient words (used only for contradiction/payoff matching, not emitted
   directly)
   Tokens are extracted with /[A-Za-z']+/, lowercased, and kept if longer
   than 2 characters and not in a fixed ~60-word stopword list of closed-class
   English words (articles, pronouns, auxiliaries, conjunctions, common
   prepositions). This is a bag-of-words overlap, not coreference resolution:
   it will treat "Tara" and "she" as unrelated, and it will treat two
   different characters who happen to share a word (e.g. both scenes mention
   "water") as related.

5. Payoff detection (emits a `PayoffLink`, never verified)
   A row is scanned for resolution language: /\\bfinally\\b/, /\\bat last\\b/,
   /\\bit was never\\b/, /\\bthe truth was\\b/. On a hit, the extractor looks
   at every entry opened by an earlier episode that has not yet been given a
   payoff, in reverse chronological order (most recent first), and links to
   the first one whose salient words intersect the current episode's salient
   words. If none intersect, no link is emitted for that episode -- the
   extractor does not guess. ``PayoffLink.verified`` is left at its default
   ``False`` on every link this module ever produces; nothing in this module
   ever sets it to ``True``. That is intentional: an extracted payoff is a
   claim, not a fact, and the ledger resolver is the only place trust can be
   granted (via an explicit verifier), so every extractor-derived
   contradiction resolves ``broken`` until something independent verifies it.

Known blind spots (a non-exhaustive list, kept here so they're not
rediscovered as "bugs"):
   - No coreference: pronouns never link back to a named entity.
   - No negation scope tracking beyond the three fixed patterns above --
     "It's not true that she can't swim" reads as a negated claim.
   - Promise/contradiction/payoff windows are unbounded in episode distance;
     there is no recency decay.
   - Only English, only the literal strings/patterns listed above.
"""

from __future__ import annotations

import re

from app.extraction import ExtractionResult
from app.narrative_models import Excerpt, LedgerEntry, NarrativeNode, PayoffLink

_STOPWORDS = frozenset(
    """
    a an the and or but to of in on at is was were are be been being she he
    it they them her his their that this these those i you we her him us
    for with as by from into onto up down out over under again further then
    once here there when where why how all any both each few more most
    other some such no nor not only own same so than too very s t can will
    just don should now had has have did do does won't didn't isn't aren't
    wasn't weren't never cannot admits finds
    """.split()
)

_PROMISE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("promise_verb", re.compile(r"\bpromises?\b|\bswears?\b|\bvows?\b|\bwill\s+(?:return|come\s+back|be\s+back)\b", re.IGNORECASE)),
    ("future_marker", re.compile(r"\bone day\b|\bsomeday\b", re.IGNORECASE)),
    ("obligation", re.compile(r"\bmust\s+\w+", re.IGNORECASE)),
]
_QUESTION_PATTERN = re.compile(r"[^.!?]*\?")

_NEGATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bnever\s+(?:learned|learnt)\s+to\s+(\w+)", re.IGNORECASE),
    re.compile(r"\bcan(?:not|'t)\s+(\w+)", re.IGNORECASE),
]
_DEAD_PATTERN = re.compile(r"\b(?:is|was)\s+dead\b", re.IGNORECASE)

_PAYOFF_PATTERN = re.compile(
    r"\bfinally\b|\bat last\b|\bit was never\b|\bthe truth was\b", re.IGNORECASE
)

_SYNONYM_CLUSTERS: dict[str, frozenset[str]] = {
    # No "swim"/"dive" entry: a prior version had one, but it existed only
    # because it happened to clear one specific manifest fixture (a
    # character who "can't swim" later "dives"). Swimming and diving are not
    # actually the same capability -- someone who cannot swim diving into
    # water is the *point* of that contradiction, not evidence the verbs are
    # synonyms in general prose. A rule earning its place only by matching
    # one fixture's vocabulary is worse than no rule: it inflates apparent
    # recall without generalizing. Left out; the extractor is allowed to
    # miss swim/dive contradictions until a genuinely general case justifies
    # one.
    "dead": frozenset({"speak", "appear", "return", "arrive", "walk", "live"}),
    "walk": frozenset({"walk", "run"}),
    "speak": frozenset({"speak", "talk", "say"}),
    "see": frozenset({"see", "watch", "look"}),
    "fly": frozenset({"fly", "soar"}),
    "remember": frozenset({"remember", "recall"}),
}

_TOKEN_PATTERN = re.compile(r"[A-Za-z']+")


def _stem(word: str) -> str:
    """Crude suffix stripper -- just enough to fold "welds"/"welded"/"welding"
    onto "weld" for cluster matching. Not a real stemmer: it knows nothing
    about irregular verbs (e.g. "spoke" does not stem to "speak")."""
    word = word.lower()
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("ing") and len(word) > 5:
        return word[:-3]
    if word.endswith("ed") and len(word) > 4:
        return word[:-2]
    if word.endswith("es") and len(word) > 4 and (word[-3] in "sxz" or word.endswith(("ches", "shes"))):
        return word[:-2]
    if word.endswith("s") and len(word) > 3:
        return word[:-1]
    return word


def _salient_words(text: str) -> set[str]:
    return {
        match.lower()
        for match in _TOKEN_PATTERN.findall(text)
        if len(match) > 2 and match.lower() not in _STOPWORDS
    }


def _proper_nouns(text: str) -> list[str]:
    """Capitalised words, as a stand-in for named entities.

    `LedgerEntry.entities` must hold names, not a bag of content words. Two
    reasons, and the second is the load-bearing one:

    * It is user-visible. Surfacing ["'because", "'everyone", "'she"] next to a
      finding reads as broken software.
    * `app/features.py::_active_threads` counts distinct entities across open
      obligations, so a word bag inflates that feature into "how many different
      words appear near an open thread" rather than "how many characters are
      carrying one".

    Crude by design -- no NER, no coreference, and it will take a
    sentence-initial word for a name. That is consistent with the rest of this
    extractor being a deliberate floor.
    """
    found = {word for word in re.findall(r"\b[A-Z][a-z]+\b", text)}
    return sorted(found - _SENTENCE_STARTERS)


# Capitalised only because they open a sentence. Without this the bag fills
# with "The", "She", "When" instead of characters.
_SENTENCE_STARTERS = {
    "The", "She", "He", "They", "It", "There", "Then", "When", "Where", "What",
    "Why", "How", "But", "And", "For", "Not", "No", "Yes", "That", "This",
    "These", "Those", "If", "As", "At", "By", "In", "On", "Of", "To", "From",
    "With", "Without", "After", "Before", "Once", "Now", "Later", "Even",
    "Still", "Only", "Just", "One", "Two", "Three", "Her", "His", "Their",
    "Its", "Every", "Each", "All", "Some", "Any", "Both", "Neither", "Either",
    "Because", "Although", "While", "Until", "Since", "So", "Or", "Nor",
    "My", "Your", "Our", "Nobody", "Nothing", "Someone", "Somebody",
    "Everyone", "Everybody", "Anyone", "Anybody", "Never", "Always",
    "Maybe", "Perhaps", "Instead", "Meanwhile", "Afterwards", "Tonight",
    "Yesterday", "Tomorrow", "Today", "Here", "Look", "Listen", "Explain",
    "Tell", "Ask", "Let", "Get", "Come", "Go", "Stop", "Wait", "Please",
}


class _PendingNegation:
    # `text` is carried so a contradiction entry can name the characters from
    # *both* episodes it spans, not just the resolving one.
    __slots__ = ("episode", "capability_stem", "words", "excerpt_id", "text")

    def __init__(
        self, episode: int, capability_stem: str, words: set[str], excerpt_id: str, text: str = ""
    ) -> None:
        self.episode = episode
        self.capability_stem = capability_stem
        self.words = words
        self.excerpt_id = excerpt_id
        self.text = text


class HeuristicExtractor:
    """See module docstring for the complete, exhaustive rule list."""

    def extract(self, episodes: list[dict]) -> ExtractionResult:
        result = ExtractionResult()
        rows: list[tuple[int, str, dict]] = []

        for row in episodes:
            parsed = self._validate(row)
            if parsed is None:
                result.rejected += 1
                continue
            rows.append(parsed)

        rows.sort(key=lambda item: item[0])

        pending_negations: list[_PendingNegation] = []
        open_entries: list[LedgerEntry] = []
        resolved_target_ids: set[str] = set()

        for episode, text, _row in rows:
            excerpt_id = f"ex-{episode}"
            node_id = f"n-{episode}"
            words = _salient_words(text)

            result.nodes.append(
                NarrativeNode(
                    id=node_id,
                    episode=episode,
                    perceived_index=episode,
                    summary=text[:200],
                    entities=_proper_nouns(text),
                    excerpt_id=excerpt_id,
                )
            )
            result.excerpts.append(Excerpt(id=excerpt_id, episode=episode, text=text))

            # -- promise detection --------------------------------------
            for category, pattern in _PROMISE_PATTERNS:
                if pattern.search(text):
                    entry = LedgerEntry(
                        id=f"promise-{episode}-{category}",
                        kind="promise",
                        description=f"Episode {episode} opens an obligation ({category}).",
                        episodes=[episode],
                        excerpt_ids=[excerpt_id],
                        entities=_proper_nouns(text),
                    )
                    result.entries.append(entry)
                    open_entries.append(entry)
            if _QUESTION_PATTERN.search(text):
                entry = LedgerEntry(
                    id=f"promise-{episode}-open_question",
                    kind="promise",
                    description=f"Episode {episode} raises an unanswered question.",
                    episodes=[episode],
                    excerpt_ids=[excerpt_id],
                    promise_kind="mystery",
                    entities=_proper_nouns(text),
                )
                result.entries.append(entry)
                open_entries.append(entry)

            # -- contradiction detection: does this episode resolve a --
            # -- pending negation from an earlier one? ------------------
            matched_index: int | None = None
            for index, pending in enumerate(pending_negations):
                if pending.episode == episode:
                    continue
                allowed = _SYNONYM_CLUSTERS.get(pending.capability_stem, {pending.capability_stem})
                text_stems = {_stem(word) for word in words}
                if not (allowed & text_stems):
                    continue
                if not (pending.words & words):
                    continue
                matched_index = index
                break
            if matched_index is not None:
                pending = pending_negations.pop(matched_index)
                earliest, latest = sorted((pending.episode, episode))
                entry = LedgerEntry(
                    id=f"contradiction-{earliest}-{latest}",
                    kind="contradiction",
                    description=(
                        f"Episode {latest} contradicts a negated claim from episode {earliest}."
                    ),
                    episodes=[earliest, latest],
                    excerpt_ids=sorted({pending.excerpt_id, excerpt_id}),
                    entities=_proper_nouns(pending.text + ' ' + text),
                )
                result.entries.append(entry)
                open_entries.append(entry)

            # -- negation detection: does this episode plant a new one? -
            capability_stem: str | None = None
            for pattern in _NEGATION_PATTERNS:
                match = pattern.search(text)
                if match:
                    capability_stem = _stem(match.group(1))
                    break
            if capability_stem is None and _DEAD_PATTERN.search(text):
                capability_stem = "dead"
            if capability_stem is not None:
                pending_negations.append(
                    _PendingNegation(episode, capability_stem, words, excerpt_id, text)
                )

            # -- payoff detection -----------------------------------------
            if _PAYOFF_PATTERN.search(text):
                for entry in reversed(open_entries):
                    if entry.id in resolved_target_ids:
                        continue
                    if entry.latest_episode >= episode:
                        continue
                    shared = set(entry.entities) & words
                    if not shared:
                        continue
                    result.payoffs.append(
                        PayoffLink(
                            node_id=node_id,
                            target_id=entry.id,
                            episode=episode,
                            rationale=(
                                f"Episode {episode} resolution language shares "
                                f"noun(s) {sorted(shared)} with entry {entry.id} "
                                f"from episode {entry.origin_episode}."
                            ),
                        )
                    )
                    resolved_target_ids.add(entry.id)
                    break

        return result

    @staticmethod
    def _validate(row: object) -> tuple[int, str, dict] | None:
        if not isinstance(row, dict):
            return None
        raw_episode = row.get("episode")
        try:
            episode = int(raw_episode)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        text = row.get("synopsis") or row.get("body") or ""
        if not isinstance(text, str) or not text.strip():
            return None
        return episode, text, row
