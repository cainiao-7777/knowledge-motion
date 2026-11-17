"""Fetch traceable sources from Wikipedia and, when useful, Open Library."""
import datetime
import html
import json
import re
import time
import urllib.parse
import urllib.request

class ResearchError(RuntimeError):
    pass

def extract_search_query(topic):
    """Remove presentation instructions and prefer an explicitly quoted title."""
    text=topic.strip()
    quoted=re.findall(r'[《「『“"]([^》」』”"]+)[》」』”"]',text)
    if quoted:
        return quoted[0].strip(), True
    text=re.sub(r'^(请)?(用.{0,12}?(方式|风格)?|帮我)?(讲明白|讲解|解释|介绍|科普|制作|生成|做一个|做条|做一条|讲一下)?','',text)
    text=re.sub(r'(为什么|为何|怎么|如何|怎样|是什么|什么是).*$','',text)
    text=re.sub(r'(这本书|这部书|这本小说|这个概念|这个主题|相关知识|知识视频)$','',text)
    text=re.sub(r'[《》「」『』“”"，。！？、：；]', ' ', text)
    text=' '.join(text.split()).strip()
    return (text or topic.strip()), bool(re.search(r'(书|小说|著作|作者)',topic))

def fetch_json(url, timeout=18, attempts=3):
    last_error=None
    for attempt in range(attempts):
        request=urllib.request.Request(url,headers={'User-Agent':'KnowledgeMotion/0.1 (educational student project)'})
        try:
            with urllib.request.urlopen(request,timeout=timeout) as response:
                return json.load(response)
        except (OSError,ValueError) as exc:
            last_error=exc
            if attempt+1<attempts:
                time.sleep(0.4*(attempt+1))
    raise last_error

def normalize_results(results):
    output=[]
    for item in results:
        url=item.get('url','')
        parsed=urllib.parse.urlparse(url)
        if parsed.scheme != 'https' or not parsed.netloc or not item.get('title'):
            continue
        output.append({'title':item['title'],'url':url,'snippet':item.get('snippet',''), 'accessed':datetime.date.today().isoformat()})
    return output

def rank_sources(sources, query, is_book):
    key=re.sub(r'\s+','',query).casefold()
    unrelated=('电视剧','電視劇','韓國電視劇','漫画','漫畫','专辑','專輯')
    def score(source):
        title=re.sub(r'\s+','',source['title']).casefold()
        snippet=source.get('snippet','').casefold()
        points=12 if title==key else 0
        if key and key in title: points+=8
        if key and key in re.sub(r'\s+','',snippet): points+=5
        if is_book and any(word in snippet for word in ('小说','小說','小説','novel','著者')): points+=7
        if is_book and source['url'].startswith('https://openlibrary.org/works/'): points+=8
        if any(word in source['title']+' '+snippet for word in unrelated): points-=20
        if '消歧義' in source['title'] or '消歧义' in source['title']: points-=15
        return points
    ranked=sorted(sources,key=score,reverse=True)
    if is_book:
        ranked=[s for s in ranked if score(s)>0]
    return ranked

def search_sources(topic):
    if not topic or not topic.strip():
        raise ResearchError('请输入知识主题')
    core,is_book=extract_search_query(topic)
    items=[]
    wiki_failures=0
    languages=['zh']
    if not re.search(r'[\u3400-\u9fff]',core):
        languages.append('en')
    for language in languages:
        query=urllib.parse.urlencode({'action':'query','list':'search','srsearch':core,'srlimit':5,'format':'json','utf8':1})
        try:
            raw=fetch_json(f'https://{language}.wikipedia.org/w/api.php?{query}')
            for item in raw['query']['search']:
                title=item['title']
                snippet=html.unescape(re.sub(r'<[^>]*>','',item.get('snippet','')))
                url=f'https://{language}.wikipedia.org/wiki/'+urllib.parse.quote(title.replace(' ','_'))
                items.append({'title':title,'url':url,'snippet':snippet,'source':'Wikipedia'})
        except (OSError, ValueError, KeyError):
            wiki_failures+=1

    # Long prompts and book titles are often poorly covered by an encyclopedia
    # search, so add catalog metadata instead of treating a weak search as empty.
    if is_book or len(items)<3:
        try:
            params=urllib.parse.urlencode({'title':core,'limit':5})
            catalog=fetch_json('https://openlibrary.org/search.json?'+params,timeout=15)
            for record in catalog.get('docs',[]):
                title=record.get('title')
                key=record.get('key')
                if not title or not key:
                    continue
                authors=', '.join(record.get('author_name',[])[:2])
                year=record.get('first_publish_year')
                detail='；'.join(x for x in (f'作者：{authors}' if authors else '',f'首版年份：{year}' if year else '') if x)
                items.append({'title':title,'url':'https://openlibrary.org'+key,'snippet':detail,'source':'Open Library'})
        except (OSError,ValueError,KeyError):
            pass

    sources=normalize_results(items)
    unique=[]
    seen=set()
    for source in sources:
        identity=(source['title'].casefold(),source['url'])
        if identity not in seen:
            unique.append(source);seen.add(identity)
    if unique:
        ranked=rank_sources(unique,core,is_book)
        if ranked:
            return ranked[:8]
    if wiki_failures==len(languages) and (is_book or not items):
        raise ResearchError('公开资料网站暂时无法连接，请检查网络后重试。')
    raise ResearchError(f'没有找到“{core}”的相关资料。请尝试更短的主题关键词，或检查网络连接。')
