Added user streams. They can be used like 
```
st=api.createUserStream(timeout=600)
u=api.getUnifiedStreamPost(connection_id=st.headers['Connection-Id'])
for line in st.iter_lines(chunk_size=1):
    if line:
        blob = json.loads(line)
        print (json.dumps(blob, sort_keys=True, indent=2))
```

See the [app.net documentation](http://developers.app.net/docs/resources/user-stream/#available-endpoints) for which endpoints can be used in place of getUnifiedStreamPost()

Also included are two new endpoints, destroyUserStream() and destroySubscriptionUserStream(). 
First takes a connection_id, and second takes a connection_id and a subscription_id.

Because of the addition of user streams, the app stream endpoints have been changed from, eg. api.getAllStream()
to api.getAllAppStream() (s/Stream/AppStream/)
