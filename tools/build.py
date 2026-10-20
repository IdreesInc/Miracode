"""Build reproducible base and Nerd Font release artifacts.

Requires FontForge 20230101 Python bindings and requirements-build.txt.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
import fontforge
import fontTools
from fontTools.ttLib import TTFont
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

ROOT = Path(__file__).resolve().parents[1]
PATCHER_VERSION = '3.5.1'
PATCHER_SHA256 = '42bcb32145499a35732274c7fc48deb434ad0d2e0e118f98527c1479c6fa251a'
PATCHER_URL = f'https://github.com/ryanoasis/nerd-fonts/releases/download/v{PATCHER_VERSION}/FontPatcher.zip'
DEFAULT_EPOCH = 1707523200  # 2024-02-10 UTC; overridden by SOURCE_DATE_EPOCH.

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(command, **kwargs):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            encoding='utf-8', **kwargs)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout[-4000:])

def normalize(path, epoch, source_hash):
    font = TTFont(path, recalcTimestamp=False)
    font['head'].created = font['head'].modified = epoch + 2082844800
    if 'FFTM' in font:
        del font['FFTM']
    unique = f'{font["name"].getDebugName(6)};{font["name"].getDebugName(5)};{source_hash[:12]}'
    font['name'].removeNames(nameID=3)
    for platform, encoding, language in [(3, 1, 0x409), (1, 0, 0)]:
        font['name'].setName(unique, 3, platform, encoding, language)
    # Multi-cell ligature advances are compatible with fixed-pitch text.
    font['post'].isFixedPitch = 1
    font.save(path)
    font.close()

def fit_added_icons(base_path, patched_path):
    base, patched = TTFont(base_path), TTFont(patched_path, recalcTimestamp=False)
    old, new = base.getBestCmap(), patched.getBestCmap()
    glyphs = patched.getGlyphSet()
    bottom, top = base['hhea'].descent, base['hhea'].ascent
    fitted = 0
    for code in set(new) - set(old):
        name = new[code]
        glyph = patched['glyf'][name]
        glyph.recalcBounds(patched['glyf'])
        if not glyph.numberOfContours or (glyph.yMin >= bottom and glyph.yMax <= top):
            continue
        scale = min(1, (top - bottom) / (glyph.yMax - glyph.yMin))
        shift = max(bottom - glyph.yMin * scale, min(0, top - glyph.yMax * scale))
        advance = patched['hmtx'][name][0]
        pen = TTGlyphPen(glyphs)
        glyphs[name].draw(TransformPen(pen, (scale, 0, 0, scale, advance * (1 - scale) / 2, shift)))
        patched['glyf'][name] = pen.glyph()
        patched['glyf'][name].recalcBounds(patched['glyf'])
        patched['hmtx'][name] = (advance, patched['glyf'][name].xMin)
        fitted += 1
    patched.save(patched_path)
    base.close()
    patched.close()
    return fitted

def check_patched(base_path, patched_path):
    base, patched = TTFont(base_path), TTFont(patched_path)
    old, new = base.getBestCmap(), patched.getBestCmap()
    if not set(old).issubset(new):
        raise RuntimeError('Patcher removed existing character coverage')
    for code, name in old.items():
        if base['hmtx'][name][0] != patched['hmtx'][new[code]][0]:
            raise RuntimeError(f'Patcher changed advance for U+{code:04X}')
    def ligatures(font):
        reverse = {name: code for code, name in font.getBestCmap().items()}
        result = {}
        for lookup in font['GSUB'].table.LookupList.Lookup:
            for sub in lookup.SubTable:
                for first, values in getattr(sub, 'ligatures', {}).items():
                    for value in values:
                        sequence = tuple(reverse[name] for name in [first] + value.Component)
                        result[sequence] = font['hmtx'][value.LigGlyph][0]
        return result
    if ligatures(base) != ligatures(patched):
        raise RuntimeError('Patcher changed ligatures or their advances')
    for code in [0xE0A0, 0xE0B0, 0xF07B, 0xF09B, 0xF0001]:
        if code not in new or patched['hmtx'][new[code]][0] != 1536:
            raise RuntimeError(f'Missing or non-single-cell icon U+{code:04X}')
    family = patched['name'].getDebugName(1)
    if 'Miracode' not in family or 'Nerd Font' not in family or len(family) > 31:
        raise RuntimeError(f'Unexpected patched family name: {family}')
    return len(set(new) - set(old))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-only', action='store_true', help='Skip the Nerd Fonts stage')
    parser.add_argument('--patcher-archive', type=Path, help='Use a local, checksum-verified FontPatcher.zip')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/release')
    args = parser.parse_args()
    if fontforge.version() != '20230101' or fontTools.__version__ != '4.63.0':
        parser.error('Pinned toolchain required: FontForge 20230101 and fontTools 4.63.0')
    epoch = int(os.environ.get('SOURCE_DATE_EPOCH', DEFAULT_EPOCH))
    if not 315532800 <= epoch <= 4354819199:
        parser.error('SOURCE_DATE_EPOCH must be in the ZIP-supported 1980-2107 range')
    source = hashlib.sha256()
    for path in sorted((ROOT / 'src').iterdir()):
        if path.is_file():
            source.update(path.name.encode() + b'\0' + path.read_bytes())
    source_hash = source.hexdigest()
    environment = dict(os.environ, PYTHONHASHSEED='0', PYTHONUTF8='1', LC_ALL='C', SOURCE_DATE_EPOCH=str(epoch))
    manifest = {'sourceSha256': source_hash, 'sourceDateEpoch': epoch,
                'fontforge': fontforge.version(), 'fonttools': fontTools.__version__, 'files': []}
    with tempfile.TemporaryDirectory(prefix='miracode-release-') as temporary:
        stage = Path(temporary)
        shutil.copytree(ROOT / 'src', stage / 'src', ignore=shutil.ignore_patterns('__pycache__'))
        (stage / 'examples').mkdir()
        run([sys.executable, 'miracode.py'], cwd=stage / 'src', env=environment)
        release = stage / 'release'
        release.mkdir()
        base = release / 'Miracode.ttf'
        shutil.copyfile(stage / 'dist/Miracode.ttf', base)
        normalize(base, epoch, source_hash)
        subprocess.run([sys.executable, str(ROOT / 'tests/check_font.py'), str(base)], env=environment, check=True)
        shutil.copyfile(ROOT / 'LICENSE', release / 'LICENSE.txt')
        if not args.base_only:
            archive = args.patcher_archive
            if archive is None:
                cache = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')) / 'miracode'
                cache.mkdir(parents=True, exist_ok=True)
                archive = cache / f'FontPatcher-{PATCHER_VERSION}.zip'
                if not archive.exists():
                    request = urllib.request.Request(PATCHER_URL, headers={'User-Agent': 'Miracode-font-build'})
                    with urllib.request.urlopen(request, timeout=60) as response:
                        archive.write_bytes(response.read())
            if sha256(archive) != PATCHER_SHA256:
                raise RuntimeError('FontPatcher archive checksum mismatch')
            patcher = stage / 'patcher'
            with zipfile.ZipFile(archive) as package:
                for entry in package.namelist():
                    if Path(entry).is_absolute() or '..' in Path(entry).parts:
                        raise RuntimeError('Unsafe FontPatcher archive path')
                package.extractall(patcher)
            patched_dir = stage / 'patched'
            patched_dir.mkdir()
            command = [sys.executable, str(patcher / 'font-patcher'), str(base), '--complete',
                       '--careful', '--single-width-glyphs', '--metrics', 'TYPO',
                       '--no-progressbars', '--outputdir', str(patched_dir)]
            run(command, cwd=patcher, env=environment)
            generated = list(patched_dir.glob('*.ttf'))
            if len(generated) != 1:
                raise RuntimeError(f'Expected one patched font, found {len(generated)}')
            patched = release / generated[0].name
            shutil.copyfile(generated[0], patched)
            fitted = fit_added_icons(base, patched)
            normalize(patched, epoch, source_hash)
            added = check_patched(base, patched)
            subprocess.run([sys.executable, str(ROOT / "tests/check_font.py"), str(patched)], env=environment, check=True)
            manifest['nerdFonts'] = {'version': PATCHER_VERSION, 'archiveSha256': PATCHER_SHA256,
                                      'url': PATCHER_URL, 'addedCodepoints': added,
                                      'iconsFittedToTextMetrics': fitted,
                                      'options': command[3:-2]}
            for path in (patcher / 'src/glyphs').rglob('*'):
                if path.is_file() and path.name.lower().startswith(('license', 'copying', 'readme')):
                    target = release / 'icon-licenses' / path.relative_to(patcher / 'src/glyphs')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, target)
        for path in sorted(release.rglob('*')):
            if path.is_file():
                manifest['files'].append({'file': str(path.relative_to(release)), 'sha256': sha256(path)})
        (release / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        (release / 'INSTALL.txt').write_text('Install the TTF files for the current user, then restart applications.\n'
                                           'This source build contains Regular only. Additional styles are a separate proposal.\n')
        archive = release / 'Miracode-fonts.zip'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as package:
            for path in sorted(release.rglob('*')):
                if not path.is_file() or path == archive:
                    continue
                entry = zipfile.ZipInfo('Miracode/' + str(path.relative_to(release)), time.gmtime(epoch)[:6])
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.create_system = 3
                entry.external_attr = 0o100644 << 16
                package.writestr(entry, path.read_bytes())
        (release / 'SHA256SUMS').write_text(''.join(f'{sha256(path)}  {path.name}\n'
                                                   for path in sorted(release.iterdir()) if path.is_file()))
        args.output.mkdir(parents=True, exist_ok=True)
        shutil.copytree(release, args.output, dirs_exist_ok=True)
        print(json.dumps({'output': str(args.output), 'archiveSha256': sha256(args.output / archive.name),
                          'nerdFonts': manifest.get('nerdFonts')}))

if __name__ == '__main__':
    main()
