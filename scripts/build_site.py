"""Refresh the static export without reimporting, deleting, or renaming posts."""
import argparse
import hashlib
import html
import json
import re
from collections import defaultdict
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / 'tests' / 'post-baseline.json'
VERSION = '20261029-1'
NAV = [('/', '首页'), ('/projects/', '项目'), ('/articles/', '文章'), ('/archive/', '归档'), ('/about/', '关于')]


class Text(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.feed(source)

    def handle_data(self, data):
        self.parts.append(data)

    @property
    def value(self):
        return re.sub(r'\s+', ' ', ' '.join(self.parts)).strip()


class Tag(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.attributes = {}
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        self.attributes = dict(attributes)


def esc(value):
    return html.escape(str(value), quote=True)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding='utf-8') != value:
        path.write_text(value, encoding='utf-8', newline='\n')


def topic_for(title):
    # Conservative display topics, not replacements for original Z-Blog categories.
    rules = [
        ('HarmonyOS', r'鸿蒙|HarmonyOS'),
        ('AI Agent 与 LLM 应用', r'自然语言生成规则|AI Agent|LLM|\bRAG\b'),
        ('开发工具与 IDE 插件', r'插件|AndroidStudio|Android Studio|ADB|adb|IntelliJ'),
        ('机器学习', r'机器学习|神经网络|深度学习|决策树|感知机|支持向量机|朴素贝叶斯'),
        ('性能优化与稳定性', r'性能优化|内存泄漏|卡顿|ANR|崩溃|启动优化'),
        ('Android 工程实践', r'Jenkins|jenkins|cicd|CI/CD|Logger|AspectJ|ASPECTJ|日志|测试体系|Gradle|gradle|混淆|打包'),
        ('Android 架构设计', r'MVVM|MVP|架构|组件化|模块化'),
        ('Android 基础与系统原理', r'Android|android|自定义View|RecyclerView|Activity|Fragment|Jetpack|Kotlin|kotlin'),
        ('个人学习笔记', r'学习笔记|读书笔记|学习版游戏')
    ]
    return next((name for name, pattern in rules if re.search(pattern, title)), '未分类')


def read_posts():
    posts = []
    for path in sorted((ROOT / 'posts').rglob('index.html')):
        source = path.read_text(encoding='utf-8')
        title_match = re.search(r'<h1\b[^>]*class="title"[^>]*>(.*?)</h1>', source, re.S)
        date_match = re.search(r'发布于\s*(\d{4}-\d\d-\d\d \d\d:\d\d)', source)
        article_match = re.search(r'<article\b[^>]*>(.*?)</article>', source, re.S)
        if not all((title_match, date_match, article_match)):
            raise ValueError(f'Missing post metadata: {path}')
        title = Text(title_match.group(1)).value
        article = Text(article_match.group(1)).value
        published = datetime.strptime(date_match.group(1), '%Y-%m-%d %H:%M')
        url = '/' + path.parent.relative_to(ROOT).as_posix() + '/'
        post_id = int(path.parent.name.split('-')[0])
        image_match = re.search(r'<img\b[^>]*src="([^"]+)"', article_match.group(1))
        if not image_match:
            image_match = re.search(r'<img\b[^>]*src="([^"]+)"', source)
        description = article[:155]
        keywords = [term for term in ('Android', 'Kotlin', 'Java', 'Jetpack', 'Room', 'ViewModel', 'RuleEngine', 'HarmonyOS', 'Jenkins', 'ADB', 'Mockito', 'AspectJ', 'Gradle', 'SQL', 'Python', 'LLM', 'RAG') if term.lower() in article.lower()]
        posts.append({
            'id': post_id, 'title': title, 'publishedAt': published.isoformat() + '+08:00',
            'date': published.date().isoformat(), 'year': str(published.year),
            'url': url, 'description': description, 'topic': topic_for(title),
            'keywords': keywords,
            'image': image_match.group(1) if image_match else '/assets/site/banner.png',
            'bodyHash': hashlib.sha256(article.encode()).hexdigest(),
            'estimatedMinutes': max(1, round(len(article) / 450))
        })
    posts.sort(key=lambda p: (p['publishedAt'], p['id']), reverse=True)
    if len(posts) != 215:
        raise ValueError(f'Expected 215 posts, got {len(posts)}')
    return posts


def integrity(posts):
    return {str(p['id']): {key: p[key] for key in ('url', 'title', 'publishedAt', 'bodyHash')} for p in posts}


def verify_baseline(posts):
    if not BASELINE.exists():
        raise ValueError('Capture the baseline before the first build: --capture-baseline')
    previous = json.loads(BASELINE.read_text(encoding='utf-8'))
    if previous != integrity(posts):
        raise ValueError('Post URL, title, publication date or original body text changed. Inspect before building.')


def navigation(active):
    return ''.join(f'<a href="{url}"' + (' class="active" aria-current="page"' if url == active else '') + f'>{title}</a>' for url, title in NAV)


def header(active):
    return f'''<a class="skip-link" href="#main-content">跳至正文</a>
<header><div class="bar"><a class="brand" href="/">u3coding</a>
<nav class="primary-nav" id="primary-navigation" aria-label="主导航">{navigation(active)}</nav>
<div class="header-tools"><a class="icon-button" href="/articles/#search" aria-label="搜索文章" title="搜索文章"><span class="icon icon-search" aria-hidden="true"></span></a>
<button type="button" class="icon-button" data-theme-toggle aria-label="切换浅色主题" title="切换浅色主题"><span class="icon icon-sun" aria-hidden="true"></span></button>
<button type="button" class="icon-button menu-toggle" data-menu-toggle aria-controls="primary-navigation" aria-expanded="false" aria-label="展开导航" title="导航菜单"><span class="icon icon-menu" aria-hidden="true"></span></button></div></div></header>'''


def footer(config):
    return f'''<footer class="ref-footer"><div><strong>u3coding</strong><small>© 2014–2026 u3coding</small></div>
<nav aria-label="页脚导航">{navigation('')}</nav><p><a href="{config['github']}">GitHub</a><a href="/feed.xml">RSS</a><a href="#main-content" aria-label="返回正文顶部">↑</a></p></footer>'''


def contact(config, label='联系我'):
    email = config.get('email')
    return f'<a class="ui-button" href="{esc("mailto:" + email if email else config["github"])}">{label if email else "通过 GitHub 联系"}</a>'


def page(title, body, config, active=''):
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} - u3coding</title></head><body>
{header(active)}<main id="main-content" class="page-shell">{body}</main>{footer(config)}</body></html>'''


def project_url(project, by_id):
    return project.get('url') or by_id[project['sourceIds'][0]]['url']


def project_links(project, by_id):
    links = []
    if project.get('repository'):
        links.append(f'<a href="{esc(project["repository"])}">GitHub 源码</a>')
    for post_id in project['sourceIds']:
        post = by_id[post_id]
        links.append(f'<a href="{esc(post["url"])}">{esc(post["title"])}</a>')
    return '<div class="project-links">' + ''.join(links) + '</div>'


def projects_page(projects, by_id, config):
    cards = []
    notes = []
    for index, project in enumerate(projects):
        tags = ''.join(f'<span>{esc(tag)}</span>' for tag in project['tags'])
        cards.append(f'''<a class="project-card{' featured' if index == 0 else ''}" href="{esc(project_url(project, by_id))}"><span class="project-no">{esc(project['kind'])}</span><h3>{esc(project['name'])}</h3><p>{esc(project['description'])}</p><div class="project-tags">{tags}</div></a>''')
        notes.append(f'''<section class="project-note" id="{project['id']}"><h3>{esc(project['name'])}</h3><p>{esc(project['subtitle'])}</p><dl><dt>背景与问题</dt><dd>{esc(project['background'])}</dd><dt>职责与实现依据</dt><dd>{esc(project['role'])}</dd><dt>关键设计与边界</dt><dd>{esc(project['design'])}</dd></dl>{project_links(project, by_id)}</section>''')
    body = f'''<div class="page-title"><h1>项目作品集</h1><p>Android、AI Agent 与工程实践。项目说明对应源码或技术文章，不使用未经核实的成果数据。</p></div>
<section class="content-sidebar"><div><article class="projects-feature"><div><span class="tag">个人工程原型</span><h2>ShaverAI</h2><p>AI 驱动的 Wi-Fi 场景规则生成与执行</p><p>用自然语言完成环境配置，拆分聊天与指令上下文，通过 Room 保存规则，由独立 RuleEngine 响应 Wi-Fi 变化。</p><a class="ui-button" href="/projects/shaverai/">查看项目详情 →</a></div><div class="hero-device"><img src="/assets/images/711-ai-config.webp" alt="ShaverAI 自然语言配置实际截图"><img src="/assets/images/711-original-config.webp" alt="原版手工配置实际截图"></div></article>
<div class="section-heading" style="margin-top:30px"><h2>项目与工程实践</h2></div><div class="all-projects">{''.join(cards)}</div>
<section class="project-proof"><h2>实现依据与技术细节</h2>{''.join(notes)}</section></div>
<aside class="sidebar"><section class="ui-card"><h3>技术方向</h3><p>Android 架构、工程工具、稳定性与 AI 应用工程化。</p><a class="text-link" href="/about/">了解我的技术背景 →</a></section><section class="ui-card"><h3>技术交流</h3><p>源码、设计取舍和实现过程，均可通过项目文章进一步了解。</p>{contact(config)}</section></aside></section>'''
    return page('项目作品集', body, config, '/projects/')


def shaver_page(by_id, config):
    post = by_id[711]
    body = f'''<div class="detail-intro"><div><span class="tag">个人工程原型 · Android + AI</span><h1>ShaverAI</h1><h2>Wi-Fi 场景规则生成与执行</h2><p>把音量、亮度、蓝牙等场景配置从表单升级为自然语言。重点不是做一个聊天壳，而是让输入分流、结构化规则、持久化和环境触发形成闭环。</p><div class="project-links"><a class="ui-button" href="https://github.com/u3shadow/ShaverAI">查看源码</a><a class="text-link" href="{post['url']}">阅读重构实录 →</a></div></div><img src="/assets/images/711-cover.webp" alt="ShaverAI 原文项目概览，包含自然语言输入和规则执行流程"></div>
<div class="content-sidebar"><div class="detail-content">
<section id="overview"><h2>项目介绍</h2><p>最初的工具通过表单选择 Wi-Fi 及设备动作。重构后，用户可以用一句自然语言描述场景，由模型生成可解析的规则，再由本地执行链处理。</p><p class="detail-note">以下实现说明以 2026-04-22 发布的重构文章为依据，不代表仓库的最新状态。首页设备界面是概念展示，不作为日志分析或性能诊断已实现的证据。</p></section>
<section id="screenshots"><h2>实际应用截图</h2><div class="screenshot-gallery"><figure><img src="/assets/images/711-original-config.webp" alt="原版手工配置：亮度、音量、蓝牙等开关和数值"><figcaption>原版：手工选择设备配置</figcaption></figure><figure><img src="/assets/images/711-ai-config.webp" alt="AI 配置：聊天输入、Wi-Fi 状态和结构化音量规则"><figcaption>AI 化后：自然语言生成规则</figcaption></figure></div></section>
<section id="implemented"><h2>已实现的核心能力</h2><ul><li>接收文本输入并区分普通聊天与指令聊天。</li><li>为不同业务链维护独立上下文与 prompt。</li><li>从模型回复解析结构化 JSON 规则。</li><li>使用 Room 保存规则，支持重启后读取。</li><li>根据 Wi-Fi 变化查询、去重并执行规则，再更新界面。</li><li>通过独立能力说明 prompt 限定普通聊天的产品边界。</li></ul></section>
<section id="architecture"><h2>技术架构</h2><pre><code class="language-mermaid">flowchart TD
  UI[MainActivity 输入与环境事件] --> VM[ChatViewModel]
  VM --> Classifier[InputClassifier]
  Classifier --> Normal[NormalChatContextManager]
  Classifier --> Command[CommandChatContextManager]
  Normal --> Prompt[PromptBuilder]
  Command --> Prompt
  Prompt --> Model[模型流式回复]
  Model --> Parse[解析结构化规则]
  Parse --> Repo[RuleRepo / Room]
  UI --> Engine[RuleEngine.run ssid]
  Engine --> Repo
  Engine --> Executor[ActionExecutor]
  Executor --> Result[环境状态与执行反馈]</code></pre></section>
<section id="rules"><h2>自然语言规则生成流程</h2><p>输入需求 → 输入分类 → 指令上下文与 prompt → 流式回复 → JSON 提取与解析 → 构造 Action → 保存规则。模型输出不是执行完成的证明，规则执行由本地链路承担。</p><p>例如，原文使用连接公司 Wi-Fi 后静音的场景，规则包含 <code>trigger</code>、<code>operation</code> 和 <code>params</code>。这里不增加原文没有证明的 RAG 或多工具规划能力。</p></section>
<section id="context"><h2>输入分类与上下文管理</h2><p><code>InputClassifier</code> 使用规则将输入分流；普通聊天和指令聊天分别由 <code>NormalChatContextManager</code> 与 <code>CommandChatContextManager</code> 维护。原文记录的窗口分别为最近 10 条普通消息和 6 条指令相关消息。</p><p>拆分上下文是为了避免日常聊天污染规则 prompt，也使两种交互可以分别演进。当前分类仍是简单规则，不包装成已训练的意图识别模型。</p></section>
<section id="engine"><h2>RuleEngine 执行机制</h2><p><code>MainActivity</code> 获取当前 SSID 后调用 <code>RuleEngine.run(ssid)</code>。引擎从仓库读取匹配规则、去重并执行，再通过 <code>updateEnvFromRuleResult</code> 与 <code>onRuleRunResult</code> 同步状态。</p><p>将运行引擎独立出来，使执行不再依赖用户点击发送消息。设备权限和系统限制仍需结合实际 Android 环境验证。</p></section>
<section id="storage"><h2>Room 持久化设计</h2><p><code>RuleRepo.init(context)</code> 通过 <code>Room.databaseBuilder</code> 创建 <code>rule_store.db</code>。<code>addRule(action)</code> 调用 DAO 的 <code>upsert</code>，<code>getRules(ssid)</code> 按触发条件读取并转换为 Action。</p><p>这让规则不再只是内存状态。原文章未展示数据库迁移策略、压力测试或大规模数据指标，因此不作对应成果声明。</p></section>
<section id="limits"><h2>当前局限与后续计划</h2><ul><li>规则编辑、删除和覆盖策略的 UI，列为后续完善方向。</li><li>输入分类需要更细粒度设计。</li><li>日志与可观测性需要系统化建设。</li><li>消息模式建模和更多系统工具模块，属于后续扩展。</li></ul><p>日志分析、性能诊断、设备洞察、完整知识库检索和多工具编排，目前不列入已验证能力。没有可复核的性能测试数据，因此不展示成功率、提效百分比或响应时延。</p></section>
<section id="sources"><h2>源码与技术文章</h2><div class="project-links"><a href="https://github.com/u3shadow/ShaverAI">ShaverAI GitHub 仓库</a><a href="{post['url']}">{esc(post['title'])}</a></div></section>
</div><aside class="sidebar"><section class="ui-card"><h3>项目索引</h3><p>Android · Kotlin · Room · JSON 规则</p><p>实现依据：2026-04-22 重构实录</p><a class="text-link" href="/projects/">← 返回全部项目</a></section><section class="ui-card"><h3>页面目录</h3><div class="detail-nav">{''.join(f'<p><a href="#{key}">{name}</a></p>' for key,name in [('overview','项目介绍'),('screenshots','实际截图'),('implemented','已实现能力'),('architecture','技术架构'),('rules','规则生成'),('context','上下文管理'),('engine','RuleEngine'),('storage','Room 持久化'),('limits','局限与计划'),('sources','源码与文章')])}</div></section></aside></div>'''
    return page('ShaverAI 项目详情', body, config, '/projects/')


def about_page(by_id, config):
    project_list = ''.join(f'<li><a class="text-link" href="{url}">{name}</a>：{description}</li>' for url,name,description in [
        ('/projects/shaverai/','ShaverAI','从自然语言配置到 Room 规则存储和 Wi-Fi 触发执行的工程原型。'),
        (by_id[691]['url'],'RemoveButterKnife','Android Studio 插件、Java PSI 代码改写和旧代码迁移。'),
        (by_id[697]['url'],'RemoteADB','ROOT 测试机无线 ADB 启动与设备端命令执行。')])
    email_note = f'<p>Email：<a href="mailto:{esc(config["email"])}">{esc(config["email"])}</a></p>' if config.get('email') else '<p>联系邮箱正在确认，暂通过 GitHub 交流。</p>'
    body = f'''<div class="about-wrap"><section class="about-hero"><p class="eyebrow">关于我</p><h1>高级 Android 工程师<br>关注 Android + AI Agent 应用工程化</h1><p>拥有 8 年以上 Android 开发经验，擅长架构设计、性能优化、稳定性建设和工程工具开发。希望把实际问题拆解为可维护、可验证的工程方案。</p>
<section><h2>核心技术能力</h2><div class="about-grid"><div class="about-chip"><strong>Android 工程</strong>架构设计、分层测试、性能与稳定性、应用维护。</div><div class="about-chip"><strong>工具与自动化</strong>Android Studio 插件、PSI 代码处理、ADB 与 CI/CD 实践。</div><div class="about-chip"><strong>AI 应用工程化</strong>输入分类、上下文隔离、结构化输出、本地规则执行与存储。</div></div></section>
<section><h2>代表性项目</h2><ul>{project_list}</ul><a class="text-link" href="/projects/">查看实现依据和技术文章 →</a></section>
<section><h2>工程实践方向</h2><p>持续关注业务逻辑的可测试性、用户操作路径与本地日志，以及将重复开发操作转化为工具。当前研究重点是 Android 与 AI Agent 的结合，并拓展 HarmonyOS 应用开发能力。</p></section>
<section><h2>技术积累</h2><ul><li>2014 年起：保留 Android 基础、系统原理与学习笔记。</li><li>后续实践：插件开发、架构测试、日志与操作路径追踪、Jenkins CI/CD。</li><li>近期探索：HarmonyOS 应用问题处理、AI 辅助开发及 Android 场景规则原型。</li></ul><p>这些方向以公开文章为依据，不代表公司任职时间线。</p><a class="text-link" href="/archive/">浏览全部 215 篇历史文章 →</a></section>
<section><h2>求职与技术交流</h2><p>关注高级 Android 工程岗位，以及 Android + AI 应用工程化相关机会。欢迎从项目源码、技术文章和具体设计取舍展开交流。</p>{contact(config)}</section></section>
<aside class="contact-panel"><h2 class="profile-name">u3</h2><p>高级 Android 工程师<br>Android · AI 应用工程化</p><p><a class="text-link" href="{config['github']}">GitHub / u3shadow</a></p>{email_note}<p>215 篇技术文章，保留原有发布时间与历史内容。</p>{contact(config)}</aside></div>'''
    return page('关于我', body, config, '/about/')


def articles_page(posts, config, archive=False):
    years = sorted({p['year'] for p in posts}, reverse=True)
    topics = sorted({p['topic'] for p in posts})
    options = lambda values: ''.join(f'<option value="{esc(value)}">{esc(value)}</option>' for value in values)
    controls = f'''<form class="search-controls" role="search" onsubmit="return false"><label for="search">关键词<input id="search" type="search" data-post-search placeholder="标题、摘要或技术关键词" autocomplete="off"></label><label for="year-filter">年份<select id="year-filter" data-post-filter="year"><option value="">全部年份</option>{options(years)}</select></label><label for="topic-filter">主题<select id="topic-filter" data-post-filter="topic"><option value="">全部主题</option>{options(topics)}</select></label><button class="plain-button" type="button" data-clear-search>清除筛选</button></form><p class="filter-status" data-post-status role="status" aria-live="polite">共 215 篇文章</p><p data-post-empty hidden>没有匹配的文章，请尝试其他关键词或筛选条件。</p>'''
    groups = defaultdict(list)
    for post in posts:
        search_text = esc((' '.join([post['title'], post['description'], post['topic'], *post['keywords']])).lower())
        groups[post['year']].append(f'''<li data-post-item data-year="{post['year']}" data-topic="{esc(post['topic'])}" data-search="{search_text}"><time datetime="{post['publishedAt']}">{post['date'][5:]}</time><a href="{esc(post['url'])}">{esc(post['title'])}</a><span class="post-topic">{esc(post['topic'])}</span></li>''')
    sections = ''.join(f'<section class="archive-list" data-year-group><h2 id="year-{year}">{year} <small>· {len(groups[year])} 篇</small></h2><ul>{"".join(groups[year])}</ul></section>' for year in years)
    title = '归档' if archive else '技术文章'
    featured = ''.join(f'<a href="{esc(p["url"])}">{esc(p["title"])}</a>' for p in posts if p['id'] in config['featuredPostIds'])
    body = f'''<div class="page-title"><h1>{title}</h1><p>全部 215 篇文章，按真实发布时间倒序保存。主题仅对明确内容作保守标注，未改变原文章分类。</p></div><div class="featured-links"><strong>精选阅读</strong>{featured}</div>{controls}<div class="article-index-list">{sections}</div>'''
    return page(title, body, config, '/archive/' if archive else '/articles/')


def update_home(source, posts, projects, config):
    by_id = {p['id']: p for p in posts}
    source = source.replace('8+ 年 Android 开发经验，专注 AI 应用工程化、工程工具链、性能优化与稳定性保障，致力于把复杂能力做成可复用的产品化方案。', '8 年以上 Android 开发经验，擅长架构设计、性能优化、稳定性建设与工程工具。当前聚焦自然语言驱动的 Android 场景规则，让 AI 输出进入可持久化、可执行的工程链路。')
    source = re.sub(r'<div class="ref-stats">.*?</div>\s*</div>\s*</div>', '<div class="ref-stats"><div><i>▣</i><strong>215</strong><span>技术文章</span></div><div><i>♡</i><strong>8+</strong><span>年 Android 经验</span></div><div><i>▢</i><strong>Android</strong><span>架构与工程工具</span></div><div><i>☆</i><strong>AI Agent</strong><span>当前研究方向</span></div></div></div>', source, count=1, flags=re.S)
    # Keep the approved device composition; label it as a concept, not a real screenshot.
    stage = '''<div class="ref-app-stage" aria-label="ShaverAI 概念界面，实际截图见项目详情">
<div class="ref-desktop"><aside><b>◉ ShaverAI</b><span class="on">◉ Overview</span><span>◌ Chat</span><span>⌘ Rules</span><span>▧ Prompts</span><span>◇ Storage</span><span>⚙ Settings</span></aside>
<section><div class="app-top">场景规则 <small>⌕　＋</small></div><div class="app-metrics"><b>普通聊天</b><b>输入分类</b><b>指令上下文</b><b>规则持久化</b><b>规则生成</b><b>环境执行</b></div><div class="app-list"><strong>场景示例</strong><span>公司 Wi-Fi：静音</span><span>为当前环境保存配置</span><span>读取已保存的场景规则</span></div></section>
<section class="app-chat"><div class="app-top">规则生成</div><p class="bot">连接公司 Wi-Fi 后静音，蓝牙保持开启。</p><p class="bot">解析结构化规则<br>通过 Room 持久化<br>由 RuleEngine 执行</p><div class="chat-input">输入场景需求 <b>↑</b></div></section></div>
<div class="ref-phone"><b>ShaverAI</b><small>场景规则</small><p>Wi-Fi 环境配置</p><span>▣ 普通聊天</span><span>◌ 输入分流</span><span>◇ 上下文管理</span><span>⌘ 规则生成</span><span>▧ 环境状态</span><i>＋</i></div>
<p class="concept-label">概念界面 · <a href="/projects/shaverai/#screenshots">查看实际截图</a></p></div>
</section><section class="ref-section">'''
    source = re.sub(r'<div class="ref-app-stage".*?</section>\s*<section class="ref-section">', lambda _: stage, source, count=1, flags=re.S)
    cards = []
    for project in projects[:3]:
        tags = ''.join(f'<i>{esc(t)}</i>' for t in project['tags'])
        cards.append(f'<a class="ref-project {project["id"]}" href="{esc(project_url(project, by_id))}"><div class="project-banner"><b>{project["symbol"]}</b><span><strong>{esc(project["name"])}</strong><small>{esc(project["subtitle"])}</small></span></div><p>{esc(project["description"])}</p><footer>{tags}</footer></a>')
    source = re.sub(r'(<div class="ref-project-grid">).*?(</div></section>)', lambda m:m[1]+''.join(cards)+m[2], source, count=1, flags=re.S)
    featured = []
    for post_id in config['featuredPostIds']:
        p = by_id[post_id]
        image = config.get('featuredImages', {}).get(str(post_id), p['image'])
        featured.append(f'<a href="{esc(p["url"])}"><img src="{esc(image)}" alt="{esc(p["title"])}" loading="lazy"><div><b>{esc(p["title"])}</b><p>{esc(p["topic"])}</p><small>{p["date"]} · 约 {p["estimatedMinutes"]} 分钟阅读</small></div></a>')
    source = re.sub(r'(<div class="ref-post-grid">).*?(</div></section>)', lambda m:m[1]+''.join(featured)+m[2], source, count=1, flags=re.S)
    updates = ''.join(f'<li><a href="{esc(p["url"])}">{esc(p["title"])}</a><time datetime="{p["publishedAt"]}">{p["date"]}</time></li>' for p in posts[:5])
    source = re.sub(r'(<div class="ref-updates"><h2>最近更新</h2><ul>).*?(</ul>)', lambda m:m[1]+updates+m[2], source, count=1, flags=re.S)
    source = re.sub(r'<a href="mailto:[^"]+" aria-label="Email">.*?</a>', f'<a href="{config["github"]}" aria-label="通过 GitHub 联系" title="通过 GitHub 联系">@</a>', source)
    return source


def shared_html(source, path, config):
    rel = path.relative_to(ROOT).as_posix()
    url = '/' if rel == 'index.html' else '/' + path.parent.relative_to(ROOT).as_posix() + '/'
    active = '/articles/' if url.startswith('/posts/') else '/projects/' if url.startswith('/projects/') else url
    source = re.sub(r'<header\b.*?</header>', lambda _: header(active).split('</a>\n',1)[-1], source, count=1, flags=re.S)
    source = re.sub(r'<a class="skip-link"[^>]*>.*?</a>\s*', '', source)
    source = re.sub(r'(<body[^>]*>)', r'\1<a class="skip-link" href="#main-content">跳至正文</a>', source, count=1)
    source = re.sub(r'<main\b[^>]*>', lambda m: re.sub(r'\s+id="[^"]*"','',m[0][:-1]) + ' id="main-content">', source, count=1)
    # Only replace the final page footer; homepage project cards also use footer elements.
    source = re.sub(r'(?<=</main>)\s*<footer\b.*?</footer>', lambda _: '\n'+footer(config), source, count=1, flags=re.S)
    if '<!-- site-common -->' in source:
        source = re.sub(r'<!-- site-common -->.*?<!-- /site-common -->', '', source, flags=re.S)
    source = re.sub(r'<link\b[^>]*rel="canonical"[^>]*>\s*', '', source)
    source = re.sub(r'<meta\b[^>]*property="og:[^"]+"[^>]*>\s*', '', source)
    source = re.sub(r'<script type="module">\s*import mermaid.*?</script>', '', source, flags=re.S)
    source = re.sub(r'<link rel="stylesheet" href="/assets/site/editorial-portfolio.css[^\"]*">', f'<link rel="stylesheet" href="/assets/site/editorial-portfolio.css?v={VERSION}">', source)
    if '/assets/site/editorial-portfolio.css' not in source:
        source = source.replace('</head>', f'<link rel="stylesheet" href="/assets/site/editorial-portfolio.css?v={VERSION}"></head>')
    title = Text(re.search(r'<title>(.*?)</title>',source,re.S)[1]).value
    def image_alt(match):
        raw = match[0]
        attributes = Tag(raw).attributes
        if attributes.get('alt', '').strip() not in ('', 'undefined', 'null'):
            return raw
        raw = re.sub(r'''\s+alt\s*=\s*(?:"[^"]*"|'[^']*')''', '', raw, flags=re.I)
        return raw[:-1] + f' alt="{esc("文章配图：" + title.removesuffix(" - u3coding"))}">'
    source = re.sub(r'<img\b[^>]*>', image_alt, source, flags=re.I)
    def safe_external(match):
        raw = match[0]
        attributes = Tag(raw).attributes
        if attributes.get('target') != '_blank': return raw
        rel = set((attributes.get('rel') or '').split()) | {'noopener', 'noreferrer'}
        raw = re.sub(r'''\s+rel\s*=\s*(?:"[^"]*"|'[^']*')''', '', raw, flags=re.I)
        return raw[:-1] + f' rel="{esc(" ".join(sorted(rel)))}">'
    source = re.sub(r'<a\b[^>]*>', safe_external, source, flags=re.I)
    def local_image_link(match):
        opening, image, closing = match.groups()
        href = Tag(opening).attributes.get('href', '')
        src = Tag(image).attributes.get('src', '')
        if urlsplit(href).hostname not in ('www.u3blog.xyz', 'u3blog.xyz'):
            return match[0]
        if not src.startswith('/assets/') or not (ROOT/src.lstrip('/')).is_file():
            return match[0]
        opening = re.sub(r'''\bhref\s*=\s*(?:"[^"]*"|'[^']*')''', f'href="{esc(src)}"', opening, count=1, flags=re.I)
        return opening + image + closing
    source = re.sub(r'(<a\b[^>]*>)\s*(<img\b[^>]*>)\s*(</a>)', local_image_link, source, flags=re.I)
    if url.startswith('/posts/'):
        def article_headings(match):
            return re.sub(r'<(/?)h1\b', r'<\1h2', match[0])
        source = re.sub(r'<article\b[^>]*>.*?</article>', article_headings, source, flags=re.S)
    desc_match = re.search(r'<meta name="description" content="([^"]*)"',source)
    description = Text(html.unescape(desc_match[1])).value if desc_match else config['description']
    descriptions = {
        '/': config['description'],
        '/projects/': 'ShaverAI、RemoveButterKnife、RemoteADB 与 Android 工程实践，包含实现范围、设计取舍、源码和技术文章。',
        '/projects/shaverai/': 'ShaverAI：AI 驱动的 Wi-Fi 场景规则生成与执行原型，包含实际截图、输入分流、上下文管理、RuleEngine 和 Room 持久化设计。',
        '/about/': 'u3，高级 Android 工程师，拥有 8 年以上开发经验，关注 Android 架构、稳定性、工程工具及 AI Agent 应用工程化。',
        '/articles/': 'u3coding 全部 215 篇技术文章，涵盖 Android、开发工具、工程实践、AI 应用与 HarmonyOS。',
        '/archive/': 'u3coding 从 2014 年至今的 215 篇技术文章归档，保留原始发布时间和文章链接。'
    }
    if url in descriptions:
        description = descriptions[url]
        if desc_match:
            source = source[:desc_match.start()] + re.sub(r'content="[^"]*"', f'content="{esc(description)}"', desc_match[0]) + source[desc_match.end():]
    if not desc_match:
        source = source.replace('</head>', f'<meta name="description" content="{esc(description)}"></head>')
    common = f'''<!-- site-common -->
<link rel="canonical" href="{esc(config['url']+url)}">
<meta property="og:type" content="{'article' if url.startswith('/posts/') else 'website'}">
<meta property="og:site_name" content="u3coding"><meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(config['url']+url)}">
<meta property="og:image" content="{config['url']}/assets/site/banner.png">
<script>document.documentElement.classList.add('js');try{{document.documentElement.dataset.theme=localStorage.getItem('u3-theme')==='light'?'light':'dark'}}catch{{document.documentElement.dataset.theme='dark'}}</script>
<link rel="stylesheet" href="/assets/site/site-theme.css?v={VERSION}">
<script defer src="/assets/site/site.js?v={VERSION}"></script>
{'<script type="module" src="/assets/site/diagrams.js?v='+VERSION+'"></script>' if 'language-mermaid' in source else ''}
<!-- /site-common -->'''
    source = re.sub(r'\s*</head>', lambda _: '\n'+common+'\n</head>', source, count=1)
    return source


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--capture-baseline', action='store_true')
    args = parser.parse_args()
    config = json.loads((ROOT/'data/site.json').read_text(encoding='utf-8'))
    projects = json.loads((ROOT/'data/projects.json').read_text(encoding='utf-8'))
    posts = read_posts()
    if args.capture_baseline:
        if BASELINE.exists():
            raise ValueError('Baseline already exists; never overwrite silently.')
        save(BASELINE, json.dumps(integrity(posts), ensure_ascii=False, indent=2)+'\n')
        print('Captured 215 original post signatures; no page changed.')
        return
    verify_baseline(posts)
    by_id = {p['id']:p for p in posts}
    for project in projects:
        for post_id in project['sourceIds']:
            if post_id not in by_id: raise ValueError(f'Unknown evidence post: {post_id}')
    save(ROOT/'projects/index.html', projects_page(projects, by_id, config))
    save(ROOT/'projects/shaverai/index.html', shaver_page(by_id, config))
    save(ROOT/'about/index.html', about_page(by_id, config))
    save(ROOT/'articles/index.html', articles_page(posts, config))
    save(ROOT/'archive/index.html', articles_page(posts, config, archive=True))
    save(ROOT/'index.html', update_home((ROOT/'index.html').read_text(encoding='utf-8'), posts, projects, config))
    for path in sorted(ROOT.rglob('*.html')):
        if '.git' not in path.parts:
            save(path, shared_html(path.read_text(encoding='utf-8'), path, config))
    save(ROOT/'data/posts.json', json.dumps([{k:v for k,v in p.items() if k!='bodyHash'} for p in posts],ensure_ascii=False,indent=2)+'\n')
    # Keep all original RSS dates and bodies; only repair the mistaken host.
    feed=ROOT/'feed.xml'
    save(feed, feed.read_text(encoding='utf-8').replace('https://u3.github.io',config['url']))
    ET.register_namespace('', 'http://www.sitemaps.org/schemas/sitemap/0.9')
    ns='{http://www.sitemaps.org/schemas/sitemap/0.9}'
    sitemap=ET.Element(ns+'urlset')
    for url in [p[0] for p in NAV]+['/projects/shaverai/']+[p['url'] for p in posts]:
        entry=ET.SubElement(sitemap,ns+'url');ET.SubElement(entry,ns+'loc').text=config['url']+url
    save(ROOT/'sitemap.xml',ET.tostring(sitemap,encoding='unicode',xml_declaration=True)+'\n')
    save(ROOT/'robots.txt',f'User-agent: *\nAllow: /\nSitemap: {config["url"]}/sitemap.xml\n')
    verify_baseline(read_posts())
    print(f'Built {len(posts)} posts and 6 site pages. Original text, titles, dates and URLs verified.')


if __name__ == '__main__':
    main()
