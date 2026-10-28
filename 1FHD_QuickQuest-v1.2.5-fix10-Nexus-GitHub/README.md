# FHD_QuickQuest v1.2.5-fix10 — recovered review sources

Готовый пакет для GitHub и проверки модераторами: 28 файлов, включая 12 JSON-сборников со всеми 114 квестами. Все 120 рабочих файлов пересобираются побайтово точно. Ручное восстановление файлов на вашем ПК не требуется.

## Supplied content and provenance

Source upload: `FHD_QuickQuest_v1.2.5-fix10.rar`, RAR5, 7,983,408 bytes. SHA-256: `f55205dc47720f92956d735d74f0b1fff25623c4c78ce9db0975bddc5dbf674d`. Original metadata credits **Prolog_D**.

The repository reconstructs the uploaded runtime bytes without gameplay changes. It contains recovered editable data, build tooling and verification; it does not claim that the author's original authoring directory was supplied. No specific Nexus moderator checklist was attached, and reconstruction checks do not imply moderation approval.

| Editable source | Rebuilt runtime content |
| --- | --- |
| `source/quests/Rus/quests_01.json` … `quests_12.json` | All 114 QMM7 quests, grouped into twelve source catalogs |
| `source/config/` | Main.dat, CacheData.dat and Rus/Lang.dat |
| `source/artwork/` | Both original John Doe JPG images |
| `source/ModuleInfo.txt` | Original CP1251 metadata |

The quests contain **14,064 locations**, **37,678 jumps** and **4,501 parameter definitions**. All 114 have entries in the supplied configuration. No DLL or SCR was supplied, so an RSON project is not needed. The runtime QMM format itself contains the text-quest graph and formulas.

## Recovery format

The source package contains **28 files**, below the requested 100-file limit. Quest sources are grouped alphabetically into twelve UTF-8 JSON catalogs (`srhd-qmm7-catalog-v1`), with up to ten quests per catalog. Each entry is keyed by its original `.qmm` filename, so the builder restores all 114 separate runtime quests automatically.

Each quest document uses the documented-in-code `srhd-qmm7-sparse-v1` structure. It stores named header fields, parameters, location text/media, formulas, jumps, conditions and explicit parameter changes. Sparse lists contain the records actually stored in the QMM, with one-based `parameter_id` values. Omitted change/condition records retain the QMM format's default meaning; they are not expanded into thousands of redundant default objects.

Location IDs and jump endpoints are explicit. Collection counts and string lengths are calculated by the encoder. `null` and empty strings remain distinct. Original record order, reserved bytes, coordinates, priorities, limits and version/changelog strings are retained. There is no compressed binary quest blob, Base64 runtime payload or dependency on the original QMM files.

DAT JSON preserves ordered blocks, repeated parameters, sorting metadata, encryption seeds and embedded game script text. CacheData also uses an additional resource-DAT checksum envelope; both its length and CRC calculations are regenerated rather than copied as opaque bytes. Metadata source is UTF-8, rebuilt with the original CP1251 encoding and CRLF line endings.

## Automated build

Only Python 3.12 and its standard library are required. No game installation, Windows, pip package, native compiler or quest editor is needed to reconstruct the supplied version.

```sh
python3 tests/verify.py
python3 scripts/build.py --verify-original
```

Output: `dist/FHD_QuickQuest-v1.2.5-fix10-install.zip`, with all 120 runtime files under `Mods/FHD_MODS/FHD_QuickQuest/`. GitHub Actions runs verification and publishes that install ZIP plus a fresh report as a downloadable artifact.

For intentional edits, omit `--verify-original`, which enforces the original uploaded SHA-256 hashes. Compressed byte identity was verified with Python 3.12.14 / zlib 1.3.2; a different zlib encoder can emit different compressed bytes for otherwise equivalent DAT content. QMM encoding itself is uncompressed.

The source ZIP contains no generated DAT/QMM/install archive, source-dump duplicates, build caches or git history. The JPG files are original editable media inputs, required by the custom quest image bindings.

## Verification and its limits

`build-verification.json` records **598 passing checks**, including:

- Building from a temporary directory containing only source and scripts, then matching all 120 original runtime SHA-256 hashes.
- All 114 named quests retained in twelve catalogs; the source package contains no more than 100 files.
- Complete DAT/QMM decode/encode roundtrips and DAT checksum corruption rejection.
- Unique location IDs, valid jump endpoints and valid/unique sparse parameter IDs in every quest.
- Resolution of 116 configured local file paths: 114 quests and two JPGs; custom image keys resolve through `Bm.PQI`.
- Actual in-memory quest-text and DAT script edits surviving serialization, plus detection of an intentionally broken graph reference.
- Preservation of CP1251 metadata, priority, language declarations and original release labels.

As a separate recovery check, the existing local **SRHD XenoModKit 0.10.4** quest parser/writer also parsed all 114 uploaded quests through EOF and reproduced their bytes exactly. It is not a build dependency and is not bundled in this package; this check is recorded in `recovery-notes.json`.

The quests refer to 625 distinct image/sound/track bindings. The two custom `FHDJohnDoe_01`/`FHDJohnDoe_02` images and their CacheData entries are included. Other media depend on game resources; their availability was not checked against a running installation. No live game, quest interpreter, TGE GUI or mod loader was executed. End-to-end quest completion, game event timing, monetary marker handling, fee deduction, existing saves and language fallback remain unverified. Byte identity establishes recovery fidelity, not gameplay correctness.

## Original labels and behavior to review

- The archive filename says **v1.2.5-fix10**, while `ModuleInfo.txt` still says **ver.1.2.3**. QMMs retain embedded changelog strings such as `FHD_QUICKQUEST_V0.14_SINGLE_REAL_MONEY_PARAMETER`. These original labels are preserved, without inventing a replacement version.
- Metadata advertises a **10–25%** fee. `Script.FHDQuickQuest10.Process` clamps `markerIndex` to 0–10 and computes `selectedPercent=10+markerIndex`, so that runtime selection is **10–20%**. The original text and script were not silently reconciled.
- Metadata advertises Russian and English, but only Russian config/quest payloads were supplied. No English translation or language DAT was invented.
- The original priority is **100**; dependency and conflict fields are empty. Startup removes the older `FHDQuickQuestCore`, `Core08` and `Core09` custom-info records and ensures `Core10` exists. The original code is visible in `source/config/Main.json`.

## Removed auxiliary files and attribution

Only the two root BMP screenshots (`КВЕСТЫ.bmp`, `КВЕСТЫ 2.bmp`, both 1920×1080) were excluded. They illustrate gameplay and are not referenced by the configs or quest media fields. Their original sizes and SHA-256 hashes are recorded in `recovery-notes.json`. The original upload is unchanged.

The DAT codec reimplements the format used by Sergei Osminin's MIT-licensed `rangers-utils`. QMM layout was cross-checked with SRHD XenoModKit by **Xenomorphchyma** and the existing local game-structure research. The compact codec included here uses Python's standard library. This recovery does not assert authorship of the original mod or assign it a new license; no mod license file was supplied.
