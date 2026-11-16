"""Small-sample comparison utilities; do not interpret results as video quality."""
def score_answers(items, answers):
    if not items or len(items)!=len(answers) or any(a not in ('A','B','C','D') for a in answers):
        raise ValueError('答案数量或选项无效')
    wrong=[item['id'] for item,answer in zip(items,answers) if item['answer']!=answer]
    correct=len(items)-len(wrong)
    return {'correct':correct,'total':len(items),'accuracy':correct/len(items),'wrong_ids':wrong}
