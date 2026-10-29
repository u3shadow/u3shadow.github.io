import json
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from build_site import read_posts, verify_baseline


class Document(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.feed(path.read_text(encoding='utf-8'))

    def handle_starttag(self, tag, attributes):
        self.tags.append((tag, dict(attributes)))


class StaticSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.posts = read_posts()
        cls.documents = {p:Document(p) for p in ROOT.rglob('*.html')}
        cls.config = json.loads((ROOT/'data/site.json').read_text(encoding='utf-8'))

    def test_original_215_posts_unchanged(self):
        verify_baseline(self.posts)

    def test_article_and_archive_index_are_complete(self):
        expected = {p['url'] for p in self.posts}
        for name in ['articles', 'archive']:
            links = {a['href'] for t,a in self.documents[ROOT/name/'index.html'].tags if t=='a' and a.get('href','').startswith('/posts/')}
            self.assertEqual(expected, links)

    def test_local_references(self):
        missing = []
        known = set(self.config['knownMissingAssets'])
        for path,document in self.documents.items():
            for tag,a in document.tags:
                value = a.get('href') if tag in ('a','link') else a.get('src') if tag in ('script','img') else None
                if not value or not value.startswith('/') or value.startswith('//'):continue
                url = unquote(urlsplit(value).path)
                target = ROOT/url.lstrip('/')
                if url.endswith('/'):target=target/'index.html'
                if not target.exists() and url not in known:missing.append((str(path.relative_to(ROOT)),url))
        self.assertEqual([], missing)

    def test_all_canonicals_og_and_common_controls(self):
        for path,document in self.documents.items():
            with self.subTest(page=path.relative_to(ROOT)):
                tags = document.tags
                relative = '/' if path==ROOT/'index.html' else '/'+path.parent.relative_to(ROOT).as_posix()+'/'
                canonical = [a['href'] for t,a in tags if t=='link' and a.get('rel')=='canonical']
                self.assertEqual([self.config['url']+relative],canonical)
                self.assertTrue(any(t=='meta' and a.get('property')=='og:title' for t,a in tags))
                self.assertEqual(1, sum(t=='header' for t,a in tags))
                self.assertEqual(1, sum(t=='button' and 'data-theme-toggle' in a for t,a in tags))
                self.assertEqual(1, sum(t=='h1' for t,a in tags))
                for t,a in tags:
                    if t=='img':self.assertNotIn(a.get('alt','').strip(),('', 'undefined','null'))

    def test_contact_not_guessed(self):
        expected = self.config.get('email')
        # Preserve historical article/code links; only public site contacts are managed here.
        addresses = {a['href'].removeprefix('mailto:') for path,d in self.documents.items() if 'posts' not in path.relative_to(ROOT).parts for t,a in d.tags if t=='a' and a.get('href','').startswith('mailto:')}
        self.assertEqual({expected} if expected else set(),addresses)

    def test_index_and_recent_publication_order(self):
        generated = json.loads((ROOT/'data/posts.json').read_text(encoding='utf-8'))
        self.assertEqual([p['id'] for p in self.posts], [p['id'] for p in generated])
        source=(ROOT/'index.html').read_text(encoding='utf-8')
        updates=source.split('<div class="ref-updates">')[1].split('</ul>')[0]
        links=Document.__new__(Document)
        HTMLParser.__init__(links,convert_charrefs=True);links.tags=[];links.feed(updates)
        self.assertEqual([p['url'] for p in self.posts[:5]],[a['href'] for t,a in links.tags if t=='a'])

    def test_sitemap_and_feed(self):
        tree=ET.parse(ROOT/'sitemap.xml');urls=[e.text for e in tree.getroot().iter() if e.tag.endswith('loc')]
        self.assertEqual(221,len(urls))
        self.assertTrue(all(u.startswith(self.config['url']+'/') for u in urls))
        self.assertNotIn('https://u3.github.io',(ROOT/'feed.xml').read_text(encoding='utf-8'))
        self.assertIn(self.config['url']+'/sitemap.xml',(ROOT/'robots.txt').read_text(encoding='utf-8'))

    def test_project_evidence_links_exist(self):
        ids={p['id'] for p in self.posts}
        for p in json.loads((ROOT/'data/projects.json').read_text(encoding='utf-8')):
            self.assertTrue(set(p['sourceIds']) <= ids)
        source=(ROOT/'projects/shaverai/index.html').read_text(encoding='utf-8')
        for section in ['overview','screenshots','implemented','architecture','rules','context','engine','storage','limits','sources']:
            self.assertIn('id="'+section+'"',source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
