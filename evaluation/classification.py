"""Evaluate scene labels on a small hand-authored pilot set (not a benchmark)."""
import json
from pathlib import Path
from src.classifier import classify_scenes

def run():
    # 用人工编写并标注的分镜小样，记录预测和标签是否一致。
    cases=json.loads(Path('evaluation/classification_cases.json').read_text(encoding='utf-8-sig'))
    labels=classify_scenes(cases)
    results=[{'text':c['text'],'expected':c['label'],'predicted':prediction} for c,prediction in zip(cases,labels)]
    correct=sum(r['expected']==r['predicted'] for r in results)
    report={'dataset':'hand-authored pilot; labels need independent review','total':len(results),'correct':correct,'accuracy':correct/len(results),'cases':results}
    dest=Path('outputs/evaluation/classifier.json');dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"小样本分类：{correct}/{len(results)}；结果：{dest}")

if __name__=='__main__': run()
