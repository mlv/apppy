##Apppy -- App.net Python library

An endpoint-complete app.net library. 

##To use

You can use an already-existing access token, or use your client id / secret to get one.

```python
from apppy import *

api = apppy(access_token="...", app_access_token="...")

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

Apppy.py is machine generated. It uses [@Duerig's endpoints.json library](https://github.com/duerig/appnet.js/blob/master/hbs/endpoints.json) to generate all the endpoints. The code that generates the endpoints is not part 
of this distribution, so while I will work hard to fix any problems, I won't accept pull requests against 
apppy.py (but I will use them to correct the source files that generate apppy.py). This file is also machine 
generated.

##License:

MIT License

Copyright 2013 Michael Vezie

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
