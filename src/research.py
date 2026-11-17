"""Fetch traceable sources from Wikipedia and, when useful, Open Library."""
import datetime
import html
import json
import re
import time
import urllib.parse
import urllib.request

PINYIN_NAME_CHARS={
    'yu':['瑜','玉','雨','宇','羽','妤','语','禹','钰'],
    'wen':['文','雯','闻','玟'],
    'yi':['怡','仪','依','艺','逸','毅','伊'],
    'xin':['欣','心','昕','馨'],
    'jia':['佳','嘉','家','加'],
    'xuan':['萱','轩','璇','宣']
}
NAME_HOMOPHONES={'宛':['婉'],'婉':['宛'],'佳':['嘉'],'嘉':['佳'],'轩':['萱'],'萱':['轩']}

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

def rank_sources(sources, query, is_book, candidates=(), prefer_best=False):
    keys=[re.sub(r'\s+','',x).casefold() for x in (query,*candidates) if x]
    unrelated=('电视剧','電視劇','韓國電視劇','漫画','漫畫','专辑','專輯')
    def score(source):
        title=re.sub(r'\s+','',source['title']).casefold()
        snippet=source.get('snippet','').casefold()
        title_points=max((12 if title==key else 0)+(8 if key in title else 0) for key in keys) if keys else 0
        snippet_points=max((5 if key in re.sub(r'\s+','',snippet) else 0) for key in keys) if keys else 0
        points=title_points+snippet_points
        if is_book and any(word in snippet for word in ('小说','小說','小説','novel','著者')): points+=7
        if is_book and source['url'].startswith('https://openlibrary.org/works/'): points+=8
        if any(word in source['title']+' '+snippet for word in unrelated): points-=20
        if '消歧義' in source['title'] or '消歧义' in source['title']: points-=15
        return points
    ranked=sorted(sources,key=score,reverse=True)
    if prefer_best and ranked:
        candidate_keys={re.sub(r'\s+','',x).casefold() for x in (query,*candidates)}
        exact=[s for s in ranked if re.sub(r'\s+','',s['title']).casefold() in candidate_keys]
        if exact:
            return exact[:3]
        best=score(ranked[0])
        ranked=[s for s in ranked if score(s)>0 and score(s)>=best-2][:3]
    ranked=[s for s in ranked if score(s)>0]
    return ranked

def spelling_suggestions(query):
    """Use public search autocomplete only to expand queries, never as a citation."""
    params=urllib.parse.urlencode({'client':'firefox','hl':'zh-CN','q':query})
    try:
        result=fetch_json('https://suggestqueries.google.com/complete/search?'+params,timeout=8,attempts=1)
    except (OSError,ValueError):
        return []
    suggestions=result[1] if isinstance(result,list) and len(result)>1 and isinstance(result[1],list) else []
    output=[]
    for suggestion in suggestions:
        cleaned=re.sub(r'\s*(是谁|是什么|歌词|扮演者|演员|老师|介绍|百科|图片|视频|爱情公寓|篮球|伴奏).*$','',suggestion).strip()
        if cleaned and cleaned.casefold()!=query.casefold() and cleaned not in output:
            output.append(cleaned)
    return output[:5]

def expand_name_candidates(query, suggestions):
    candidates=[]
    for base in suggestions:
        candidates.append(base)
        for index,char in enumerate(base):
            for replacement in NAME_HOMOPHONES.get(char,[]):
                candidates.append(base[:index]+replacement+base[index+1:])
    mixed=re.fullmatch(r'([\u3400-\u9fff]+)([A-Za-z]+)',query)
    if mixed:
        prefix,suffix=mixed.groups()
        for char in PINYIN_NAME_CHARS.get(suffix.casefold(),[]):
            candidates.append(prefix+char)
    for base in tuple(candidates):
        for index,char in enumerate(base):
            for replacement in NAME_HOMOPHONES.get(char,[]):
                candidates.append(base[:index]+replacement+base[index+1:])
    result=[]
    for candidate in candidates:
        if candidate and candidate.casefold()!=query.casefold() and candidate not in result:
            result.append(candidate)
    return result[:8]

def search_sources(topic):
    if not topic or not topic.strip():
        raise ResearchError('请输入知识主题')
    core,is_book=extract_search_query(topic)
    items=[]
    suggestions=spelling_suggestions(core)
    candidates=expand_name_candidates(core,suggestions)
    queries=[core]+candidates[:5]
    wiki_failures=0
    languages=['zh']
    if not re.search(r'[\u3400-\u9fff]',core):
        languages.append('en')
    for candidate in queries:
        for language in languages:
            query=urllib.parse.urlencode({'action':'query','list':'search','srsearch':candidate,'srlimit':5,'format':'json','utf8':1})
            try:
                raw=fetch_json(f'https://{language}.wikipedia.org/w/api.php?{query}',attempts=2)
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
        ranked=rank_sources(unique,core,is_book,candidates,prefer_best=bool(candidates))
        if ranked:
            return ranked[:8]
    if wiki_failures==len(languages) and (is_book or not items):
        raise ResearchError('公开资料网站暂时无法连接，请检查网络后重试。')
    raise ResearchError(f'没有找到“{core}”的相关资料。请尝试更短的主题关键词，或检查网络连接。')
