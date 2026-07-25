#!/usr/bin/env python3
"""Deterministic generator for the CanonPulse demo series, "The Last Monsoon".

Runs offline, once. No model calls. This script hand-authors:

  * a 220-episode arc skeleton (acts, turning points, character threads) with
    the defect manifest's plant/payoff episodes as fixed anchors,
  * full beat + excerpt text for every episode the manifest touches (35
    episodes) plus the 10 full-text pressure points the demo walks judges
    through,
  * templated (but non-repetitive) filler beats for the ~185 remaining
    background episodes.

It then emits `Series` JSON (nodes, entries, payoffs, excerpts) such that
`LedgerResolver` resolves every manifest item to its `expected_state`. See
`data/manifest/last_monsoon.yaml` for the ground truth this file is built to
satisfy -- that file is hand-authored and this script must never edit it.

Usage: uv run python scripts/generate_series.py
"""

from __future__ import annotations

import json
from pathlib import Path

TOTAL_EPISODES = 220
SERIES_ID = "last-monsoon"
REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "data" / "series" / "last_monsoon.json"

# ---------------------------------------------------------------------------
# Arc skeleton: acts, turning points, character threads.
#
# "The Last Monsoon" -- a Mumbai monsoon-season thriller. Nine years ago the
# ferry MV Konkan Rani went down in a storm. Asha Kulkarni, a podcast
# journalist whose father Vikram was aboard, is still pulling at the thread.
# The manifest's plant/payoff episodes are baked in as fixed turning points;
# everything else drapes around them.
# ---------------------------------------------------------------------------

ACTS = [
    (1, 55, "Act I -- The Tape", "Asha reopens the Konkan Rani file armed with her father's cassette."),
    (56, 133, "Act II -- The Ledger", "The dock corruption ring surfaces; Tara and Meera's tangled past resurfaces."),
    (134, 199, "Act III -- The Reveals", "The dive, the flashback, and the informant's identity all come undone."),
    (200, 220, "Act IV -- The Last Monsoon", "The cassette's voice and Asha's own account are finally tested."),
]

CHARACTERS = [
    "Asha", "Tara", "Meera", "Rafi", "Rao", "Zoya", "Salim", "Kabir's widow",
]

POV_ROTATION = ["Asha", "Tara", "Rao", "Rafi", "Zoya", "Meera"]

LOCATIONS = [
    "Sassoon Dock", "the Colaba archive", "Rao's precinct", "the harbor slum lanes",
    "the Fernandes family flat", "the drowned warehouse at Ferry Point",
    "the All-India Radio tower", "Crawford Market", "the Bandra sea wall",
    "the dock workers' union hall",
]

OBSTACLES = [
    "the file has been resealed",
    "a witness changes their story overnight",
    "the monsoon floods the only road out",
    "the union won't talk to outsiders",
    "the evidence has already been sold",
    "someone got there first",
    "the tape hisses out right where it matters",
    "the ledger page is missing",
]

TOPICS = [
    "who really owns the silence around the sinking",
    "whether the cassette should ever have aired",
    "what Rao knew before the retirement papers were signed",
    "whether Tara's memory of that night can be trusted",
    "who Zoya really answers to",
    "what the union paid to keep quiet",
]

# ---------------------------------------------------------------------------
# Hand-authored episodes: every episode the manifest anchors (35), plus the
# 10 full-text pressure points the demo reads on stage. Pressure points get
# long-form excerpts; the rest get short, precise excerpts that contain the
# exact contradiction or promise language the manifest note describes.
# ---------------------------------------------------------------------------

PRESSURE_POINTS = {1, 12, 47, 88, 134, 178, 199, 210, 218, 220}

SPECIAL_EPISODES: dict[int, dict[str, str]] = {}


def add(n: int, beat: str, excerpt: str, entities: list[str]) -> None:
    SPECIAL_EPISODES[n] = {"beat": beat, "excerpt": excerpt, "entities": entities}


# --- Ep 1 (pressure point) -- twist-05 anchor: the cassette is framed as
# Vikram's own voice, unedited. Ep 210 will contradict this. ---------------
add(
    1,
    "Asha opens her podcast with the cassette her father Vikram left behind before the "
    "Konkan Rani sailed into the storm nine years ago, and tells her listeners, on air, "
    "that the voice on the tape is unmistakably his.",
    "COLD OPEN. Tape hiss, then a man's voice, low and warm: 'Asha, beta, if you're playing "
    "this, it means I didn't make it back before the water came up.' Asha, over the hiss: "
    "'That's my father. Vikram Kulkarni. Nine years and I still know that voice the way I know "
    "my own name -- there's no editing booth in Bombay clever enough to fake the way he says "
    "my name. I've had it tested twice. Both times the answer came back the same: this is "
    "him, unaltered, unedited, the last thing he ever said to me before the Konkan Rani went "
    "down with a hundred and eleven souls on board and came back up with eighty-nine.' "
    "She sets the recorder down on the studio desk, the reel still turning. 'Everything I "
    "tell you this season, I tell you starting from that certainty. My father's voice, on my "
    "father's tape, saying my father's goodbye. Hold onto that, because before the last "
    "monsoon of this story breaks, you are going to want to doubt it. I'm asking you not to "
    "doubt it yet. I'm asking you to trust the tape the way I have trusted it for nine years, "
    "because everything else I am about to tell you about the Konkan Rani, about Inspector "
    "Rao, about the dock ledgers nobody was supposed to see, starts from this one certain "
    "thing: my father spoke these words to me, and no one else's voice could have said them.' "
    "The rain starts against the studio window, first of the season. She lets it play under "
    "the silence for four full seconds before she says: 'Episode one. Let's begin.'",
    ["Asha", "Vikram"],
)

# --- Ep 2 -- hole-04 first anchor: locket described as brass. -------------
add(
    2,
    "Asha finds her mother's locket in the drawer where the police returned Vikram's effects "
    "and turns it over in the lamplight, dull brass, before she can look at it too long.",
    "The clasp had gone stiff with rust. Asha worked it open with a thumbnail. 'Brass,' she "
    "said, mostly to herself, 'she always said it was brass, cheap, from the Crawford Market "
    "stall, and that's exactly why she never had it insured.' Inside, no photograph -- just a "
    "curl of her mother's hair, wound twice around the pin.",
    ["Asha"],
)

# --- Ep 3 -- twist-02 planted: Tara cannot swim. ---------------------------
add(
    3,
    "Tara helps Asha comb the survivor registry at the union hall and, when Asha jokes about "
    "the two of them jumping off the sea wall like they did as kids, Tara goes quiet and "
    "admits she never learned to swim.",
    "'I can't swim, Asha. I never learned. Not before the Rani, not after.' Tara said it flat, "
    "daring the subject to move on. 'You know that. Everyone on this stretch of coast knows "
    "that about me. It's practically the only thing people ask when they find out where I'm "
    "from.'",
    ["Tara", "Asha"],
)

# --- Ep 5 -- open-01 planted, urgency 5, overdue by Ep 220. ---------------
add(
    5,
    "Rao tells Asha, off the record, that if she can name one dock worker willing to swear "
    "the manifest was altered, he will personally reopen the Konkan Rani file within the "
    "week -- a promise he makes look easy and is anything but.",
    "Rao lowered his voice even though the canteen was empty. 'One name, Asha. One dock "
    "worker who'll sign a statement that the manifest was altered before the inquiry saw it, "
    "and I reopen the file myself, this week, no committee, no delay. That's the whole price.' "
    "He said it like a man who already regretted offering it.",
    ["Rao", "Asha"],
)

# --- Ep 12 (pressure point) -- hole-01 planted: ferry sank at dawn. -------
add(
    12,
    "In a long flashback interview, the sole surviving deckhand tells Asha the Konkan Rani "
    "went down at dawn, the sky already grey when the water came over the rail.",
    "The deckhand's hands shook around the chai glass Asha had bought him, and he would not "
    "look at the recorder. 'You want to know when. Everyone wants to know when, like the hour "
    "explains the how.' He turned toward the window as if the harbor itself might correct him. "
    "'It was dawn. I remember because I remember hating the light -- how ordinary it looked, "
    "grey and flat over Colaba, while the deck was going under. A proper storm should be black. "
    "This one had the nerve to happen at first light, like the sea wanted witnesses. The last "
    "thing I saw clearly before I went into the water was the sun trying to come up behind the "
    "smoke off the engine room, and I remember thinking, absurdly, that I'd be late for my "
    "shift change if I didn't hurry, because it was morning, it was actually morning, and I was "
    "drowning in it.' He set the glass down so hard the chai slopped over the rim. 'Write that "
    "down exactly. Dawn. Not night, not evening -- dawn. I have had nine years of people telling "
    "me it happened some other time, and I was there, and I am telling you it was dawn, the sky "
    "the color of a police uniform, and I will say that on any recorder you like until the day I "
    "die.' Asha thanked him and turned off the machine, already composing the headline in her "
    "head: a ferry that sank into morning. She did not yet know how much that single word -- "
    "dawn -- would cost the story later, when a second witness, just as certain, would place the "
    "whole disaster in the dark, and no one in the newsroom would ever manage to reconcile the "
    "two accounts, because nobody thought to try.",
    ["Asha"],
)

# --- Ep 22 -- twist-03 planted: flashback misreadable as present tense. ---
add(
    22,
    "Tara describes the night before the Konkan Rani sailed in present tense, unbroken, so "
    "that a first-time listener would place the scene now, this week, rather than in the "
    "monsoon of 2009 -- a slip Asha lets stand without correction.",
    "'It's raining the way it never rains here,' Tara says, eyes fixed on nothing. 'Papa is on "
    "the dock arguing with the loading clerk, and I am standing under the shed roof getting "
    "wet anyway because I want to hear what they're saying. Amma is calling us in. The horn "
    "sounds twice, which means they're ready to cast off.' No date, no 'that year,' no "
    "grammar to mark the distance. Asha does not interrupt to ask when.",
    ["Tara"],
)

# --- Ep 30 -- open-02 planted, urgency 4, overdue by Ep 220. --------------
add(
    30,
    "Rao vows that if Asha finds even one more witness to the manifest tampering inside a "
    "month, he will personally walk the new evidence past the commissioner himself.",
    "'One month, Asha. You bring me one more name inside a month, and I carry it to the "
    "commissioner's desk myself, no middleman, no delay.' Rao said it standing in the rain "
    "outside the precinct, as if saying it indoors would make it official and he wasn't ready "
    "for that yet.",
    ["Rao", "Asha"],
)

# --- Ep 34 -- hole-02 planted: Rafi's brother is Imran. -------------------
add(
    34,
    "Rafi introduces his younger brother Imran to Asha at the union hall, explaining that "
    "Imran was the one who loaded the Konkan Rani's cargo the morning it sailed.",
    "'This is my brother, Imran,' Rafi said, an arm around the younger man's shoulders. "
    "'Imran was on the loading crew that morning. If anyone knows what went into that hold "
    "and what didn't, it's Imran.'",
    ["Rafi"],
)

# --- Ep 40 -- clean-01 planted, paid Ep 55. -------------------------------
add(
    40,
    "Tara promises Asha she will introduce her to the harbor archivist who keeps the only "
    "surviving paper manifest, once the archivist is back from Ratnagiri.",
    "'Give it two weeks,' Tara said. 'The archivist is visiting her sister in Ratnagiri, but "
    "the day she's back, I'll take you to her myself. She trusts me, and she doesn't trust "
    "reporters, so you'll need me in the room.'",
    ["Tara", "Asha"],
)

# --- Ep 47 (pressure point) -- twist-01 planted (Asha's fire account) AND
# hole-03 planted (phone destroyed). Both live in this episode. -----------
add(
    47,
    "A fire tears through the Ferry Point warehouse where the salvaged cargo records were "
    "stored; Asha recounts, in vivid first person, watching the flames take the shelving "
    "apart from just feet away, and in the same chaos her phone is crushed under a falling "
    "drum, dead beyond recovery.",
    "Asha's voice on the recording is close to breaking, the kind of close that makes a "
    "producer keep the tape rolling instead of cutting for time. 'I was standing right there "
    "when it went up. Fifteen feet, maybe less, from the shelf with the cargo ledgers on it. "
    "I felt the heat on my face before I heard anyone shout. I watched the fire take the "
    "second shelf, the one with the manifests, and there was nothing I could do but stand "
    "there and watch nine years of paper go up in about ninety seconds. I will never forget "
    "the smell.' She pauses, and you can hear, underneath the pause, something that doesn't "
    "quite match the certainty of the rest of it -- a smallness, a held breath. Then, in the "
    "same segment, almost as an aside: 'And in the scramble to get everyone out, one of the "
    "drums came off a stacked pallet and landed square on my bag. Phone's gone. Screen "
    "shattered, housing bent, water in the mic port from the sprinkler system on top of "
    "everything. Dead. I had to borrow Tara's phone just to call the desk and tell them what "
    "happened.' She says it like a footnote to the real story, an inconvenience, not a clue. "
    "It will be five episodes before that phone, supposedly crushed beyond recovery on this "
    "exact night, turns up in her hand again with no one asking how, and it will be a hundred "
    "and seventy-one episodes before anyone asks how she could have watched the fire from "
    "fifteen feet away when, as it turns out, she was nowhere near the warehouse that night at "
    "all.",
    ["Asha"],
)

# --- Ep 52 -- hole-03 second anchor: phone used again, unexplained. -------
add(
    52,
    "Asha calls Rao from her own phone to arrange a meeting, five days after telling listeners "
    "the device was crushed beyond recovery in the warehouse fire, with no mention of a "
    "replacement or repair.",
    "'Rao, it's Asha, calling from my own number.' She rattled off an address for the meeting "
    "as though the phone in her hand were the same one, the same crushed housing, the same "
    "shattered screen, that she had described going dead in the fire five days before. No one "
    "on the call asked how it had come back.",
    ["Asha"],
)

# --- Ep 55 -- clean-01 payoff. --------------------------------------------
add(
    55,
    "Tara delivers on her promise and brings Asha to the harbor archivist, now back from "
    "Ratnagiri, who unlocks a filing cabinet of paper manifests no one has touched in years.",
    "'Two weeks, like I said,' Tara told Asha, nodding at the archivist unlocking the cabinet. "
    "'She's back from Ratnagiri, and she's agreed to let you look, because I asked her to.'",
    ["Tara", "Asha"],
)

# --- Ep 60 -- twist-02 second anchor: the dive. ----------------------------
add(
    60,
    "Despite swearing weeks ago that she cannot swim, Tara dives from the sea wall into the "
    "harbor at night to retrieve a dropped evidence bag, surfacing with it held above her "
    "head before anyone can stop her.",
    "She was over the rail before Rafi could grab her sleeve. Tara -- who had told Asha in no "
    "uncertain terms that she never learned to swim -- hit the water in a clean dive and came "
    "up twenty feet out with the evidence bag clamped in one fist, stroking back toward the "
    "ladder like she'd done it a hundred times.",
    ["Tara"],
)

# --- Ep 66 -- twist-04 planted: informant introduced. ---------------------
add(
    66,
    "A guarded dock informant calling herself Zoya starts feeding Asha details about the "
    "corruption ring, insisting on meeting only after dark and refusing to explain why she "
    "knows so much about Kabir Ansari's murder.",
    "'Call me Zoya,' the woman said, not offering a hand. 'I know things about what happened "
    "to Kabir that the file doesn't. I'm not going to tell you how I know. Not yet. Maybe not "
    "ever.'",
    ["Zoya"],
)

# --- Ep 71 -- open-03 planted, urgency 4, overdue by Ep 220. --------------
add(
    71,
    "Zoya promises Asha she will hand over her brother Kabir's private ledger the moment she "
    "is certain Asha won't take it straight to Rao.",
    "'The ledger exists. I have it. The day I'm sure you won't run straight to Rao with it -- "
    "that day, it's yours.' Zoya said it like a debt she intended to pay, on her own timeline, "
    "to no one else's schedule.",
    ["Zoya"],
)

# --- Ep 88 (pressure point) -- hole-01 second anchor: ferry sank at night. -
add(
    88,
    "A second survivor, tracked down through the harbor archivist's ledger, tells Asha the "
    "Konkan Rani went down at night, in total darkness, with no light on the water at all.",
    "The second survivor had never been interviewed before; Asha had found her name buried in "
    "a Ratnagiri hospital admission log, cross-referenced against the manifest by hand. She "
    "spoke slowly, the way people do when they've rehearsed a memory so many times alone that "
    "saying it out loud feels strange. 'It was night. Full dark, no moon, the kind of black "
    "where you can't tell the sky from the water except by which one is trying to kill you. "
    "I remember because I remember praying for morning and it not coming -- I kept thinking, "
    "if I can just hold on until it's light, someone will see us, and it never got light, not "
    "once, the whole time I was in the water. Hours, it felt like. All of it dark.' She wrapped "
    "both hands around her tea. 'People ask me sometimes if I remember it as dawn, like some "
    "of the survivors say, and I tell them no, absolutely not, there was no dawn anywhere near "
    "that night, I would have wept with relief to see even a grey sky and I never did, not "
    "until they pulled me out the next afternoon.' Asha sat very still, running the arithmetic "
    "in her head: one survivor certain of dawn, one survivor equally certain of a night with no "
    "light in it at all, both accounts recorded, dated, verified as genuine survivors of the "
    "same sinking, and neither one, in the seventy-six episodes since the first interview, "
    "reconciled with the other. She would carry both tapes back to the studio that evening and "
    "file them, unresolved, in the same folder, and there they would stay -- one voice saying "
    "dawn, one voice saying night, the Konkan Rani going down twice in the record, at two "
    "different hours, with no one, not Asha, not Rao, not the inquiry that closed the file "
    "years ago, ever asked to explain how both could be true.",
    ["Asha"],
)

# --- Ep 90 -- hole-04 second anchor: locket described as silver. ---------
add(
    90,
    "Asha shows the locket to a jeweler for an appraisal and is startled when the jeweler "
    "identifies it, without hesitation, as silver.",
    "The jeweler turned the locket under his lamp for all of four seconds. 'Silver,' he said, "
    "tapping it once with a fingernail for the ring of it. 'Old silver, worn thin at the edges, "
    "but silver, no question. You don't get that patina on brass.' Asha did not correct him.",
    ["Asha"],
)

# --- Ep 101 -- hole-02 second anchor: brother is Irfan. -------------------
add(
    101,
    "Rafi mentions his brother again while describing the loading crew roster, this time "
    "calling him Irfan, with no acknowledgment that the name has changed.",
    "'Irfan was on that crew for six years,' Rafi said, flipping through the roster. 'My "
    "brother knows that loading dock better than anyone alive.' He said Irfan the way he'd "
    "always said it, as if there had never been another name.",
    ["Rafi"],
)

# --- Ep 110 -- twist-05 planted (second beat): the cassette's authenticity
# is quietly questioned for the first time. --------------------------------
add(
    110,
    "A sound engineer Asha consults about the cassette's hiss pattern mentions, almost in "
    "passing, that a second-generation copy would carry a specific artifact -- the first hint, "
    "buried and unremarked, that the tape playing since Ep 1 may not be a direct original "
    "recording of Vikram's voice at all.",
    "'This hiss profile,' the engineer said, frowning at his monitor, 'this is consistent with "
    "a re-recording, not a first-generation tape. Whoever made this copied it off something "
    "else.' Asha filed the comment away without following it, the way you file away a "
    "stranger's remark that doesn't fit the story you've already decided to tell.",
    ["Asha"],
)

# --- Ep 120 -- clean-02 planted, paid Ep 133. -----------------------------
add(
    120,
    "Asha promises Rao she will hand over the full chain-of-custody log for the cargo "
    "ledgers within thirteen days, once her paperwork with the archive board clears.",
    "'Thirteen days, Rao. That's how long the archive board says the clearance takes, and the "
    "day it clears, the chain-of-custody log is yours, complete, nothing held back.'",
    ["Asha", "Rao"],
)

# --- Ep 133 -- clean-02 payoff. -------------------------------------------
add(
    133,
    "Exactly as promised, Asha delivers the full chain-of-custody log to Rao's desk, thirteen "
    "days after the archive board cleared it.",
    "Rao signed for the folder without looking up. 'Thirteen days,' he said. 'You kept your "
    "word.' Asha didn't answer; she just watched him initial the log, complete, nothing held "
    "back.",
    ["Asha", "Rao"],
)

# --- Ep 134 (pressure point) -- twist-02 payoff: the dive was Meera. ------
add(
    134,
    "Confronted with the harbor CCTV timestamp, Tara finally admits that the dive off the sea "
    "wall was never hers -- it was her estranged twin sister Meera, wearing Tara's jacket, "
    "while Tara stood twenty feet up the wall unable to move toward the water at all.",
    "Asha laid the printed CCTV frame on the table between them, the timestamp burned into the "
    "corner in white digits. 'Explain this to me, Tara. Because I have you on record saying "
    "you can't swim, and I have you diving off that wall in front of six witnesses.' Tara "
    "didn't touch the photograph. 'That's not me,' she said, finally, after a silence long "
    "enough that Asha almost filled it herself. 'That's Meera. My sister. My twin, if you want "
    "the ugly word for it, though we stopped using it years ago.' She pulled her sleeve down "
    "over her wrist, an old habit. 'She was in the city that week. Nobody knew, because nobody "
    "was supposed to know -- we haven't spoken in eight years, and she doesn't exactly announce "
    "herself. She borrowed my jacket off the back of a chair at the union hall because it was "
    "raining and hers was soaked through, and then that whole business with the evidence bag "
    "happened, and everyone assumed the woman in my jacket diving off my usual spot was me, "
    "because who else would it be?' Her hands were shaking slightly around her cup. 'I was "
    "twenty feet up the wall the entire time, Asha. I couldn't even watch. I have never been "
    "able to make myself go near open water since the Rani, and Meera is the only person alive "
    "who can dive like that without thinking twice, because she was the one who pulled three "
    "people out of the wreck with her own hands the night it happened, and I was the one who "
    "couldn't move.' Asha sat back, recalibrating six weeks of assumptions in real time. 'Why "
    "didn't you say something sooner?' 'Because the moment I say Meera was in the city,' Tara "
    "said, 'everyone starts asking why, and I am not ready for anyone to ask why yet.'",
    ["Tara", "Meera", "Asha"],
)

# --- Ep 140 -- hole-05 planted: Rao retires. ------------------------------
add(
    140,
    "Rao announces his retirement from the force at a small precinct gathering, citing thirty "
    "years of service and a promise to his wife that this monsoon would be his last on duty.",
    "'Thirty years,' Rao said, raising a paper cup of tea instead of anything stronger. 'I "
    "promised my wife this would be my last monsoon in uniform, and a man should keep at least "
    "one promise to his wife before he dies. I'm retiring, effective the end of the month.'",
    ["Rao"],
)

# --- Ep 160 -- hole-05 second anchor: Rao leads the raid. -----------------
add(
    160,
    "Rao personally leads the raid on the dock warehouse where the corruption ring's ledgers "
    "are hidden, issuing orders over the radio from the front of the strike team.",
    "'On my mark,' Rao's voice crackled over every radio on the team. 'I want the east door "
    "and the loading bay covered before anyone breathes. Move.' He went in first, service "
    "revolver drawn, exactly as he had a hundred times before in thirty years on the force.",
    ["Rao"],
)

# --- Ep 175 -- hole-06 planted: scar on the left arm. ---------------------
add(
    175,
    "Tara rolls up her left sleeve to show Asha the scar she got pulling survivors from the "
    "wreck the night of the sinking, a pale seam running from wrist to elbow.",
    "Tara pushed up her left sleeve without being asked. 'This is where the rebar caught me,' "
    "she said, tracing the scar from wrist to elbow. 'The night of the Rani. I don't show many "
    "people. My left arm's had this seam for nine years.'",
    ["Tara"],
)

# --- Ep 178 (pressure point) -- twist-03 payoff: flashback dated to 2009. -
add(
    178,
    "Reviewing old newspaper clippings with Asha, Tara finally dates the vivid present-tense "
    "memory she described back in Ep 22 -- the rain, her father on the dock, the horn sounding "
    "twice -- as the night before the Konkan Rani sailed in 2009, not anything happening now.",
    "Asha spread the brittle newspaper clippings across the table, dates inked faintly in the "
    "margins by whoever had clipped them years ago. 'Tara. That story you told me, months ago "
    "-- the rain, your father on the dock, the horn sounding twice. You told it like it was "
    "happening. Present tense, no date, no distance. I want to know when that actually was.' "
    "Tara went still over the clippings, one fingertip resting on a photograph of the dock in "
    "the rain. 'It's the night before the Rani sailed,' she said quietly. 'August, 2009. I "
    "tell it that way -- like it's happening now -- because in my head it never stopped "
    "happening. I've told that story to myself so many times, in the present tense, that I "
    "forgot to warn you it was a memory and not a report. It's fourteen years old, Asha. It "
    "happened in 2009, the night before everything, and I have never once told it any other "
    "way, not because I was hiding when it was, but because in my head there is no when. There "
    "is only the rain, and Papa on the dock, and the horn.' She finally looked up. 'I'm sorry. "
    "I should have said the year. I should have said 2009 the first time I told you, and I "
    "didn't, and I understand now why that might have confused things you were trying to keep "
    "straight.' Asha wrote the date in the margin of her own notes, next to the transcript from "
    "months back, closing a gap she hadn't fully registered as open until this moment: not a "
    "lie, not a contradiction in the ordinary sense, just a memory spoken as if it were "
    "unfolding live, dated, at last, to the night before the storm that started everything.",
    ["Tara", "Asha"],
)

# --- Ep 180 -- clean-03 planted, paid Ep 195. -----------------------------
add(
    180,
    "Zoya promises Asha she will finally explain her connection to Kabir once the monsoon "
    "session of the harbor tribunal closes, fifteen days out.",
    "'After the tribunal session closes,' Zoya said, checking the calendar pinned above her "
    "desk. 'Fifteen days. Then I'll tell you everything about my connection to Kabir, all of "
    "it, no more half-answers.'",
    ["Zoya"],
)

# --- Ep 190 -- hole-06 second anchor: scar on the right arm. -------------
add(
    190,
    "Tara rolls up her right sleeve this time to show the same rebar scar to Rao, tracing an "
    "identical seam from wrist to elbow that she had shown Asha weeks earlier on her left arm.",
    "'Rebar caught me right here,' Tara told Rao, pushing up her right sleeve and tracing a "
    "pale seam from wrist to elbow. 'The night of the Rani. Right arm's had this scar for nine "
    "years.' Rao nodded, taking her at her word, the same seam somehow migrated from the arm "
    "she had shown Asha only fifteen episodes before.",
    ["Tara", "Rao"],
)

# --- Ep 195 -- clean-03 payoff. -------------------------------------------
add(
    195,
    "As promised, the day the tribunal session closes, Zoya sits Asha down and finally "
    "explains her connection to Kabir in full.",
    "'Tribunal's closed,' Zoya said, setting two cups of tea on the table between them. "
    "'Fifteen days, like I told you. Now I'll tell you everything.'",
    ["Zoya", "Asha"],
)

# --- Ep 199 (pressure point) -- twist-04 payoff: Zoya is Kabir's sister. -
add(
    199,
    "Zoya finally reveals that she has been Kabir Ansari's sister all along -- the informant "
    "and the victim's family were the same person from the very first meeting in Ep 66.",
    "Zoya set her tea down without drinking it. 'You've been asking for eight months how I "
    "know so much about what happened to Kabir Ansari,' she said. 'I know because he was my "
    "brother. Zoya Ansari. I never lied to you about my name, I just never gave you the second "
    "half of it.' Asha's pen stopped moving. 'You let me build a whole informant profile "
    "around you being an outside source close to the ring. You let Rao's team vet you as an "
    "independent tip.' 'I let you assume,' Zoya said. 'I never once said I wasn't family. I "
    "just never corrected the assumption, because the moment anyone knew I was Kabir's sister, "
    "every door I'd spent a year prying open would have slammed shut -- his killers would have "
    "known exactly why I was asking questions, and I would have been the second Ansari in a "
    "grave instead of the first. So I called myself an informant, because that's what I "
    "became, in every practical sense, the day I decided to find out who did this to him. I "
    "just happened to also be his sister. Both things were true the entire time. You only ever "
    "asked me the first question.' Asha sat back, running the whole eight months backward "
    "through this single new fact -- every guarded meeting after dark, every refusal to explain "
    "her sources, every flinch whenever Kabir's name came up -- suddenly legible as grief "
    "rather than mere caution. 'Why tell me now?' 'Because the tribunal's closed, the ledger's "
    "handed over, and there's nothing left for anyone to take from me if the ring finds out. "
    "I've been an informant and a sister this whole time, Asha. I'm just done being only one "
    "of those things out loud.'",
    ["Zoya"],
)

# --- Ep 205 -- open-04 planted, urgency 3, healthy at Ep 220. ------------
add(
    205,
    "The new harbor tribunal clerk promises Asha access to the sealed 2009 inquiry annex, "
    "provided Asha files a formal request through the proper channel first.",
    "'File the request through the registrar,' the clerk said, not unkindly, 'and the sealed "
    "annex from the 2009 inquiry is yours to read. These things take time, but it will come "
    "through.'",
    ["Asha"],
)

# --- Ep 210 (pressure point) -- twist-05 payoff: the cassette's voice is
# not Vikram's. Contradicts the Ep 1 framing directly. ---------------------
add(
    210,
    "The sound engineer's lab confirms what Ep 110 only hinted at: the voice on Asha's "
    "cassette is not a first-generation recording of her father at all, but a copy of a voice "
    "actor -- Salim, a radio impersonator paid by the ring -- brought in to record a farewell "
    "that would keep Asha from digging for years.",
    "The engineer slid the spectrogram across the desk without preamble. 'I told you months "
    "ago this hiss profile looked like a re-recording. Now I can tell you why. This voiceprint "
    "doesn't match any surviving sample of your father's voice from before 2009 -- not the "
    "radio interview, not the wedding video, none of it. It matches a man named Salim "
    "Qureshi, a radio drama voice actor who did commercial work for a shipping concern with "
    "ties to the same dock ledger you've been chasing all year.' Asha didn't move. 'You're "
    "telling me the tape I have been playing on air since episode one, the tape I told half a "
    "million listeners was my father's unaltered voice, was performed. By an actor. Paid by "
    "the same ring that sank the Rani.' 'I'm telling you the science says so, yes. Someone "
    "wanted you to have a version of your father's goodbye that would make you stop asking "
    "questions -- not start them. They wrote you a very good ending, and it worked for nine "
    "years.' She sat with that for a long moment, the studio recorder running the whole time, "
    "because some habits don't break even at the exact instant your certainty does. 'Episode "
    "one,' she finally said into the microphone, quietly, more to herself than to any listener, "
    "'I told you there was no editing booth in Bombay clever enough to fake the way my father "
    "said my name. I was wrong. There was. I just hadn't found it yet.' The tape that had "
    "opened this whole story, the one thing she'd asked her audience to trust without doubt "
    "until the story caught up to it, turned out to be the story's first and best-hidden lie.",
    ["Asha", "Salim"],
)

# --- Ep 212 -- open-05 planted, urgency 4, healthy at Ep 220. ------------
add(
    212,
    "Rao promises Asha that once the ring's remaining financiers are named in the tribunal "
    "filing, he will personally see that the reopened Konkan Rani case gets a public inquest "
    "date within the year.",
    "'Once the financiers are named in the filing,' Rao said, 'I will see to it personally "
    "that the Rani case gets a public inquest date, and I'll see it happens within the year. "
    "That much I can still promise you, even out of uniform.'",
    ["Rao"],
)

# --- Ep 218 (pressure point) -- twist-01 payoff: Asha was not at the fire.
# Also open-06 planted, urgency 5, healthy at Ep 220. -----------------------
add(
    218,
    "Under gentle questioning from Tara, Asha finally admits she was never at the Ferry Point "
    "warehouse fire in Ep 47 at all -- she was at the hospital that night with her mother, and "
    "built her vivid account of the flames from Tara's own retelling, told so many times it "
    "became indistinguishable, even to her, from memory. In the same conversation, Rafi's "
    "younger cousin asks Asha to keep his name out of the final report until the tribunal "
    "ruling is public, a promise she makes with two episodes left to keep it.",
    "Tara wasn't accusing, just quiet, the way she got when she already knew the answer. "
    "'Asha. The fire. You've told that story on air I don't know how many times -- fifteen "
    "feet from the shelf, watching the flames take the ledgers apart. I was there. You "
    "weren't.' Asha set down her pen. 'I was at the hospital with my mother that night. Her "
    "blood pressure had spiked, and I couldn't leave her. You called me from the warehouse, "
    "and you told me everything, in so much detail, so many times over the weeks after, that "
    "somewhere along the way I stopped remembering it as your account and started remembering "
    "it as mine. I've been telling half a million listeners I watched that fire firsthand. I "
    "didn't. I built it out of your voice, until your voice became indistinguishable from a "
    "memory of my own that never actually happened.' Tara didn't look surprised, only tired. "
    "'I wondered, eventually. The details were too clean. Real memory has gaps you can't paper "
    "over. Yours never did.' In the same visit, Rafi's younger cousin -- barely out of his "
    "teens, terrified of the ring's reach even now -- caught Asha in the corridor after. 'Please. "
    "Keep my name out of the final report. Just until the tribunal ruling is public. Two more "
    "episodes, that's all I'm asking, and then it won't matter what anyone knows about my part "
    "in this.' Asha promised him she would, meaning it, aware even as she said it how many "
    "promises this story had already collected, and how little time remained to keep the ones "
    "still open.",
    ["Asha", "Tara"],
)

# --- Ep 220 (pressure point) -- finale. -----------------------------------
add(
    220,
    "The tribunal ruling goes public, the ring's financiers are named, and Asha closes the "
    "season with the two lies she now knows the story was built on -- the cassette's borrowed "
    "voice and her own borrowed memory of the fire -- laid out plainly for her listeners, "
    "alongside everything that still, honestly, remains unresolved.",
    "'Two years ago I told you this season would start from one certainty: my father's voice, "
    "on my father's tape, saying my father's goodbye. I was wrong about that, and I told you "
    "so, back in episode two hundred and ten. Today the tribunal ruling went public. The "
    "financiers behind the ring that sank the Konkan Rani and killed Kabir Ansari have names "
    "now, on paper, in a court record that can't be resealed the way the original inquiry was. "
    "Rao, who should be enjoying his retirement, tells me the public inquest date is coming "
    "within the year, and I believe him, because he has kept every promise he's made me so "
    "far, on a timeline he chose himself.' She let the rain sound under the words for a beat, "
    "the season's last monsoon finally slackening outside the studio window. 'I owe you one "
    "more correction before I let you go. The warehouse fire, episode forty-seven -- I told it "
    "like I was standing fifteen feet from the flames. I wasn't there. I was at a hospital "
    "with my mother, and I built that memory out of someone else's voice until I couldn't tell "
    "the difference anymore. I'm telling you that now because a story that starts with a false "
    "certainty and never corrects it isn't journalism, it's just a better-produced silence. "
    "Some of what I promised you this season isn't finished. There's still a name from a dock "
    "worker I owe Rao from episode five, still owed, past due, and I haven't found it. There's "
    "a young man whose name I'm still keeping out of this report, as promised two episodes "
    "ago, because the promise isn't due yet. Not everything closes on the season finale. That's "
    "not a flaw in the story. That's the last true thing I can tell you about how long the "
    "water off this coast takes to give anything back.'",
    ["Asha", "Rao"],
)

# ---------------------------------------------------------------------------
# Filler episode generation: deterministic, template-driven, non-repetitive
# enough to read as background rather than noise. These carry no manifest
# weight -- they exist so the series has 220 coherent episodes end to end.
# ---------------------------------------------------------------------------

BEAT_TEMPLATES = [
    "{pov} follows a lead near {location}, but {obstacle}.",
    "{pov} and {other} clash over {topic}; neither one gives ground.",
    "{pov} spends the episode at {location}, turning over {topic} without resolving it.",
    "A quiet stretch: {pov} reflects on {topic} while the monsoon batters {location}.",
    "{pov} corners a reluctant source at {location}, only to find {obstacle}.",
    "{other} warns {pov} away from {topic}, which only makes {pov} dig further.",
]

EXCERPT_TEMPLATES = [
    "\"{topic_cap}? I've stopped pretending that one has an easy answer,\" {pov} said, "
    "looking out at {location} through the rain.",
    "\"{obstacle_cap},\" {other} said flatly. \"You want to keep going anyway?\" {pov} did "
    "not answer right away.",
    "The rain hadn't let up over {location} in three days. {pov} stood in it anyway, thinking "
    "about {topic}.",
    "\"You're going to get yourself in trouble over {topic},\" {other} said. {pov} just kept "
    "walking toward {location}.",
    "At {location}, the conversation kept circling back to {topic}, and {pov} let it, because "
    "{obstacle} and there was nothing else to do but wait it out.",
]


def _cap(text: str) -> str:
    return text[0].upper() + text[1:] if text else text


def generate_filler(episode: int) -> dict[str, object]:
    """Deterministic filler beat/excerpt for a background episode.

    Indices are derived from the episode number so the same series is
    produced every run, but neighbouring episodes rarely land on the same
    template/location/topic combination.
    """
    pov = POV_ROTATION[episode % len(POV_ROTATION)]
    other_candidates = [c for c in POV_ROTATION if c != pov]
    other = other_candidates[episode % len(other_candidates)]
    location = LOCATIONS[(episode * 3) % len(LOCATIONS)]
    obstacle = OBSTACLES[(episode * 5) % len(OBSTACLES)]
    topic = TOPICS[(episode * 7) % len(TOPICS)]

    beat_template = BEAT_TEMPLATES[episode % len(BEAT_TEMPLATES)]
    excerpt_template = EXCERPT_TEMPLATES[(episode // 2) % len(EXCERPT_TEMPLATES)]

    beat = beat_template.format(pov=pov, other=other, location=location, obstacle=obstacle, topic=topic)
    excerpt = excerpt_template.format(
        pov=pov,
        other=other,
        location=location,
        obstacle=_cap(obstacle),
        topic=topic,
        topic_cap=_cap(topic),
        obstacle_cap=_cap(obstacle),
    )
    return {"beat": beat, "excerpt": excerpt, "entities": [pov, other]}


def act_for(episode: int) -> str:
    for start, end, name, _ in ACTS:
        if start <= episode <= end:
            return name
    return ACTS[-1][2]


# ---------------------------------------------------------------------------
# Assembly.
# ---------------------------------------------------------------------------


def build_episode_content() -> dict[int, dict[str, object]]:
    content: dict[int, dict[str, object]] = {}
    for episode in range(1, TOTAL_EPISODES + 1):
        if episode in SPECIAL_EPISODES:
            content[episode] = SPECIAL_EPISODES[episode]
        else:
            content[episode] = generate_filler(episode)
    return content


def build_nodes(content: dict[int, dict[str, object]]) -> list[dict[str, object]]:
    nodes = []
    for episode in range(1, TOTAL_EPISODES + 1):
        data = content[episode]
        node: dict[str, object] = {
            "id": f"ep-{episode:03d}",
            "episode": episode,
            "perceived_index": episode,
            "summary": data["beat"],
            "entities": data["entities"],
            "valence": 0.0,
            "excerpt_id": f"ex-{episode:03d}",
        }
        # Flavor the dual-layer divergence for the two episodes that are
        # explicitly about time displacement -- not required for ledger
        # resolution, but true to the "G_true vs G_perceived" premise.
        if episode == 22:
            node["true_time"] = 0.05  # the flashback night, chronologically early
        if episode == 178:
            node["true_time"] = 0.05  # the dating of that same flashback
        nodes.append(node)
    return nodes


def build_excerpts(content: dict[int, dict[str, object]]) -> list[dict[str, object]]:
    return [
        {"id": f"ex-{episode:03d}", "episode": episode, "text": content[episode]["excerpt"]}
        for episode in range(1, TOTAL_EPISODES + 1)
    ]


def build_entries_and_payoffs() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    entries: list[dict[str, object]] = []
    payoffs: list[dict[str, object]] = []

    def excerpt_ids(*episodes: int) -> list[str]:
        return [f"ex-{ep:03d}" for ep in episodes]

    # --- 6 accidental holes: contradiction, no payoff. ---
    entries.append({
        "id": "hole-01", "kind": "contradiction",
        "description": "The Konkan Rani sank at dawn (Ep 12) and at night (Ep 88); never reconciled.",
        "episodes": [12, 88], "excerpt_ids": excerpt_ids(12, 88),
        "urgency": 3, "entities": ["Asha"],
    })
    entries.append({
        "id": "hole-02", "kind": "contradiction",
        "description": "Rafi's brother is named Imran in Ep 34 and Irfan in Ep 101.",
        "episodes": [34, 101], "excerpt_ids": excerpt_ids(34, 101),
        "urgency": 2, "entities": ["Rafi"],
    })
    entries.append({
        "id": "hole-03", "kind": "contradiction",
        "description": "Asha's phone is destroyed beyond recovery in Ep 47, then used without explanation in Ep 52.",
        "episodes": [47, 52], "excerpt_ids": excerpt_ids(47, 52),
        "urgency": 3, "entities": ["Asha"],
    })
    entries.append({
        "id": "hole-04", "kind": "contradiction",
        "description": "The locket is described as brass in Ep 2 and identified as silver in Ep 90.",
        "episodes": [2, 90], "excerpt_ids": excerpt_ids(2, 90),
        "urgency": 2, "entities": ["Asha"],
    })
    entries.append({
        "id": "hole-05", "kind": "contradiction",
        "description": "Inspector Rao retires from the force in Ep 140 but personally leads the raid in Ep 160.",
        "episodes": [140, 160], "excerpt_ids": excerpt_ids(140, 160),
        "urgency": 3, "entities": ["Rao"],
    })
    entries.append({
        "id": "hole-06", "kind": "contradiction",
        "description": "Tara's rebar scar is on her left arm in Ep 175 and her right arm in Ep 190.",
        "episodes": [175, 190], "excerpt_ids": excerpt_ids(175, 190),
        "urgency": 2, "entities": ["Tara"],
    })

    # --- 5 intentional twists: contradiction, payoff downstream. ---
    entries.append({
        "id": "twist-01", "kind": "contradiction",
        "description": "Asha's vivid firsthand account of the Ep 47 warehouse fire is later revealed (Ep 218) to be built from Tara's retelling -- she was never there.",
        "episodes": [47], "excerpt_ids": excerpt_ids(47),
        "urgency": 3, "entities": ["Asha"],
    })
    payoffs.append({
        "node_id": "ep-218", "target_id": "twist-01", "episode": 218,
        "rationale": "Asha admits under questioning from Tara that she was at the hospital with her mother during the Ep 47 fire, not at the warehouse.",
    })

    entries.append({
        "id": "twist-02", "kind": "contradiction",
        "description": "Tara says she cannot swim in Ep 3, yet dives off the sea wall in Ep 60; Ep 134 reveals the diver was her estranged twin Meera.",
        "episodes": [3, 60], "excerpt_ids": excerpt_ids(3, 60),
        "urgency": 3, "entities": ["Tara", "Meera"],
    })
    payoffs.append({
        "node_id": "ep-134", "target_id": "twist-02", "episode": 134,
        "rationale": "Tara admits the Ep 60 dive was her twin sister Meera, wearing Tara's jacket, not Tara herself.",
    })

    entries.append({
        "id": "twist-03", "kind": "contradiction",
        "description": "Tara narrates the night before the Konkan Rani sailed in present tense in Ep 22, misreadable as happening now; Ep 178 dates it to 2009.",
        "episodes": [22], "excerpt_ids": excerpt_ids(22),
        "urgency": 2, "entities": ["Tara"],
    })
    payoffs.append({
        "node_id": "ep-178", "target_id": "twist-03", "episode": 178,
        "rationale": "Tara explicitly dates the Ep 22 flashback to August 2009, the night before the Konkan Rani sailed.",
    })

    entries.append({
        "id": "twist-04", "kind": "contradiction",
        "description": "The dock informant Zoya, introduced in Ep 66, is revealed in Ep 199 to be Kabir Ansari's sister -- informant and victim's family are one person.",
        "episodes": [66], "excerpt_ids": excerpt_ids(66),
        "urgency": 3, "entities": ["Zoya"],
    })
    payoffs.append({
        "node_id": "ep-199", "target_id": "twist-04", "episode": 199,
        "rationale": "Zoya reveals her full name, Zoya Ansari, and that she is Kabir Ansari's sister.",
    })

    entries.append({
        "id": "twist-05", "kind": "contradiction",
        "description": "Ep 1 frames the cassette voice as unmistakably Vikram's; Ep 110 hints at a re-recording artifact; Ep 210 confirms the voice belongs to a hired actor, not Vikram.",
        "episodes": [1, 110], "excerpt_ids": excerpt_ids(1, 110),
        "urgency": 4, "entities": ["Asha", "Salim"],
    })
    payoffs.append({
        "node_id": "ep-210", "target_id": "twist-05", "episode": 210,
        "rationale": "Voiceprint analysis confirms the cassette is a performance by voice actor Salim Qureshi, not a recording of Vikram.",
    })

    # --- 6 outstanding obligations: planted, unpaid at Ep 220. urgency set
    # per manifest notes so exactly three read overdue and three healthy. ---
    entries.append({
        "id": "open-01", "kind": "promise",
        "description": "Rao promises to reopen the Konkan Rani file within a week of Asha naming one dock worker willing to swear the manifest was altered.",
        "episodes": [5], "excerpt_ids": excerpt_ids(5),
        "urgency": 5, "promise_kind": "causal", "entities": ["Rao", "Asha"],
    })
    entries.append({
        "id": "open-02", "kind": "promise",
        "description": "Rao vows to walk any new manifest-tampering witness past the commissioner within a month.",
        "episodes": [30], "excerpt_ids": excerpt_ids(30),
        "urgency": 4, "promise_kind": "causal", "entities": ["Rao", "Asha"],
    })
    entries.append({
        "id": "open-03", "kind": "promise",
        "description": "Zoya promises to hand over Kabir's private ledger once she trusts Asha won't take it straight to Rao.",
        "episodes": [71], "excerpt_ids": excerpt_ids(71),
        "urgency": 4, "promise_kind": "mystery", "entities": ["Zoya"],
    })
    entries.append({
        "id": "open-04", "kind": "promise",
        "description": "The tribunal clerk promises Asha access to the sealed 2009 inquiry annex once she files a formal request.",
        "episodes": [205], "excerpt_ids": excerpt_ids(205),
        "urgency": 3, "promise_kind": "mystery", "entities": ["Asha"],
    })
    entries.append({
        "id": "open-05", "kind": "promise",
        "description": "Rao promises a public inquest date within the year once the ring's remaining financiers are named.",
        "episodes": [212], "excerpt_ids": excerpt_ids(212),
        "urgency": 4, "promise_kind": "causal", "entities": ["Rao"],
    })
    entries.append({
        "id": "open-06", "kind": "promise",
        "description": "Asha promises Rafi's cousin to keep his name out of the final report until the tribunal ruling is public.",
        "episodes": [218], "excerpt_ids": excerpt_ids(218),
        "urgency": 5, "promise_kind": "relationship", "entities": ["Asha", "Rafi"],
    })

    # --- 3 clean controls: ordinary plant and payoff. Must not be flagged. ---
    entries.append({
        "id": "clean-01", "kind": "promise",
        "description": "Tara promises to introduce Asha to the harbor archivist once the archivist is back from Ratnagiri.",
        "episodes": [40], "excerpt_ids": excerpt_ids(40),
        "urgency": 2, "promise_kind": "relationship", "entities": ["Tara", "Asha"],
    })
    payoffs.append({
        "node_id": "ep-055", "target_id": "clean-01", "episode": 55,
        "rationale": "Tara brings Asha to the harbor archivist as promised.",
    })

    entries.append({
        "id": "clean-02", "kind": "promise",
        "description": "Asha promises Rao the full chain-of-custody log within thirteen days.",
        "episodes": [120], "excerpt_ids": excerpt_ids(120),
        "urgency": 3, "promise_kind": "causal", "entities": ["Asha", "Rao"],
    })
    payoffs.append({
        "node_id": "ep-133", "target_id": "clean-02", "episode": 133,
        "rationale": "Asha delivers the chain-of-custody log to Rao exactly thirteen days later.",
    })

    entries.append({
        "id": "clean-03", "kind": "promise",
        "description": "Zoya promises to explain her connection to Kabir once the tribunal session closes.",
        "episodes": [180], "excerpt_ids": excerpt_ids(180),
        "urgency": 3, "promise_kind": "relationship", "entities": ["Zoya"],
    })
    payoffs.append({
        "node_id": "ep-195", "target_id": "clean-03", "episode": 195,
        "rationale": "Zoya explains her connection to Kabir once the tribunal session closes, as promised.",
    })

    return entries, payoffs


def build_series() -> dict[object, object]:
    content = build_episode_content()
    nodes = build_nodes(content)
    excerpts = build_excerpts(content)
    entries, payoffs = build_entries_and_payoffs()

    return {
        "id": SERIES_ID,
        "title": "The Last Monsoon",
        "genre": "Mumbai monsoon thriller",
        "total_episodes": TOTAL_EPISODES,
        "ongoing": False,
        "nodes": nodes,
        "entries": entries,
        "payoffs": payoffs,
        "excerpts": excerpts,
    }


def main() -> None:
    series = build_series()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(series, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(f"Wrote {OUTPUT_PATH} ({TOTAL_EPISODES} episodes, "
          f"{len(series['entries'])} entries, {len(series['payoffs'])} payoffs, "
          f"{len(series['excerpts'])} excerpts)")


if __name__ == "__main__":
    main()
