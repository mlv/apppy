##Apppy -- App.net Python library

An endpoint-complete app.net library. 

##To use

It currently requires that you already have an access token.

```python
from apppy import *

api = apppy(access_token="...")

r=api.getUser("me")
assert r.json()['data']['username'] == username
```

It was tested with requests 1.1.0, but other versions should also work. Each endpoint call generates the 
appropriate URL, moves known API parameters to the appropriate location, then calls the corresponding requests 
call. It returns the request response.

It automatically handles rate limit requests by sleeping and retrying. If you don't want that, and know what 
you're doing, the following code:
```
api.gimme_429 = True
```
will let you catch 429 (rate limit) errors. 

