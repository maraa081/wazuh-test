import pickle, json, sys

cookies = pickle.load(open(sys.argv[1], 'rb'))
print(json.dumps([{
    'name': c['name'],
    'value': c['value'],
    'domain': c.get('domain', '.linkedin.com'),
    'path': c.get('path', '/'),
    'secure': c.get('secure', True),
    'httpOnly': c.get('httpOnly', False),
    'sameSite': c.get('sameSite', 'None'),
} for c in cookies]))
