import json
from collections import Counter

def summarize(path):
    with open(path,'r',encoding='utf-8') as f:
        data = json.load(f)
    total = len(data)
    status = Counter(e.get('status_code') for e in data)
    errors = sum(1 for e in data if e.get('error'))
    pending = 0
    missing = 0
    missing_examples = []
    for e in data:
        body = e.get('response_body') or {}
        tcs = body.get('top_candidates') or []
        if any(tc.get('code') == '9999.00' for tc in tcs):
            pending += 1
        if body.get('missing_fields'):
            missing += 1
            missing_examples.append({'query_id': e.get('query_id'), 'query': e.get('query'), 'missing_fields': body.get('missing_fields'), 'top_candidates': tcs[:3]})
    out = {
        'total': total,
        'status_counts': dict(status),
        'errors': errors,
        'pending_classifications': pending,
        'with_missing_fields': missing,
        'missing_examples_sample': missing_examples[:5]
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    summarize('evaluation/detailed_logs.json')
