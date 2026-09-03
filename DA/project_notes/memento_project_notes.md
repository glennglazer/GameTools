# Reverse Engineering Dragon Age: The Veilguard's Memento Power System

*A case study in learning an unfamiliar domain from zero, working
collaboratively with Claude, an AI assistant, to extract authoritative
game data for a wiki project.*

## The goal

Dragon Age: The Veilguard has a wiki page listing every collectible
"Memento," small lore objects scattered through the game that boost the
Caretaker's power (used to upgrade a crafting workshop). The wiki table had
a Power column, but it was incomplete and, as it turned out, sometimes
wrong, populated by whatever individual editors had happened to observe or
guess in the game. The goal of this project was to replace guesswork with
ground truth by mining the actual game files, then merge that data back
into the wiki.

The two parties in this project were Glenn (a software engineer, the wiki
editor driving the project) and Claude (an AI assistant). Neither started
with any domain knowledge of the Frostbite engine, its asset formats, or
game file reverse engineering in general. Everything below was worked out
from first principles, one clue at a time.

## Phase 1: The first files are unreadable

The project started with two small files (`loot_mementos_enableaftercaretaker.ebx`
and `loot_appearances_secretappearances.ebx`) pulled from a dump tool found
via a modding forum link. `file` identified them only as generic
little endian RIFF containers, not useful on its own.

A hex dump showed a repeating structure: `RIFF`, `EBX\0`, `EBXD`, a GUID,
more GUIDs, and one readable string, the asset's own internal path (for
example `RPG/Loot/Mementos/Loot_Mementos_EnableAfterCaretaker`). This was
recognizable as **Frostbite's EBX format**, DICE's engine's binary asset
format, used across Frostbite titles (Battlefield, Anthem, Mass Effect:
Andromeda, and now Veilguard).

**What we learned here:** EBX is driven entirely by an external schema.
The byte layout of any given field depends on a type descriptor that lives
outside the file, in a shared schema table across the whole game. Without
that schema, an EBX file is just an opaque blob of GUIDs and offsets, no
amount of staring at the hex dump would recover a "power" value directly.
The right tool for this job is something like **Frosty Editor/Toolsuite**,
which resolves those schemas and can decompile EBX into readable form.

**What didn't work:** trying to eyeball binary GUIDs for meaning. This was
a dead end that taught us to stop guessing and go get the right tool
instead.

## Phase 2: The pivot to XML

Glenn found and followed community modding instructions, ran a Frostbite
dump/decompile tool, and exported the entire game's EBX data to XML, about
15GB. This was the turning point: XML, unlike raw EBX, carries the schema
resolved structure directly, including field names.

From a `FactionCurios` directory, a sample file (`COL_Smith_Fac_AC_TorrentiMask.xml`,
the "Mask of Torrenti" memento) revealed the structural pattern that would
turn out to unlock everything:

```
<SelectionInfo>[Ebx] RPG/Loot/XPProgression/Smith/SmithXP_Hierarchy [c40c68a8-...]</SelectionInfo>
```

This pointed at a `SmithXP_Hierarchy` asset, which in turn pointed at a
`SmithXP_Switch` asset, which Glenn described to Claude as "the XML
equivalent of a switch statement," correctly, as it turned out. The switch
had several `Child` leaf nodes, each holding an actual
`<XP>0x...</XP>` hex value. The catch: the hierarchy chain didn't reveal
which leaf a given item selects.

## Phase 3: Cracking the selection mechanism

This was the core reverse engineering breakthrough of the whole project.
Given the curio file, the hierarchy file, the switch file, and one known
leaf file, the question was: what actually picks a row out of the switch?

The answer was hiding in a completely different part of the curio file,
not the `SelectionInfo` field the hierarchy came from, but a sibling
field:

```
<LootTags> to <EntityTagList> to <EntityTag><Hash>0xdd3bc1ce</Hash>
```

And each row in `SmithXP_Switch.xml` carried its own tag, via a
`BoolProvider_HierarchySelectionTags` block, with a matching `Hash`. **The
switch selects by comparing the entity's own loot tag hash against each
row's condition tag, not by anything in the hierarchy chain at all.** The
hierarchy is just a pointer to which switch table applies; the tag on the
object itself is the actual selector.

Once this was traced from end to end for one item (Mask of Torrenti to tag
`0xdd3bc1ce` to switch row 1 to `SmithXP_Leaf_Grant_Standard` to
`XP = 0x32` = 50), the whole mechanism was provably solved and, critically,
**scriptable**, no more manual per item tracing needed.

## Phase 4: Scaling up, from one file to hundreds

With the mechanism understood, the next step was automation. A Python
resolver was built to:
1. Parse every curio file's `LootTags` hash
2. Parse `SmithXP_Switch.xml` into a hash to child leaf lookup table
3. Parse every `SmithXP_Leaf_Grant_*.xml` file's XP value
4. Chain the three together per curio file

Applied to all 40 `FactionCurios`, every single one resolved to the same
tag (`0xdd3bc1ce`, 50 XP), a real, if initially suspicious looking,
finding: it wasn't a bug, it just meant faction curios don't vary in
power, contrary to the wiki's assumption (which had at that point been set
to a mix of 50, 200, and 300 by earlier editors' guesswork).

**What broke along the way, and what it taught us:**
- The initial leaf XP parser accidentally grabbed the file's own GUID
  instead of the asset's GUID (two different `Guid=` attributes in the
  same file), a reminder to verify assumptions about "the first match"
  in loosely structured text rather than trust it blindly.
- A second batch (`RegionalTrinkets`) exposed a schema inconsistency
  between export batches: faction curios used a lowercase `<n>` tag for
  the internal name field, while regional trinkets used `<Name>`
  (capitalized). A regex that only checked for `<n>` silently returned
  blank names for 98 files instead of erroring, a good example of how a
  parser can fail silently and convincingly. Caught by Glenn asking "why
  is this column always blank?" rather than Claude noticing it unprompted.

## Phase 5: The Regional Trinkets reveal variation

Unlike the uniform Faction Curios, the 98 Regional Trinkets showed real
distribution across tags: 87 Standard (50), 9 Larger (100), 1 Large (200),
1 ExtraLarge (300). The two outliers were `COL_Smith_Special_MythalDragon`
and `COL_Smith_Special_RevenantDragon`, which Glenn (drawing on actual
gameplay knowledge) identified as not physical mementos at all, but plot
triggered Caretaker Power boosts that reuse the same underlying grant
mechanism for narrative beats rather than item pickups. This was an
important piece of domain knowledge the files alone couldn't reveal, the
switch mechanism is agnostic to why it fires, only that it fires.

The 9 Larger tier items turned out to be masks of the Evanuris (elven
gods) plus Fen'Harel, initially unmatched to any wiki title because the
naive assumption ("Mask" in the filename means an existing wiki title with
"Mask" in it) was wrong. That gap got closed in Phase 7.

## Phase 6: Where automation hits its ceiling

At this point the project shifted from extracting data to attaching the
right label to each data point, matching cryptic internal filenames
(`Barrel`, `Badge`, `Letter1`, `Painting1` through `Painting5`, `ToySword`,
`OpenBook`) to real wiki codex titles. This is where the limits of pure
file analysis became clear:

- The XML files carry no embedded display text or description, confirmed
  by inspecting several ambiguous pairs (`ToySword` versus `ToyHessarian`,
  `Book` versus `OpenBook`) identical byte for byte in structure aside
  from the filename.
- A naive fuzzy matching script (token overlap plus string similarity
  against wiki titles) got roughly 40 percent of items right with real
  confidence, but produced dangerous false positives elsewhere. For
  example, it tried to match every Evanuris mask to unrelated existing
  wiki rows that happened to contain the word "Mask," and it created
  outright collisions where two different files scored highest against
  the same single wiki title.

**The right call here was to stop and ask** rather than force a guess, a
deliberate discipline that ran through the whole matching phase: present
high confidence matches, but surface duplicate collisions and zero
confidence groups explicitly for Glenn to resolve using his own gameplay
knowledge, rather than silently picking the top scoring (but possibly
wrong) candidate.

## Phase 7: The breakthrough that cracked the mask group

The nine Evanuris/Fen'Harel masks were the best example of combining file
mining with external research. Glenn discovered that every one of the nine
mask files shared a common "pantomime theater mask" description pattern,
then used that phrase to search external wiki sources and found all nine
matching codex pages, for example "a pantomime theater mask of Andruil"
leading to *Codex entry: The Lady of Fortune*. None of these nine titles
contain the word "mask" or the deity's name at all, which is exactly why
pure filename/token matching had failed on all nine. Cross checking those
nine titles against the current wiki table showed all nine already
existed as rows: two already correctly populated, seven blank, and two
holding an outdated or incorrect value (200 instead of the correct 100)
that the game files corrected.

This phase is a good illustration of the collaboration model that worked
best throughout: Claude handled bulk parsing, hash matching, and
consistency checking at scale; Glenn supplied game specific knowledge,
targeted web research, and judgment calls that no amount of file
inspection alone could produce.

## Phase 8: Iterative wiki merging, with real corrections caught along the way

The wiki merge happened over several rounds, each time pasting the current
wiki state back in as the source of truth (rather than trusting Claude's
own last known copy), applying a fixed rule set:

1. If a wiki row already has a power value, overwrite it with the
   game file value.
2. If a memento isn't in the wiki yet, add it with a blank location.
3. Exclude plot triggered "fake" mementos.

This surfaced several genuine corrections to existing (previously
guessed) wiki data, not just filled gaps:
- Ammazzacaffè, Grappling Hook, Vint 6 the Common Red, Templar's Ritual
  Kit: all previously listed at 100, corrected to 50.
- Falon'Din's and Dirthamen's masks (The Long Night, The Unspoken):
  previously listed at 200, corrected to 100.
- Blade of Warden Janos: previously listed at 100, corrected to 50 once
  its faction curio file (`GW_JanusSword`) was matched.

It also caught two collisions created by Glenn's own matching suggestions
in different rounds of the merge: the same source file
(`Tevinter_15_ManyLimbedIdol`, and separately `Nevarra_11_MiniTree`) got
proposed for two different wiki titles across different sessions. Neither
was silently resolved; both were flagged back for a decision, and the
original (more confident) assignment was kept in both cases.

One deliberate choice not to overwrite: two wiki rows ("Pillars of
Kal-Sharok: Stone" and "...Voice") already had values from an apparently
different, not yet mined source (Treviso vendor purchases, not Deep Roads
finds). The temptation to force four ambiguous Deep Roads files onto four
similarly named wiki rows was resisted for exactly these two, on the
reasoning that overwriting already correct data with a different item's
value would be worse than leaving a legitimate gap. (This later turned out
to be the right call. See Phase 12.)

## Phase 9: Knowing when to stop guessing

By the later merge rounds, a real cost and benefit judgment came into
play: roughly 27 regional trinket files had no confident textual match at
all (fully generic names, no in file description text, multiple plausible
wiki candidates). Rather than force matches or spend unlimited time
chasing diminishing returns, the explicit decision was made to leave these
blank, on the reasoning that the wiki can always be updated later if
someone finds something. A number of these were later resolved anyway,
using Glenn's own gameplay knowledge to make calls the files alone
couldn't support, for example "the Anderfels toy is Hessarian because
Hossberg Wetlands is in Anderfels," real world game geography, not
something derivable from XML.

## Phase 10: The phylactery investigation, a hypothesis correctly abandoned

One remaining item, `SD_Phylactery`, prompted a deeper dive. Glenn
explained the Dragon Age lore meaning of a phylactery (a blood vial used
to magically track mages), and a web search turned up a real in game
questline (Sea of Blood/Bloodbath, destroying Lucanis's phylactery) that
seemed thematically plausible. Claude proposed a theory connecting the
item to that questline's third, inconsistently named memento drop. Glenn's
own gameplay knowledge overturned this theory: he identified `SD` as
standing for the Shadow Dragons (a real Tevinter faction), not a "story
drop" abbreviation as guessed, and confirmed the item is very likely a
plot triggered Caretaker boost (same pattern as the two Special dragon
items) rather than a physical collectible with a discoverable codex title.
The item was excluded from the mapping at that point. This is a useful
record of a hypothesis being generated, tested against available
evidence, and correctly discarded rather than forced into the data,
arguably as valuable a result as a confirmed match. (It was resolved for
good in Phase 12, once a genuinely exhaustive search became possible.)

## Phase 11: Handoff to Claude Code

By this point the project had a working baseline: 110 confidently matched
items, a merged wiki table, and a clearly documented list of everything
still unresolved. Separately, and in parallel, a second wiki editor had
worked out a more rigorous method for resolving memento titles exactly,
rather than by fuzzy filename matching. Since that method required hopping
across a much larger subset of the 15GB export than this conversation
could practically upload, the project moved to Claude Code, which has
direct access to a local file tree.

Before moving, Claude wrote a handoff document summarizing everything
established so far: the tag hash to switch to leaf mechanism, the file
naming conventions and their quirks (including the `<n>` versus `<Name>`
inconsistency that had caused a silent bug earlier), the known exceptions,
and the current state of the wiki table and file to memento mapping. The
goal was for a fresh Claude Code session to be able to continue the work
without rediscovering any of it.

## Phase 12: The exact mapping method

Once in Claude Code, Glenn supplied a fully worked example (the memento
"One Moment of Victory") showing a real, deterministic GUID chain that
resolves a physical curio file all the way to its exact in game codex
title, no fuzzy filename matching required:

1. The curio file's `TemplateAsset` GUID is the master identifier for
   that physical object.
2. A `DES_Collectibles.xml` file under the relevant level/region places
   that GUID in the world via a `SpatialPrefabReferenceObjectData` block,
   which references a local override GUID (unique only within that file).
3. That override block, elsewhere in the same file, references a specific
   `CollectibleSets` file.
4. In that file, the matching `BWCollectiblesInstance` has a
   `CollectibleInstanceName`, an eight character hex localization ID.
5. `globalmaster.csv`, a file that had been supplied earlier without being
   understood, turned out to be the payoff: a localization ID to display
   string table (UTF-16LE encoded, no byte order mark). Looking up the ID
   from step 4 gives the real, in game codex title and its flavor text.

This whole chain was scripted using `xml.etree.ElementTree` rather than
regex, since the GUID scoping (override IDs are only unique within one
file) makes naive text search unsafe.

The Claude Code session also confirmed the hierarchy to switch pattern is
a generic Frostbite idiom used throughout loot selection generally, not
unique to mementos, and closed out a question left open since Phase 4:
whether the three unused XP tiers (Small, RootBarrier, VeryLarge) belonged
to some unmined weapon or armor category. An exhaustive search across
every plausible part of the file tree, including 52 merchant purchase
files that also reference the same hierarchy, found no trace of those
three tiers anywhere in the shipped game data, in any context. The
conclusion, per Glenn's own framing: the game's designers defined a
fuller tier ladder up front and only ever authored content for four of
the seven tiers. The other three are vestigial, unused scaffolding, not
something this project failed to find.

## Phase 13: Automated results versus the fuzzy matched baseline

Running the exact chain across all 141 known Smith XP tagged curio files
(the original 138 plus three newly discovered `SolasKeepsake` files) and
diffing against the earlier baseline produced a clean picture:

- 86 agreed exactly with the earlier fuzzy matched results, good cross
  validation of both methods.
- 24 came back with titles for files that had no baseline entry at all,
  the generic filename group left unresolved back in Phase 9. When
  checked against the actual wiki table rather than the smaller working
  CSV, every one of these 24 titles already existed as a real row, just
  with a blank power value. What had looked like 24 new mementos were
  really 24 existing rows nobody had filled in.
- 16 disagreed with the baseline. On inspection, 14 were confirmed
  corrections of earlier wrong guesses, including one pair (`Lute1` and
  `Lute2`) that had been assigned backwards during the original session's
  coin flip guess. One disagreement turned out not to be a disagreement
  at all: "Grappaling Hook," which had looked like a simple typo, is
  actually an intentional Antiva/Renaissance Italy pun (grappa plus
  grappling hook), confirmed by Glenn and kept as written. One
  (`Antiva_14_ToySword`) resolved to "Antivan Sprig," which on the
  surface contradicted its own in game description of a child's toy
  sword, until Glenn confirmed "sprig" here means a twig used as an
  improvised toy sword, resolving the apparent contradiction rather than
  flagging a data error.
- The nine pantomime masks from Phase 7 aren't placed via any
  `DES_Collectibles.xml` at all, since they spawn in a scripted theater
  scene rather than sitting in the open world, so the GUID chain
  couldn't reach them directly. Glenn independently confirmed the
  original fuzzy matched titles by looking them up directly in
  `globalmaster.csv`, so all nine were kept as already correct.
- Three items were excluded outright: the two Special dragon items and
  `SD_Phylactery`, all confirmed, this time conclusively, to be plot
  triggered boosts rather than physical pickups, since none of them are
  placed via any level file anywhere in the game. The three
  `SolasKeepsake` files uncovered along the way joined this excluded
  group too, by the same reasoning and for lack of any corroborating
  evidence of an in game item to match them to.

Reconciling all of this against the wiki table also surfaced two rows
that weren't new mementos at all: "Antivan Toy Sword" turned out to be a
duplicate of the real "Antivan Sprig" row, and "Templars in Nevarra"
turned out not to be a Caretaker Power memento in the first place (see
Phase 14). Four other rows that looked similarly suspicious at a glance,
"Open Book" and the four "Relief" entries, were confirmed as genuinely
separate, real mementos once Glenn recognized them from his own knowledge
of the items.

## Phase 14: A second editor's location complaint

A different wiki editor flagged that some Location values in the table
didn't match reality in game, for example the "Bones Beneath the Creek"
verses being listed as Rivain Coast when they're actually found in
Hossberg Wetlands. The task became: check every memento's actual codex
page for its real location field and correct the table.

Getting at those location fields hit an access problem worth remembering
for future projects: the wiki's site is protected by a Cloudflare
challenge that blocks essentially all non browser access, confirmed
across several different tools and approaches. The eventual workaround
was much better than scraping around the block: Fandom wikis support a
full XML database export via a built in special page, which produces
clean, structured wikitext for every article with no scraping required at
all. Glenn obtained this export (roughly 323 megabytes, over 178,000
pages) and provided it directly.

Streaming that file with an incremental XML parser (clearing each page
from memory as it was processed, essential for a file that size) and
pulling the relevant location field out of each target page's template
call confirmed both of the second editor's specific examples exactly, and
also surfaced a broader pattern: of 179 tracked pages, 89 had a flatly
different region listed than the current table showed, most often because
"Arlathan Forest" appeared to have been used as a default guess by earlier
editors whenever the real location wasn't known.

This pass also caught a subtler problem. "Templars in Nevarra" shared
identical location text with a different, genuine memento ("Dense Tome"),
which prompted a closer look. Its category field turned out to be "The
Mourn Watch" rather than "Mementos," the only one of all 180 tracked pages
not categorized that way. It's a lore pickup found at the same spot as a
real memento, not a Caretaker Power memento itself, and it was removed
from the table entirely rather than corrected.

The same pass found eight more power values that disagreed with the
ground truth tag hash data, all in items from the original unresolved
group, and all corrected from their old (guessed) values down to the
game confirmed 50.

## Phase 15: Final table regeneration

All of the above was applied on top of the wiki table as it stood at the
end of the original session, producing a new version with 183 rows, down
from 185: every confirmed title and power correction from Phase 13, every
location correction from Phase 14, the duplicate "Antivan Toy Sword" row
merged away, the non memento "Templars in Nevarra" row removed, and a
small display text fix for "Grappaling Hook" (the link text had been
showing the more familiar "Grappling Hook" while pointing at the
correctly spelled page). Every individual field change, 210 of them
total, was logged for Glenn to review before anything went live on the
actual wiki.

## What worked

- **Tracing one example from end to end by hand before automating.** The
  switch/hierarchy mechanism was fully verified on a single item (Mask of
  Torrenti) before any script was written. This made the eventual
  automation trustworthy rather than a guess at scale.
- **Verifying suspicious looking bulk results independently.** When the
  first automated pass showed all 40 faction curios sharing one tag, the
  finding was checked again with a raw grep that bypassed the script
  entirely, rather than assumed to be a bug or accepted uncritically.
- **Treating uncertainty as a legitimate output**, not a failure:
  surfacing collisions, zero confidence groups, and open questions
  explicitly rather than picking an answer that merely looked plausible
  and moving on.
- **Re syncing from Glenn's actual wiki state** at each merge round,
  rather than trusting Claude's last saved copy. This caught independent
  edits Glenn had made in the meantime (for example fixing redlinked page
  titles) and avoided clobbering them.
- **Combining automated file mining with targeted external research** (the
  "pantomime theater mask" search) at exactly the point where file data
  ran out. Neither approach alone would have cracked the mask group.
- **Moving to a better tool once the current one hit its ceiling.**
  Fuzzy matching got the project most of the way; the exact GUID chain
  method, only practical with direct filesystem access, closed out nearly
  everything that remained. Recognizing that boundary and handing off
  cleanly, rather than continuing to force the wrong tool at the problem,
  is what let the project actually finish.

## What didn't work or had to be abandoned

- Reading raw EBX binary by hand. The necessary tooling didn't exist in
  this environment, which forced a switch to a decompiled XML export
  instead.
- Naive fuzzy text matching (token overlap plus string similarity) as a
  general purpose solution. Useful for maybe 40 percent of ambiguous
  items, but actively dangerous past that point without a human sanity
  check on every match.
- Assuming internal directory or prefix naming reflects real in game
  location or category. Disproven early (files prefixed "Anderfels" that
  turned out to be located in Rivain Coast) and had to be explicitly
  unlearned so it didn't taint later judgment calls. The same lesson
  recurred at larger scale in Phase 14, where "Arlathan Forest" turned out
  to have been an overused default guess across dozens of wiki rows.
- Scraping the wiki's own site directly for location data. Blocked
  entirely by a Cloudflare challenge across every access method tried;
  the working solution was a completely different approach (a bulk
  database export) rather than a cleverer way through the same wall.

## Team dynamics

This was genuinely a three way collaboration by the end: Glenn, Claude,
and a second wiki editor working in parallel, who independently worked
out the exact mapping method that Claude Code would later automate, and
who separately flagged the location data problem that became Phase 14.
Recognizing that this conversation's approach had reached its practical
ceiling, and that a different tool (Claude Code, with direct filesystem
access to the full export) was better suited to the newly discovered
method, the project was handed off with a dedicated technical brief
summarizing the mechanism, known pitfalls, and everything resolved so
far, so the next phase of work could start from established ground truth
instead of re deriving it. When that Claude Code session finished its own
work, it in turn wrote its own summary for this conversation to fold back
in, which is what most of Phases 11 through 15 are drawn from.

## Outcome

- A previously binary, undocumented, schema dependent game asset format
  was reverse engineered to a fully automatable resolution pipeline: tag
  hash to switch row to leaf XP.
- That pipeline was later shown, via an independently discovered GUID
  chain through the game's level and localization data, to agree with the
  original fuzzy matched results in the large majority of cases, and to
  correct or newly resolve nearly everything that didn't.
- The final wiki table (183 rows) has a confirmed power value and a
  verified location for essentially every real memento, several outright
  corrections to previously guessed data, and a small number of items
  conclusively identified as plot triggered rather than physical, and
  excluded on solid evidence rather than a shrug.
- The project moved cleanly across two different tools and three
  collaborators without losing continuity, by treating clear, honest
  documentation of the current state, including what was still unknown,
  as part of the deliverable at every handoff.
