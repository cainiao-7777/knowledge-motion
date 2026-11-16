"""Fetch traceable knowledge sources from Wikipedia's public search API."""
import datetime
import html
import json
import re
import urllib.parse
import urllib.request

class ResearchError(RuntimeError):
    pass

def normalize_results(results):
    output=[]
    for item in results:
        url=item.get('url','')
        parsed=urllib.parse.urlparse(url)
        if parsed.scheme != 'https' or not parsed.netloc or not item.get('title'):
            continue
        output.append({'title':item['title'],'url':url,'snippet':item.get('snippet',''), 'accessed':datetime.date.today().isoformat()})
    return output

def search_sources(topic):
    if not topic or not topic.strip():
        raise ResearchError('请输入知识主题')
    query=urllib.parse.urlencode({'action':'query','list':'search','srsearch':topic,'srlimit':5,'format':'json','utf8':1})
    request=urllib.request.Request('https://zh.wikipedia.org/w/api.php?'+query, headers={'User-Agent':'KnowledgeMotion/0.1 (educational student project)'})
    try:
        with urllib.request.urlopen(request,timeout=20) as response:
            raw=json.load(response)
        items=[]
        for item in raw['query']['search']:
            title=item['title']
            snippet=html.unescape(re.sub(r'<[^>]*>','',item.get('snippet','')))
            items.append({'title':title,'url':'https://zh.wikipedia.org/wiki/'+urllib.parse.quote(title.replace(' ','_')),'snippet':snippet})
        sources=normalize_results(items)
        if not sources: raise ResearchError('没有找到资料，请更换主题重试')
        return sources
    except (OSError, ValueError, KeyError) as exc:
        raise ResearchError('资料检索失败，请检查网络后重试') from exc
