"""NaughtyBoddy P5.3 synthetic contract kit, not a model-quality benchmark.

All data is fictional and contains explicit SRC/TGT marker tokens. Checks only
structure, exact synthetic ID alignment, and declared knowledge visibility.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED, BadZipFile

ROOT = Path(__file__).resolve().parent / "benchmarks" / "p53"
MAX_JSON_BYTES = 256_000
MAX_EPUB_BYTES = 3 * 1024 * 1024
MAX_PART_BYTES = 512 * 1024
MAX_MEMBERS = 50
NS_OPF = "http://www.idpf.org/2007/opf"
NS_CONTAINER = "urn:oasis:names:tc:opendocument:xmlns:container"
NS_HTML = "http://www.w3.org/1999/xhtml"
ALLOWED_TAGS = {"h1", "h2", "h3", "p", "div"}


class KitError(ValueError):
    pass


def read_json(path: Path | str) -> dict:
    path = Path(path)
    if path.stat().st_size > MAX_JSON_BYTES:
        raise KitError("JSON exceeds fixture limit")
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise KitError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    try:
        result = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise KitError(f"Malformed JSON: {exc}") from exc
    if not isinstance(result, dict):
        raise KitError("Fixture must be an object")
    return result


def item_error(code: str, **kwargs) -> dict:
    return {"code": code, **kwargs}


def result_report(kind: str, errors: list[dict], checked: int, note: str) -> dict:
    return {"schema_version": 1, "kind": kind, "passed": not errors,
            "checked": checked, "errors": errors,
            "scope": "synthetic_contract_only", "note": note}


def book_segments(case: dict) -> list[tuple[str, str, str, str, str]]:
    chapters = case.get("chapters")
    if case.get("schema_version") != 1 or not isinstance(chapters, list) or not chapters:
        raise KitError("Invalid book manifest")
    seen = set()
    names = set()
    out = []
    for chapter in chapters:
        name = chapter.get("file")
        if (not isinstance(name, str) or not name.startswith("OEBPS/")
                or ".." in PurePosixPath(name).parts or name in names):
            raise KitError("Invalid chapter path")
        names.add(name)
        for seg in chapter.get("segments", []):
            sid, tag = seg.get("id"), seg.get("tag")
            if (not isinstance(sid, str) or not sid or sid in seen
                    or tag not in ALLOWED_TAGS):
                raise KitError("Invalid or duplicate segment")
            if not all(isinstance(seg.get(k), str) and seg[k] for k in ("source", "target")):
                raise KitError("Missing synthetic source/target token")
            seen.add(sid)
            out.append((name, sid, tag, seg["source"], seg["target"]))
    return out


def generate_epub(case: dict, destination: str | Path, variant: str = "good") -> None:
    """Create self-contained EPUB3 package from safe artificial tokens."""
    if variant not in {"source", "good", "p_only_bad", "missing_bad", "swapped_bad"}:
        raise KitError("Unknown demo variant")
    segments = book_segments(case)
    translation = {sid: tgt for _, sid, _, _, tgt in segments}
    p_ids = [sid for _, sid, tag, _, _ in segments if tag == "p"]
    if variant == "swapped_bad":
        if len(p_ids) < 2:
            raise KitError("Swap demo requires two paragraphs")
        translation[p_ids[0]], translation[p_ids[1]] = translation[p_ids[1]], translation[p_ids[0]]
    omitted = p_ids[-1] if p_ids else None
    chapters = []
    for idx, section in enumerate(case["chapters"], 1):
        name = section["file"]
        pieces = []
        for file, sid, tag, src, _ in segments:
            if file != name or (variant == "missing_bad" and sid == omitted):
                continue
            text = src if variant == "source" or (variant == "p_only_bad" and tag != "p") else translation[sid]
            pieces.append('<{0} data-nb-id="{1}">{2}</{0}>'.format(tag, escape(sid), escape(text)))
        doc = (f'<?xml version="1.0" encoding="utf-8"?><html xmlns="{NS_HTML}">'
               '<head><title>Synthetic</title></head><body>' + "".join(pieces) + '</body></html>')
        chapters.append((idx, name, doc))
    manifest = "".join(
        f'<item id="c{i}" href="{escape(str(PurePosixPath(name).relative_to("OEBPS")))}" '
        'media-type="application/xhtml+xml"/>' for i, name, _ in chapters)
    spine = "".join(f'<itemref idref="c{i}"/>' for i, _, _ in chapters)
    opf = (f'<?xml version="1.0" encoding="utf-8"?><package xmlns="{NS_OPF}" '
           'version="3.0" unique-identifier="uid"><metadata '
           'xmlns:dc="http://purl.org/dc/elements/1.1/">'
           '<dc:identifier id="uid">urn:uuid:nb-p53-synthetic</dc:identifier>'
           '<dc:title>Artificial Chapter Fixture</dc:title><dc:language>en</dc:language>'
           '<meta property="dcterms:modified">2026-11-09T00:00:00Z</meta>'
           '</metadata><manifest>' + manifest + '</manifest><spine>' + spine + '</spine></package>')
    container = (f'<?xml version="1.0" encoding="utf-8"?><container xmlns="{NS_CONTAINER}" '
                 'version="1.0"><rootfiles><rootfile full-path="OEBPS/content.opf" '
                 'media-type="application/oebps-package+xml"/></rootfiles></container>')
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(dest, 'w') as z:
        z.writestr('mimetype', 'application/epub+zip', compress_type=ZIP_STORED)
        z.writestr('META-INF/container.xml', container, compress_type=ZIP_DEFLATED)
        z.writestr('OEBPS/content.opf', opf, compress_type=ZIP_DEFLATED)
        for _, path, document in chapters:
            z.writestr(path, document, compress_type=ZIP_DEFLATED)


def epub_units(path: str | Path) -> tuple[list[str], list[tuple[str, str, str, str]]]:
    """Bounded parser for the generated fixture shape; not a general EPUB reader."""
    path = Path(path)
    if path.stat().st_size > MAX_EPUB_BYTES:
        raise KitError("EPUB archive exceeds byte limit")
    try:
        with ZipFile(path) as z:
            info = z.infolist()
            names = [i.filename for i in info]
            if len(info) > MAX_MEMBERS or len(set(names)) != len(names):
                raise KitError("Too many or duplicate EPUB members")
            if any(i.file_size > MAX_PART_BYTES for i in info) or sum(i.file_size for i in info) > MAX_EPUB_BYTES:
                raise KitError("Expanded EPUB too large")
            for name in names:
                if name.startswith('/') or '\\' in name or '..' in PurePosixPath(name).parts:
                    raise KitError("Unsafe ZIP member path")
            if z.read('mimetype') != b'application/epub+zip':
                raise KitError("Not an EPUB")
            root = ET.fromstring(z.read('META-INF/container.xml'))
            entry = root.find(f'.//{{{NS_CONTAINER}}}rootfile')
            if entry is None:
                raise KitError("Missing OPF reference")
            opf_path = entry.get('full-path', '')
            if opf_path not in names or not opf_path.endswith('.opf'):
                raise KitError("Invalid OPF path")
            opf = ET.fromstring(z.read(opf_path))
            manifest = opf.find(f'{{{NS_OPF}}}manifest')
            spine = opf.find(f'{{{NS_OPF}}}spine')
            if manifest is None or spine is None:
                raise KitError("Missing EPUB manifest or spine")
            relative = PurePosixPath(opf_path).parent
            known = {}
            for item in manifest:
                if item.get('media-type') != 'application/xhtml+xml':
                    continue
                href = item.get('href', '')
                if href.startswith('/') or '..' in PurePosixPath(href).parts:
                    raise KitError("Unsafe chapter path")
                name = str(relative / href)
                if name not in names:
                    raise KitError("Missing chapter")
                known[item.get('id')] = name
            sections, out = [], []
            for item in spine:
                name = known.get(item.get('idref'))
                if not name:
                    raise KitError("Broken EPUB spine")
                sections.append(name)
                root = ET.fromstring(z.read(name))
                for node in root.iter():
                    sid = node.get('data-nb-id')
                    if sid is not None:
                        out.append((name, sid, node.tag.split('}')[-1], ''.join(node.itertext()).strip()))
            return sections, out
    except (BadZipFile, ET.ParseError, KeyError, RuntimeError) as exc:
        raise KitError(f'Malformed synthetic EPUB: {exc}') from exc


def check_book(case: dict, epub: Path | str) -> dict:
    expected = book_segments(case)
    sections, actual = epub_units(epub)
    issues = []
    expected_sections = [x['file'] for x in case['chapters']]
    if sections != expected_sections:
        issues.append(item_error('chapter_spine_mismatch', expected=expected_sections, actual=sections))
    by_id = {}
    for file, sid, tag, text in actual:
        if sid in by_id:
            issues.append(item_error('duplicate_segment', id=sid))
        by_id[sid] = (file, tag, text)
    seen = set()
    for file, sid, tag, src, tgt in expected:
        seen.add(sid)
        if sid not in by_id:
            issues.append(item_error('missing_segment', id=sid))
            continue
        actual_file, actual_tag, value = by_id[sid]
        if actual_file != file or actual_tag != tag:
            issues.append(item_error('segment_structure', id=sid))
        if value == src:
            issues.append(item_error('unchanged_source', id=sid, tag=tag))
        elif value != tgt:
            issues.append(item_error('target_token_mismatch', id=sid))
    for sid in by_id.keys() - seen:
        issues.append(item_error('extra_segment', id=sid))
    return result_report('book', issues, len(expected),
                         'Exact synthetic target markers and EPUB shape; not translation quality.')


def check_comic(case: dict, candidate: dict) -> dict:
    bubbles = case.get('bubbles')
    if case.get('schema_version') != 1 or not isinstance(bubbles, list):
        raise KitError('Invalid comic case')
    if not isinstance(candidate.get('outputs'), list):
        raise KitError('Comic candidate needs outputs list')
    expected = {b['id']: b['target_token'] for b in bubbles}
    if len(expected) != len(bubbles):
        raise KitError('Duplicate case bubble ID')
    by_token = {token: bid for bid, token in expected.items()}
    actual, issues = {}, []
    for row in candidate['outputs']:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not isinstance(row.get('text'), str):
            raise KitError('Invalid comic response')
        if row['id'] in actual:
            issues.append(item_error('duplicate_bubble', id=row['id']))
        actual[row['id']] = row['text']
    for bid, token in expected.items():
        if bid not in actual:
            issues.append(item_error('missing_bubble', id=bid))
        elif actual[bid] != token:
            other = by_token.get(actual[bid])
            issues.append(item_error('shifted_target_token' if other else 'wrong_target_token',
                                      id=bid, from_id=other))
    for bid in actual.keys() - expected.keys():
        issues.append(item_error('extra_bubble', id=bid))
    return result_report('comic', issues, len(expected),
                         'Exact synthetic tokens detect broken stable-ID mapping; not OCR accuracy.')


def check_memory(case: dict, candidate: dict) -> dict:
    actors = case.get('characters')
    if case.get('schema_version') != 1 or not isinstance(actors, list) or len(set(actors)) != len(actors):
        raise KitError('Invalid memory case')
    known = {}
    for fact in case.get('facts', []):
        fid = fact['id']
        if fid in known:
            raise KitError('Duplicate fact ID')
        viewers = set(actors) if fact.get('public') else set(fact.get('witnesses', []))
        if not viewers.issubset(set(actors)):
            raise KitError('Unknown witness')
        known[fid] = viewers
    snapshots = candidate.get('snapshots')
    if not isinstance(snapshots, dict):
        raise KitError('Expected snapshots object')
    issues, count = [], 0
    for actor, channels in snapshots.items():
        if actor not in actors:
            issues.append(item_error('unknown_character', actor=actor))
            continue
        if not isinstance(channels, dict):
            raise KitError('Invalid snapshot channels')
        for channel, facts in channels.items():
            if channel not in {'history', 'lorebook', 'memory'}:
                raise KitError('Unsupported context channel')
            if not isinstance(facts, list) or not all(isinstance(v, str) for v in facts):
                raise KitError('Invalid fact ID list')
            for fid in facts:
                count += 1
                if fid not in known:
                    issues.append(item_error('unknown_fact', actor=actor, channel=channel, fact_id=fid))
                elif actor not in known[fid]:
                    issues.append(item_error('private_fact_leak', actor=actor, channel=channel, fact_id=fid))
    for actor in actors:
        if actor not in snapshots:
            issues.append(item_error('missing_actor', actor=actor))
    return result_report('memory', issues, count,
                         'Visibility of explicit synthetic fact IDs in context snapshots only; not model beliefs.')


def run_demo(root: Path = ROOT) -> dict:
    book = read_json(root / 'book_case.json')
    comic = read_json(root / 'comic_case.json')
    memory = read_json(root / 'memory_case.json')
    results = {}
    with tempfile.TemporaryDirectory(prefix='nb-evalkit-') as tmp:
        for variant, expected in [('good', True), ('p_only_bad', False),
                                  ('missing_bad', False), ('swapped_bad', False)]:
            epub = Path(tmp) / f'{variant}.epub'
            generate_epub(book, epub, variant)
            results['book_' + variant] = {'expected_pass': expected, **check_book(book, epub)}
    for name, expected in [('comic_good', True), ('comic_bad_shifted', False)]:
        r = check_comic(comic, read_json(root / (name + '.json')))
        results[name] = {'expected_pass': expected, **r}
    for name, expected in [('memory_good', True), ('memory_bad_leak', False)]:
        r = check_memory(memory, read_json(root / (name + '.json')))
        results[name] = {'expected_pass': expected, **r}
    return {'suite': 'p53_synthetic_contracts', 'passed': all(
        r['passed'] == r['expected_pass'] for r in results.values()),
        'cases': results, 'real_model_tests': 'not_run'}


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(description='Offline synthetic structure/ID/knowledge checks')
    sub = cli.add_subparsers(dest='action', required=True)
    sub.add_parser('demo')
    gen = sub.add_parser('generate-book')
    gen.add_argument('--out-dir', type=Path, required=True)
    book = sub.add_parser('check-book')
    book.add_argument('--case', type=Path, default=ROOT / 'book_case.json')
    book.add_argument('--epub', type=Path, required=True)
    comic = sub.add_parser('check-comic')
    comic.add_argument('--case', type=Path, default=ROOT / 'comic_case.json')
    comic.add_argument('--candidate', type=Path, required=True)
    mem = sub.add_parser('check-memory')
    mem.add_argument('--case', type=Path, default=ROOT / 'memory_case.json')
    mem.add_argument('--candidate', type=Path, required=True)
    args = cli.parse_args(argv)
    try:
        if args.action == 'demo':
            output = run_demo()
        elif args.action == 'generate-book':
            manifest = read_json(ROOT / 'book_case.json')
            for variant in ('source', 'good', 'p_only_bad', 'missing_bad', 'swapped_bad'):
                generate_epub(manifest, args.out_dir / (variant + '.epub'), variant)
            output = {'out_dir': str(args.out_dir), 'generated': 5}
        elif args.action == 'check-book':
            output = check_book(read_json(args.case), args.epub)
        elif args.action == 'check-comic':
            output = check_comic(read_json(args.case), read_json(args.candidate))
        else:
            output = check_memory(read_json(args.case), read_json(args.candidate))
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0 if output.get('passed', True) else 1
    except (KitError, OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
