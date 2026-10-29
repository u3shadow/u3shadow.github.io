"""Fetch the pinned existing diagram runtime and five Lucide icons; no npm runtime."""
import io
import json
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'u3coding-static-maintenance/1.0'})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def main():
    version = '11.12.0'
    package = json.loads(fetch(f'https://registry.npmjs.org/mermaid/{version}'))
    archive = tarfile.open(fileobj=io.BytesIO(fetch(package['dist']['tarball'])), mode='r:gz')
    destination = ROOT / 'assets/vendor/mermaid'
    count = 0
    for member in archive.getmembers():
        name = member.name
        if not member.isfile(): continue
        if name == 'package/LICENSE':
            relative = Path('LICENSE')
        elif name == 'package/dist/mermaid.esm.min.mjs':
            relative = Path('mermaid.esm.min.mjs')
        elif name.startswith('package/dist/chunks/mermaid.esm.min/') and name.endswith('.mjs'):
            relative = Path(name.removeprefix('package/dist/'))
        else: continue
        path = destination / relative
        if not path.resolve().is_relative_to(destination.resolve()):
            raise ValueError('Unsafe archive path')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(archive.extractfile(member).read())
        count += 1
    icons = ROOT/'assets/site/icons'
    icons.mkdir(parents=True, exist_ok=True)
    icon_version = '0.468.0'
    for name in ['menu', 'search', 'sun', 'moon', 'minimize']:
        (icons/f'{name}.svg').write_bytes(fetch(f'https://unpkg.com/lucide-static@{icon_version}/icons/{name}.svg'))
    (icons/'LICENSE').write_bytes(fetch(f'https://unpkg.com/lucide-static@{icon_version}/LICENSE'))
    (destination/'VERSION').write_text(f'mermaid {version}\nSource: https://www.npmjs.com/package/mermaid/v/{version}\n', encoding='utf-8')
    print(f'Vendored Mermaid {version}: {count} module/license files. Lucide {icon_version}: 5 icons.')


if __name__ == '__main__':
    main()
