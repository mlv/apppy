import requests
import itertools
import json
import time

from functools import reduce

class ratelimit(object):
    """ Class that manages rate limits. It may include higher level math to optimize sleep times, etc.
Parameters:
wlimit: Limit of number of writes per period
wreset: Time until full count of writes is restored.
wremaining: How many writes can be run in the next wreset seconds.

glimit: Limit of number of accesses per period
greset: Time until full count of accesses is restored.
gremaining: How many accesses can be run in the next greset seconds.

Method:setlimit(r): get the rate limit parameters from the response header and set them accordingly.
"""


    def __init__(self):
        self._wlimit = None
        self._wreset = None
        self._wremaining = None
        self._glimit = None
        self._greset = None
        self._gremaining = None

    def get_wlimit(self): return self._wlimit
    def get_wreset(self): return self._wreset
    def get_wremaining(self): return self._wremaining
    wlimit     = property(get_wlimit,     None, None,
                          "Maximum number of accesses per period (write limit)")
    wreset     = property(get_wreset,     None, None,
                          "Time until full count is reset (write limit)")
    wremaining = property(get_wremaining, None, None,
                          "accesses remaining until reset time (write limit)")

    def get_glimit(self): return self._glimit
    def get_greset(self): return self._greset
    def get_gremaining(self): return self._gremaining
    glimit     = property(get_glimit,     None, None,
                          "Maximum number of accesses per period (global limit)")
    greset     = property(get_greset,     None, None,
                          "Time until full count is reset (global limit)")
    gremaining = property(get_gremaining, None, None,
                          "accesses remaining until reset time (global limit)")

    def setlimit(self, r): # r is assumed to be the response to a requests.call
        def ghead(v): return int(r.headers['X-RateLimit-'+v])
        limit     = ghead('Limit')
        reset     = ghead('Reset')
        remaining = ghead('Remaining')
        
        if r.request.method == "POST" or r.request.method == "DELETE":
            self._wlimit = limit
            self._wreset = reset
            self._wremaining = remaining
            # Reminder: writes also affect global. I don't know the global limit, 
            # but I can at least make a guess about remaining.
            if self._gremaining > 0:
                self._gremaining -= 1
        else:
            self._glimit = limit
            self._greset = reset
            self._gremaining = remaining

class apppy(ratelimit):
    """ Usage: apppy(access_token=None, api_access_token=None)"""
    
    public_api_anchor = "alpha-api.app.net"

    def set_accesstoken(self, token):
        self._access_token = token
    def get_accesstoken(self):
        return self._access_token
    def del_accesstoken(self):
        self._access_token = None
    access_token = property(get_accesstoken, set_accesstoken, del_accesstoken, "The access token")

    def set_app_accesstoken(self, token):
        self._app_access_token = token
    def get_app_accesstoken(self):
        return self._app_access_token
    def del_app_accesstoken(self):
        self._app_access_token = None
    app_access_token = property(get_app_accesstoken, set_app_accesstoken, del_app_accesstoken, "The app access token")

    def set_gimme_429(self, token):
        self._gimme_429 = token
    def get_gimme_429(self):
        return self._gimme_429
    def del_gimme_429(self):
        self._gimme_429 = False
    gimme_429 = property(get_gimme_429, set_gimme_429, del_gimme_429,
                         "If true, tell API to return 429 error codes, instead of automaticallyh sleeping")

    def __init__(self, access_token=None, app_access_token=None):
        self.gimme_429 = False
        if access_token:
            self.set_accesstoken(access_token)
        if app_access_token:
            self.set_app_accesstoken(app_access_token)
        self.debug = False

    def generateAuthUrl(self, client_id, client_secret, redirect_url, scopes=None):
        """api.generateAuthUrl(client_id, client_secret, redirect_url, scopes=None)

Saves id, secret, redirect for getAuthResponse. First half of server-side web flow.
This returns a URL. Copy it and open it in a browser. When you authenticate, it will
take you to the redirect URL with the code attached. Feed that code into getAuthResponse
and you will have the access token."""
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_url = redirect_url
        
        url = "https://account.app.net/oauth/authorize?client_id="+\
            self.client_id + "&response_type=code&redirect_uri=" +\
            redirect_url + "&scope="

        if scopes == None:
            scopes = self.allscopes

        url += " ".join(filter(lambda x:x in self.allscopes, scopes))
        return url

    def dprint(self, st):
        import sys
        if type(self.debug)==bool:
            if not self.debug:
                return
            out=sys.stdout
        else:
            out=self.debug
        out.write(st+"\n")

    def getAuthResponse(self, code):
        """api.getAuthResponse(code)

Second half of server-side web flow. Use the code obtained from the AuthURL.
Note that this sets access_token but doesn't save it."""
        #generate POST request
        url = "https://alpha.app.net/oauth/access_token"
        post_data = {'client_id':self.client_id,
        'client_secret':self.client_secret,
        'grant_type':'authorization_code',
        'redirect_uri':self.redirect_url,
        'code':code}

        r = requests.post(url,data=post_data)
        r.raise_for_status()
        r=r.json()
        self.access_token = r['access_token']
        return r

    # App Access Token Flow
    def getAppAccessToken(self, client_id, client_secret):
        params={'client_id'    : client_id,
                'client_secret': client_secret,
                'grant_type'   : 'client_credentials'}
        url='https://account.app.net/oauth/access_token'

#        for k in params:
#            url=url+"&{0}={1}".format(k,params[k])
        print (url)
        r=requests.post(url, data=params)
        if r.status_code != 200:
            print (r.text)
        r.raise_for_status()
        d=r.json()
        return d['access_token']

    def createUserStream(self, connection_id=None, timeout=None):
        h={"Authorization": "BEARER "+self.access_token}
        r=requests.get("https://stream-channel.app.net/stream/user", stream=True, headers=h, timeout=None)
        return r
    
        
    def geturl(self, e, *opts):
        lparam=len(e['url_params'])
        assert len(opts) >= lparam
        url=self.base+"".join(reduce(tuple.__add__, zip(e['url']+['','',''], list(opts[:lparam])+['','',''])))
        # url=self.base+"".join(sum(itertools.izip_longest(e['url'], opts[:lparam], fillvalue=''), ()))
        return url
    

    calls = {
        "GET":      requests.get,
        "PUT":      requests.put,
        "DELETE":   requests.delete,
        "PATCH":    requests.patch,
        "POST":     requests.post,
        "POST-RAW": requests.post,
        }

    def expand_params(self, params):
        ret=None
        for p in params:
            if p in self.parameter_category:
                if ret == None:
                    ret = self.parameter_category[p]
                else:
                    ret += self.parameter_category[p]
            else:
                if ret == None:
                    ret = [p]
                else:
                    ret.append(p)
        return ret
        
    #Generic REQUESTS
    def genRequest(self, url, ep_data, params):
        rp={}
        for p in ("headers", "params", "data"):
            if p in params:
                rp[p] = params[p]
                del params[p]
            else:
                rp[p] = {}

        isjson = True
        rp['headers']['Content-Type'] = "application/json"
        for c,epl in (("data", "data_params"),
                     ("params", "get_params"),
                     ("params", "array_params")):
            pl = self.expand_params(ep_data[epl])
            #print epl, ep_data[epl], pl
            if c == "data" and hasattr(pl, 'join'):
                isjson = False
                del rp['headers']['Content-Type']
                continue
            if pl == None:
                continue
            #print pl
            for p in pl:
                #print p
                if p in params:
                    rp[c][p] = params[p]
                    del params[p]

        # The expected (by the API) parameters are put in the appropriate places (data, params, etc).
        # Any other parameters are assumed to be other named parameters used by requests. For example,
        # files and timeout.
        for k in params:
            rp[k] = params[k]
            
        # If the endpoint calls for the App access token, use that.
        # Otherwise, use the access token (even if it calls for None).
        # Reason: some endpoints (like getUser("me")) use the access_token
        if ep_data['token'] == 'App':
            rp['headers']['Authorization'] = "Bearer " + self.app_access_token
        elif self.access_token:
            rp['headers']['Authorization'] = "Bearer " + self.access_token
        
        self.dprint("calling {0} with URL {2} and all params {1}".format(ep_data['method'], json.dumps(rp, indent=2), url))

        call = self.calls[ep_data['method']]

        if isjson:
            rp['data'] = json.dumps(rp['data'])
        #print url, rp
        # we repeat the call in case of a 429
        for i in range(2):
            r = call(url, **rp)
            if r.status_code == 429:
                # 429 is "Rate limit exceeded. Need to sleep before you try again"
                # http://developers.app.net/docs/basics/rate-limits/
                # App.net asks that any client respect 429 and sleep RetryAfter seconds 
                # before trying again. In the normal case, we handle the sleeping 
                # ourselves. If the caller is clever, they can do api.gimme_429=True 
                # in which case it'll raise a 429 error that they're able to catch.
                # If they're clever enough to set gimme_429, but not clever enough 
                # to catch it, then app.net is still happy.
                #
                # Only do this once. If i > 0 (second time through the loop), just raise
                if i > 0 or self.gimme_429:
                    r.raise_for_status()
                    return {} # shouldn't get here. This just in case...
                time.sleep(float(r.header['RetryAfter']))
                # repeat the call
                continue

            return r
        return r
    base="https://alpha-api.app.net/stream/0/"
    parameter_category={'general_channel': ['channel_types', 'include_marker', 'include_read', 'include_recent_message', 'include_annotations', 'include_user_annotations', 'include_message_annotations', 'connection_id'], 'post_or_message': ['text'], 'file_ids': ['ids'], 'file': ['kind', 'type', 'name', 'public', 'annotations'], 'marker': ['id', 'name', 'percentage'], 'message': ['text', 'reply_to', 'annotations', 'entities', 'machine_only', 'destinations'], 'message_ids': ['ids'], 'UserStream': [], 'post_search': ['index', 'order', 'query', 'text', 'hashtags', 'links', 'link_domains', 'mentions', 'leading_mentions', 'annotation_types', 'attachment_types', 'crosspost_url', 'crosspost_domain', 'place_id', 'is_reply', 'is_directed', 'has_location', 'has_checkin', 'is_crosspost', 'has_attachment', 'has_oembed_photo', 'has_oembed_video', 'has_oembed_html5video', 'has_oembed_rich', 'language', 'client_id', 'creator_id', 'reply_to', 'thread_id'], 'content': 'content', 'place_search': ['latitude', 'longitude', 'q', 'radius', 'count', 'remove_closed', 'altitude', 'horizontal_accuracy', 'vertical_accuracy'], 'channel': ['readers', 'writers', 'annotations', 'type'], 'channel_ids': ['ids'], 'user_ids': ['ids'], 'user_search': ['q', 'count'], 'general_message': ['include_muted', 'include_deleted', 'include_machine', 'include_annotations', 'include_user_annotations', 'include_message_annotations', 'include_html', 'connection_id'], 'user': ['name', 'locale', 'timezone', 'description'], 'AppStream': ['object_types', 'type', 'filter_id', 'key'], 'post': ['text', 'reply_to', 'machine_only', 'annotations', 'entities'], 'general_file': ['file_types', 'include_incomplete', 'include_private', 'include_annotations', 'include_file_annotations', 'include_user_annotations', 'connection_id'], 'general_post': ['include_muted', 'include_deleted', 'include_directed_posts', 'include_machine', 'include_starred_by', 'include_reposters', 'include_annotations', 'include_post_annotations', 'include_user_annotations', 'include_html', 'connection_id'], 'pagination': ['since_id', 'before_id', 'count'], 'general_user': ['include_annotations', 'include_user_annotations', 'include_html', 'connection_id'], 'cover': 'image', 'filter': ['name', 'match_policy', 'clauses'], 'avatar': 'image', 'post_ids': ['ids'], 'stream_facet': ['has_oembed_photo'], 'channel_search': ['order', 'q', 'type', 'creator_id', 'tags']}
    allscopes=['files', 'follow', 'update_profile', 'stream', 'messages', 'public_messages', 'export', 'basic', 'write_post', 'email']

    def getUser(self , user_id, **kargs):
        """api.getUser(user_id) - Retrieve a User
        
        http://developers.app.net/docs/resources/user/lookup/#retrieve-a-user"""
        ep={'url_params': ['user_id'], 'group': 'user', 'name': 'get', 'array_params': [], 'data_params': [], 'get_params': ['general_user'], 'url': ['users/'], 'token': 'None', 'link': 'http://developers.app.net/docs/resources/user/lookup/#retrieve-a-user', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve a User'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def updateUser(self , **kargs):
        """api.updateUser() - Update a User
        
        http://developers.app.net/docs/resources/user/profile/#update-a-user"""
        ep={'url_params': [], 'group': 'user', 'name': 'update', 'array_params': [], 'data_params': ['user'], 'get_params': ['general_user'], 'url': ['users/me'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/user/profile/#update-a-user', 'scope': 'update_profile', 'method': 'PUT', 'description': 'Update a User'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def partialUpdateUser(self , **kargs):
        """api.partialUpdateUser() - Partially Update a User
        
        http://developers.app.net/docs/resources/user/profile/#partially-update-a-user"""
        ep={'url_params': [], 'group': 'user', 'name': 'partialUpdate', 'array_params': [], 'data_params': ['user'], 'get_params': ['general_user'], 'url': ['users/me'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/user/profile/#partially-update-a-user', 'scope': 'update_profile', 'method': 'PATCH', 'description': 'Partially Update a User'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getAvatarUser(self , user_id, **kargs):
        """api.getAvatarUser(user_id) - Retrieve a User's avatar image
        
        http://developers.app.net/docs/resources/user/profile/#retrieve-a-users-avatar-image"""
        ep={'url_params': ['user_id'], 'group': 'user', 'name': 'getAvatar', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['users/', '/avatar'], 'token': 'None', 'link': 'http://developers.app.net/docs/resources/user/profile/#retrieve-a-users-avatar-image', 'scope': 'basic', 'method': 'GET', 'description': "Retrieve a User's avatar image"}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def updateAvatarUser(self , **kargs):
        """api.updateAvatarUser() - Update a User's avatar image
        
        http://developers.app.net/docs/resources/user/profile/#update-a-users-avatar-image"""
        ep={'url_params': [], 'group': 'user', 'name': 'updateAvatar', 'array_params': [], 'data_params': ['avatar'], 'get_params': [], 'url': ['users/me/avatar'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/user/profile/#update-a-users-avatar-image', 'scope': 'update_profile', 'method': 'POST-RAW', 'description': "Update a User's avatar image"}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getCoverUser(self , user_id, **kargs):
        """api.getCoverUser(user_id) - Retrieve a User's cover image
        
        http://developers.app.net/docs/resources/user/profile/#retrieve-a-users-cover-image"""
        ep={'url_params': ['user_id'], 'group': 'user', 'name': 'getCover', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['users/', '/cover'], 'token': 'None', 'link': 'http://developers.app.net/docs/resources/user/profile/#retrieve-a-users-cover-image', 'scope': 'basic', 'method': 'GET', 'description': "Retrieve a User's cover image"}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def updateCoverUser(self , **kargs):
        """api.updateCoverUser() - Update a User's cover image
        
        http://developers.app.net/docs/resources/user/profile/#update-a-users-cover-image"""
        ep={'url_params': [], 'group': 'user', 'name': 'updateCover', 'array_params': [], 'data_params': ['cover'], 'get_params': [], 'url': ['users/me/cover'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/user/profile/#update-a-users-cover-image', 'scope': 'update_profile', 'method': 'POST-RAW', 'description': "Update a User's cover image"}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def followUser(self , user_id, **kargs):
        """api.followUser(user_id) - Follow a User
        
        http://developers.app.net/docs/resources/user/following/#follow-a-user"""
        ep={'url_params': ['user_id'], 'group': 'user', 'name': 'follow', 'array_params': [], 'data_params': [], 'get_params': ['general_user'], 'url': ['users/', '/follow'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/user/following/#follow-a-user', 'scope': 'follow', 'method': 'POST', 'description': 'Follow a User'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def unfollowUser(self , user_id, **kargs):
        """api.unfollowUser(user_id) - Unfollow a User
        
        http://developers.app.net/docs/resources/user/following/#unfollow-a-user"""
        ep={'url_params': ['user_id'], 'group': 'user', 'name': 'unfollow', 'array_params': [], 'data_params': [], 'get_params': ['general_user'], 'url': ['users/', '/follow'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/user/following/#unfollow-a-user', 'scope': 'follow', 'method': 'DELETE', 'description': 'Unfollow a User'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def muteUser(self , user_id, **kargs):
        """api.muteUser(user_id) - Mute a User
        
        http://developers.app.net/docs/resources/user/muting/#mute-a-user"""
        ep={'url_params': ['user_id'], 'group': 'user', 'name': 'mute', 'array_params': [], 'data_params': [], 'get_params': ['general_user'], 'url': ['users/', '/mute'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/user/muting/#mute-a-user', 'scope': 'follow', 'method': 'POST', 'description': 'Mute a User'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def unmuteUser(self , user_id, **kargs):
        """api.unmuteUser(user_id) - Unmute a User
        
        http://developers.app.net/docs/resources/user/muting/#unmute-a-user"""
        ep={'url_params': ['user_id'], 'group': 'user', 'name': 'unmute', 'array_params': [], 'data_params': [], 'get_params': ['general_user'], 'url': ['users/', '/mute'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/user/muting/#unmute-a-user', 'scope': 'follow', 'method': 'DELETE', 'description': 'Unmute a User'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def blockUser(self , user_id, **kargs):
        """api.blockUser(user_id) - Block a User
        
        http://developers.app.net/docs/resources/user/blocking/#block-a-user"""
        ep={'url_params': ['user_id'], 'group': 'user', 'name': 'block', 'array_params': [], 'data_params': [], 'get_params': ['general_user'], 'url': ['users/', '/block'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/user/blocking/#block-a-user', 'scope': 'follow', 'method': 'POST', 'description': 'Block a User'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def unblockUser(self , user_id, **kargs):
        """api.unblockUser(user_id) - Unblock a User
        
        http://developers.app.net/docs/resources/user/blocking/#unblock-a-user"""
        ep={'url_params': ['user_id'], 'group': 'user', 'name': 'unblock', 'array_params': [], 'data_params': [], 'get_params': ['general_user'], 'url': ['users/', '/block'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/user/blocking/#unblock-a-user', 'scope': 'follow', 'method': 'DELETE', 'description': 'Unblock a User'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def getListUser(self , **kargs):
        """api.getListUser(ids=[...]) - Retrieve multiple Users
        
        http://developers.app.net/docs/resources/user/lookup/#retrieve-multiple-users"""
        ep={'url_params': [], 'group': 'user', 'name': 'getList', 'array_params': ['user_ids'], 'data_params': [], 'get_params': ['general_user'], 'url': ['users'], 'token': 'Any', 'link': 'http://developers.app.net/docs/resources/user/lookup/#retrieve-multiple-users', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve multiple Users'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def searchUser(self , **kargs):
        """api.searchUser() - Search for Users
        
        http://developers.app.net/docs/resources/user/lookup/#search-for-users"""
        ep={'url_params': [], 'group': 'user', 'name': 'search', 'array_params': [], 'data_params': [], 'get_params': ['user_search', 'general_user'], 'url': ['users/search'], 'token': 'Any', 'link': 'http://developers.app.net/docs/resources/user/lookup/#search-for-users', 'scope': 'basic', 'method': 'GET', 'description': 'Search for Users'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getFollowingUser(self , user_id, **kargs):
        """api.getFollowingUser(user_id) - Retrieve Users a User is following
        
        http://developers.app.net/docs/resources/user/following/#list-users-a-user-is-following"""
        ep={'url_params': ['user_id'], 'group': 'user', 'name': 'getFollowing', 'array_params': [], 'data_params': [], 'get_params': ['general_user', 'pagination'], 'url': ['users/', '/following'], 'token': 'Any', 'link': 'http://developers.app.net/docs/resources/user/following/#list-users-a-user-is-following', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve Users a User is following'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def getFollowersUser(self , user_id, **kargs):
        """api.getFollowersUser(user_id) - Retrieve Users following a User
        
        http://developers.app.net/docs/resources/user/following/#list-users-following-a-user"""
        ep={'url_params': ['user_id'], 'group': 'user', 'name': 'getFollowers', 'array_params': [], 'data_params': [], 'get_params': ['general_user', 'pagination'], 'url': ['users/', '/followers'], 'token': 'Any', 'link': 'http://developers.app.net/docs/resources/user/following/#list-users-following-a-user', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve Users following a User'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def getFollowingIdsUser(self , user_id, **kargs):
        """api.getFollowingIdsUser(user_id) - Retrieve IDs of Users a User is following
        
        http://developers.app.net/docs/resources/user/following/#list-user-ids-a-user-is-following"""
        ep={'url_params': ['user_id'], 'group': 'user', 'name': 'getFollowingIds', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['users/', '/following/ids'], 'token': 'Any', 'link': 'http://developers.app.net/docs/resources/user/following/#list-user-ids-a-user-is-following', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve IDs of Users a User is following'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def getFollowerIdsUser(self , user_id, **kargs):
        """api.getFollowerIdsUser(user_id) - Retrieve IDs of Users following a User
        
        http://developers.app.net/docs/resources/user/following/#list-user-ids-following-a-user"""
        ep={'url_params': ['user_id'], 'group': 'user', 'name': 'getFollowerIds', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['users/', '/followers/ids'], 'token': 'Any', 'link': 'http://developers.app.net/docs/resources/user/following/#list-user-ids-following-a-user', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve IDs of Users following a User'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def getMutedUser(self , user_id, **kargs):
        """api.getMutedUser(user_id) - Retrieve muted Users
        
        http://developers.app.net/docs/resources/user/muting/#list-muted-users"""
        ep={'url_params': ['user_id'], 'group': 'user', 'name': 'getMuted', 'array_params': [], 'data_params': [], 'get_params': ['general_user'], 'url': ['users/', '/muted'], 'token': 'Any', 'link': 'http://developers.app.net/docs/resources/user/muting/#list-muted-users', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve muted Users'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def getMutedListUser(self , **kargs):
        """api.getMutedListUser(ids=[...]) - Retrieve muted User IDs for multiple Users
        
        http://developers.app.net/docs/resources/user/muting/#retrieve-muted-user-ids-for-multiple-users"""
        ep={'url_params': [], 'group': 'user', 'name': 'getMutedList', 'array_params': ['user_ids'], 'data_params': [], 'get_params': [], 'url': ['users/muted/ids'], 'token': 'App', 'link': 'http://developers.app.net/docs/resources/user/muting/#retrieve-muted-user-ids-for-multiple-users', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve muted User IDs for multiple Users'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getBlockedUser(self , user_id, **kargs):
        """api.getBlockedUser(user_id) - Retrieve blocked Users
        
        http://developers.app.net/docs/resources/user/blocking/#list-blocked-users"""
        ep={'url_params': ['user_id'], 'group': 'user', 'name': 'getBlocked', 'array_params': [], 'data_params': [], 'get_params': ['general_user'], 'url': ['users/', '/blocked'], 'token': 'Any', 'link': 'http://developers.app.net/docs/resources/user/blocking/#list-blocked-users', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve blocked Users'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def getBlockedListUser(self , **kargs):
        """api.getBlockedListUser(ids=[...]) - Retrieve blocked User IDs for multiple Users
        
        http://developers.app.net/docs/resources/user/blocking/#retrieve-blocked-user-ids-for-multiple-users"""
        ep={'url_params': [], 'group': 'user', 'name': 'getBlockedList', 'array_params': ['user_ids'], 'data_params': [], 'get_params': [], 'url': ['users/blocked/ids'], 'token': 'App', 'link': 'http://developers.app.net/docs/resources/user/blocking/#retrieve-blocked-user-ids-for-multiple-users', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve blocked User IDs for multiple Users'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getRepostersUser(self , post_id, **kargs):
        """api.getRepostersUser(post_id) - Retrieve Users who reposted a Post
        
        http://developers.app.net/docs/resources/user/post-interactions/#list-users-who-have-reposted-a-post"""
        ep={'url_params': ['post_id'], 'group': 'user', 'name': 'getReposters', 'array_params': [], 'data_params': [], 'get_params': ['general_user'], 'url': ['posts/', '/reposters'], 'token': 'Any', 'link': 'http://developers.app.net/docs/resources/user/post-interactions/#list-users-who-have-reposted-a-post', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve Users who reposted a Post'}
        url=self.geturl(ep , post_id)
        return self.genRequest(url, ep, kargs)

    def getStarsUser(self , post_id, **kargs):
        """api.getStarsUser(post_id) - Retrieve Users who starred a Post
        
        http://developers.app.net/docs/resources/user/post-interactions/#list-users-who-have-starred-a-post"""
        ep={'url_params': ['post_id'], 'group': 'user', 'name': 'getStars', 'array_params': [], 'data_params': [], 'get_params': ['general_user'], 'url': ['posts/', '/stars'], 'token': 'Any', 'link': 'http://developers.app.net/docs/resources/user/post-interactions/#list-users-who-have-starred-a-post', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve Users who starred a Post'}
        url=self.geturl(ep , post_id)
        return self.genRequest(url, ep, kargs)

    def createPost(self , **kargs):
        """api.createPost() - Create a Post
        
        http://developers.app.net/docs/resources/post/lifecycle/#create-a-post"""
        ep={'url_params': [], 'group': 'post', 'name': 'create', 'array_params': [], 'data_params': ['post'], 'get_params': ['general_post'], 'url': ['posts'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/post/lifecycle/#create-a-post', 'scope': 'write_post', 'method': 'POST', 'description': 'Create a Post'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getPost(self , post_id, **kargs):
        """api.getPost(post_id) - Retrieve a Post
        
        http://developers.app.net/docs/resources/post/lookup/#retrieve-a-post"""
        ep={'url_params': ['post_id'], 'group': 'post', 'name': 'get', 'array_params': [], 'data_params': [], 'get_params': ['general_post'], 'url': ['posts/'], 'token': 'None', 'link': 'http://developers.app.net/docs/resources/post/lookup/#retrieve-a-post', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve a Post'}
        url=self.geturl(ep , post_id)
        return self.genRequest(url, ep, kargs)

    def destroyPost(self , post_id, **kargs):
        """api.destroyPost(post_id) - Delete a Post
        
        http://developers.app.net/docs/resources/post/lifecycle/#delete-a-post"""
        ep={'url_params': ['post_id'], 'group': 'post', 'name': 'destroy', 'array_params': [], 'data_params': [], 'get_params': ['general_post'], 'url': ['posts/'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/post/lifecycle/#delete-a-post', 'scope': 'write_post', 'method': 'DELETE', 'description': 'Delete a Post'}
        url=self.geturl(ep , post_id)
        return self.genRequest(url, ep, kargs)

    def repostPost(self , post_id, **kargs):
        """api.repostPost(post_id) - Repost a Post
        
        http://developers.app.net/docs/resources/post/reposts/#repost-a-post"""
        ep={'url_params': ['post_id'], 'group': 'post', 'name': 'repost', 'array_params': [], 'data_params': [], 'get_params': ['general_post'], 'url': ['posts/', '/repost'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/post/reposts/#repost-a-post', 'scope': 'write_post', 'method': 'POST', 'description': 'Repost a Post'}
        url=self.geturl(ep , post_id)
        return self.genRequest(url, ep, kargs)

    def unrepostPost(self , post_id, **kargs):
        """api.unrepostPost(post_id) - Unrepost a Post
        
        http://developers.app.net/docs/resources/post/reposts/#unrepost-a-post"""
        ep={'url_params': ['post_id'], 'group': 'post', 'name': 'unrepost', 'array_params': [], 'data_params': [], 'get_params': ['general_post'], 'url': ['posts/', '/repost'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/post/reposts/#unrepost-a-post', 'scope': 'write_post', 'method': 'DELETE', 'description': 'Unrepost a Post'}
        url=self.geturl(ep , post_id)
        return self.genRequest(url, ep, kargs)

    def starPost(self , post_id, **kargs):
        """api.starPost(post_id) - Star a Post
        
        http://developers.app.net/docs/resources/post/stars/#star-a-post"""
        ep={'url_params': ['post_id'], 'group': 'post', 'name': 'star', 'array_params': [], 'data_params': [], 'get_params': ['general_post'], 'url': ['posts/', '/star'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/post/stars/#star-a-post', 'scope': 'write_post', 'method': 'POST', 'description': 'Star a Post'}
        url=self.geturl(ep , post_id)
        return self.genRequest(url, ep, kargs)

    def unstarPost(self , post_id, **kargs):
        """api.unstarPost(post_id) - Unstar a Post
        
        http://developers.app.net/docs/resources/post/stars/#unstar-a-post"""
        ep={'url_params': ['post_id'], 'group': 'post', 'name': 'unstar', 'array_params': [], 'data_params': [], 'get_params': ['general_post'], 'url': ['posts/', '/star'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/post/stars/#unstar-a-post', 'scope': 'write_post', 'method': 'DELETE', 'description': 'Unstar a Post'}
        url=self.geturl(ep , post_id)
        return self.genRequest(url, ep, kargs)

    def getListPost(self , **kargs):
        """api.getListPost(ids=[...]) - Retrieve multiple Posts
        
        http://developers.app.net/docs/resources/post/lookup/#retrieve-multiple-posts"""
        ep={'url_params': [], 'group': 'post', 'name': 'getList', 'array_params': ['post_ids'], 'data_params': [], 'get_params': ['general_post'], 'url': ['posts'], 'token': 'Any', 'link': 'http://developers.app.net/docs/resources/post/lookup/#retrieve-multiple-posts', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve multiple Posts'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getUserPost(self , user_id, **kargs):
        """api.getUserPost(user_id) - Retrieve a User's posts
        
        http://developers.app.net/docs/resources/post/streams/#retrieve-posts-created-by-a-user"""
        ep={'url_params': ['user_id'], 'group': 'post', 'name': 'getUser', 'array_params': [], 'data_params': [], 'get_params': ['general_post', 'pagination'], 'url': ['users/', '/posts'], 'token': 'None', 'link': 'http://developers.app.net/docs/resources/post/streams/#retrieve-posts-created-by-a-user', 'scope': 'basic', 'method': 'GET', 'description': "Retrieve a User's posts"}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def getUserStarredPost(self , user_id, **kargs):
        """api.getUserStarredPost(user_id) - Retrieve a User's starred posts
        
        http://developers.app.net/docs/resources/post/stars/#retrieve-posts-starred-by-a-user"""
        ep={'url_params': ['user_id'], 'group': 'post', 'name': 'getUserStarred', 'array_params': [], 'data_params': [], 'get_params': ['general_post', 'pagination'], 'url': ['users/', '/stars'], 'token': 'None', 'link': 'http://developers.app.net/docs/resources/post/stars/#retrieve-posts-starred-by-a-user', 'scope': 'basic', 'method': 'GET', 'description': "Retrieve a User's starred posts"}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def getUserMentionsPost(self , user_id, **kargs):
        """api.getUserMentionsPost(user_id) - Retrieve Posts mentioning a User
        
        http://developers.app.net/docs/resources/post/streams/#retrieve-posts-mentioning-a-user"""
        ep={'url_params': ['user_id'], 'group': 'post', 'name': 'getUserMentions', 'array_params': [], 'data_params': [], 'get_params': ['general_post', 'pagination'], 'url': ['users/', '/mentions'], 'token': 'Any', 'link': 'http://developers.app.net/docs/resources/post/streams/#retrieve-posts-mentioning-a-user', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve Posts mentioning a User'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def getHashtagPost(self , hashtag, **kargs):
        """api.getHashtagPost(hashtag) - Retrieve Posts containing a hashtag
        
        http://developers.app.net/docs/resources/post/streams/#retrieve-tagged-posts"""
        ep={'url_params': ['hashtag'], 'group': 'post', 'name': 'getHashtag', 'array_params': [], 'data_params': [], 'get_params': ['general_post', 'pagination'], 'url': ['posts/tag/'], 'token': 'None', 'link': 'http://developers.app.net/docs/resources/post/streams/#retrieve-tagged-posts', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve Posts containing a hashtag'}
        url=self.geturl(ep , hashtag)
        return self.genRequest(url, ep, kargs)

    def getThreadPost(self , post_id, **kargs):
        """api.getThreadPost(post_id) - Retrieve replies to a Post
        
        http://developers.app.net/docs/resources/post/replies"""
        ep={'url_params': ['post_id'], 'group': 'post', 'name': 'getThread', 'array_params': [], 'data_params': [], 'get_params': ['general_post', 'pagination'], 'url': ['posts/', '/replies'], 'token': 'Any', 'link': 'http://developers.app.net/docs/resources/post/replies', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve replies to a Post'}
        url=self.geturl(ep , post_id)
        return self.genRequest(url, ep, kargs)

    def getUserStreamPost(self , **kargs):
        """api.getUserStreamPost() - Retrieve a User's personalized stream
        
        http://developers.app.net/docs/resources/post/streams/#retrieve-a-users-personalized-stream"""
        ep={'url_params': [], 'group': 'post', 'name': 'getUserStream', 'array_params': [], 'data_params': [], 'get_params': ['general_post', 'pagination', 'stream_facet'], 'url': ['posts/stream'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/post/streams/#retrieve-a-users-personalized-stream', 'scope': 'stream', 'method': 'GET', 'description': "Retrieve a User's personalized stream"}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getUnifiedStreamPost(self , **kargs):
        """api.getUnifiedStreamPost() - Retrieve a User's unified stream
        
        http://developers.app.net/docs/resources/post/streams/#retrieve-a-users-unified-stream"""
        ep={'url_params': [], 'group': 'post', 'name': 'getUnifiedStream', 'array_params': [], 'data_params': [], 'get_params': ['general_post', 'pagination', 'stream_facet'], 'url': ['posts/stream/unified'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/post/streams/#retrieve-a-users-unified-stream', 'scope': 'stream', 'method': 'GET', 'description': "Retrieve a User's unified stream"}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getGlobalPost(self , **kargs):
        """api.getGlobalPost() - Retrieve the Global stream
        
        http://developers.app.net/docs/resources/post/streams/#retrieve-the-global-stream"""
        ep={'url_params': [], 'group': 'post', 'name': 'getGlobal', 'array_params': [], 'data_params': [], 'get_params': ['general_post', 'pagination'], 'url': ['posts/stream/global'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/post/streams/#retrieve-the-global-stream', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve the Global stream'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def reportPost(self , post_id, **kargs):
        """api.reportPost(post_id) - Report a Post
        
        http://developers.app.net/docs/resources/post/report/#report-a-post"""
        ep={'url_params': ['post_id'], 'group': 'post', 'name': 'report', 'array_params': [], 'data_params': [], 'get_params': ['general_post'], 'url': ['posts/', '/report'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/post/report/#report-a-post', 'scope': 'basic', 'method': 'POST', 'description': 'Report a Post'}
        url=self.geturl(ep , post_id)
        return self.genRequest(url, ep, kargs)

    def searchPost(self , **kargs):
        """api.searchPost() - Search for Posts
        
        http://developers.app.net/docs/resources/post/search/#search-for-posts"""
        ep={'url_params': [], 'group': 'post', 'name': 'search', 'array_params': [], 'data_params': [], 'get_params': ['post_search', 'general_post'], 'url': ['posts/search'], 'token': 'Any', 'link': 'http://developers.app.net/docs/resources/post/search/#search-for-posts', 'scope': 'basic', 'method': 'GET', 'description': 'Search for Posts'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getUserSubscribedChannel(self , **kargs):
        """api.getUserSubscribedChannel() - Get current user's subscribed channels
        
        http://developers.app.net/docs/resources/channel/subscriptions/#get-current-users-subscribed-channels"""
        ep={'url_params': [], 'group': 'channel', 'name': 'getUserSubscribed', 'array_params': [], 'data_params': [], 'get_params': ['general_channel', 'pagination'], 'url': ['channels'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/channel/subscriptions/#get-current-users-subscribed-channels', 'scope': 'messages', 'method': 'GET', 'description': "Get current user's subscribed channels"}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def createChannel(self , **kargs):
        """api.createChannel() - Create a Channel
        
        http://developers.app.net/docs/resources/channel/lifecycle/#create-a-channel"""
        ep={'url_params': [], 'group': 'channel', 'name': 'create', 'array_params': [], 'data_params': ['channel'], 'get_params': ['general_channel'], 'url': ['channels'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/channel/lifecycle/#create-a-channel', 'scope': 'messages', 'method': 'POST', 'description': 'Create a Channel'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getChannel(self , channel_id, **kargs):
        """api.getChannel(channel_id) - Retrieve a Channel
        
        http://developers.app.net/docs/resources/channel/lookup/#retrieve-a-channel"""
        ep={'url_params': ['channel_id'], 'group': 'channel', 'name': 'get', 'array_params': [], 'data_params': [], 'get_params': ['general_channel'], 'url': ['channels/'], 'token': 'Varies', 'link': 'http://developers.app.net/docs/resources/channel/lookup/#retrieve-a-channel', 'scope': 'messages', 'method': 'GET', 'description': 'Retrieve a Channel'}
        url=self.geturl(ep , channel_id)
        return self.genRequest(url, ep, kargs)

    def getListChannel(self , **kargs):
        """api.getListChannel(ids=[...]) - Retrieve multiple Channels
        
        http://developers.app.net/docs/resources/channel/lookup/#retrieve-multiple-channels"""
        ep={'url_params': [], 'group': 'channel', 'name': 'getList', 'array_params': ['channel_ids'], 'data_params': [], 'get_params': ['general_channel'], 'url': ['channels'], 'token': 'Varies', 'link': 'http://developers.app.net/docs/resources/channel/lookup/#retrieve-multiple-channels', 'scope': 'messages', 'method': 'GET', 'description': 'Retrieve multiple Channels'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getCreatedChannel(self , **kargs):
        """api.getCreatedChannel() - Retrieve my Channels
        
        http://developers.app.net/docs/resources/channel/lookup/#retrieve-my-channels"""
        ep={'url_params': [], 'group': 'channel', 'name': 'getCreated', 'array_params': [], 'data_params': [], 'get_params': ['general_channel', 'pagination'], 'url': ['users/me/channels'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/channel/lookup/#retrieve-my-channels', 'scope': 'messages', 'method': 'GET', 'description': 'Retrieve my Channels'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getUnreadCountChannel(self , **kargs):
        """api.getUnreadCountChannel() - Retrieve number of unread PM Channels
        
        http://developers.app.net/docs/resources/channel/lookup/#retrieve-number-of-unread-pm-channels"""
        ep={'url_params': [], 'group': 'channel', 'name': 'getUnreadCount', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['users/me/channels/pm/num_unread'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/channel/lookup/#retrieve-number-of-unread-pm-channels', 'scope': 'messages', 'method': 'GET', 'description': 'Retrieve number of unread PM Channels'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getUnreadBroadcastCountChannel(self , **kargs):
        """api.getUnreadBroadcastCountChannel() - Retrieve number of unread Broadcast Channels
        
        http://developers.app.net/docs/resources/channel/lookup/#retrieve-number-of-unread-broadcast-channels"""
        ep={'url_params': [], 'group': 'channel', 'name': 'getUnreadBroadcastCount', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['users/me/channels/broadcast/num_unread'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/channel/lookup/#retrieve-number-of-unread-broadcast-channels', 'scope': 'messages', 'method': 'GET', 'description': 'Retrieve number of unread Broadcast Channels'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def markBroadcastChannelsReadChannel(self , **kargs):
        """api.markBroadcastChannelsReadChannel() - Mark all Broadcast Channels as read
        
        http://developers.app.net/docs/resources/channel/lookup/#mark-all-broadcast-channels-as-read"""
        ep={'url_params': [], 'group': 'channel', 'name': 'markBroadcastChannelsRead', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['users/me/channels/broadcast/num_unread'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/channel/lookup/#mark-all-broadcast-channels-as-read', 'scope': 'messages', 'method': 'DELETE', 'description': 'Mark all Broadcast Channels as read'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def updateChannel(self , channel_id, **kargs):
        """api.updateChannel(channel_id) - Update a Channel
        
        http://developers.app.net/docs/resources/channel/lifecycle/#update-a-channel"""
        ep={'url_params': ['channel_id'], 'group': 'channel', 'name': 'update', 'array_params': [], 'data_params': ['channel'], 'get_params': ['general_channel'], 'url': ['channels/'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/channel/lifecycle/#update-a-channel', 'scope': 'messages', 'method': 'PUT', 'description': 'Update a Channel'}
        url=self.geturl(ep , channel_id)
        return self.genRequest(url, ep, kargs)

    def deactivateChannel(self , channel_id, **kargs):
        """api.deactivateChannel(channel_id) - Deactivate a Channel
        
        http://developers.app.net/docs/resources/channel/lifecycle/#deactivate-a-channel"""
        ep={'url_params': ['channel_id'], 'group': 'channel', 'name': 'deactivate', 'array_params': [], 'data_params': ['channel'], 'get_params': ['general_channel'], 'url': ['channels/'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/channel/lifecycle/#deactivate-a-channel', 'scope': 'messages', 'method': 'DELETE', 'description': 'Deactivate a Channel'}
        url=self.geturl(ep , channel_id)
        return self.genRequest(url, ep, kargs)

    def subscribeChannel(self , channel_id, **kargs):
        """api.subscribeChannel(channel_id) - Subscribe to a Channel
        
        http://developers.app.net/docs/resources/channel/subscriptions/#subscribe-to-a-channel"""
        ep={'url_params': ['channel_id'], 'group': 'channel', 'name': 'subscribe', 'array_params': [], 'data_params': [], 'get_params': ['general_channel'], 'url': ['channels/', '/subscribe'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/channel/subscriptions/#subscribe-to-a-channel', 'scope': 'messages', 'method': 'POST', 'description': 'Subscribe to a Channel'}
        url=self.geturl(ep , channel_id)
        return self.genRequest(url, ep, kargs)

    def unsubscribeChannel(self , channel_id, **kargs):
        """api.unsubscribeChannel(channel_id) - Unsubscribe from a Channel
        
        http://developers.app.net/docs/resources/channel/subscriptions/#unsubscribe-from-a-channel"""
        ep={'url_params': ['channel_id'], 'group': 'channel', 'name': 'unsubscribe', 'array_params': [], 'data_params': [], 'get_params': ['general_channel'], 'url': ['channels/', '/subscribe'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/channel/subscriptions/#unsubscribe-from-a-channel', 'scope': 'messages', 'method': 'DELETE', 'description': 'Unsubscribe from a Channel'}
        url=self.geturl(ep , channel_id)
        return self.genRequest(url, ep, kargs)

    def getSubscribersChannel(self , channel_id, **kargs):
        """api.getSubscribersChannel(channel_id) - Retrieve users subscribed to a Channel
        
        http://developers.app.net/docs/resources/channel/subscriptions/#retrieve-users-subscribed-to-a-channel"""
        ep={'url_params': ['channel_id'], 'group': 'channel', 'name': 'getSubscribers', 'array_params': [], 'data_params': [], 'get_params': ['general_channel', 'pagination'], 'url': ['channels/', '/subscribers'], 'token': 'None', 'link': 'http://developers.app.net/docs/resources/channel/subscriptions/#retrieve-users-subscribed-to-a-channel', 'scope': 'messages', 'method': 'GET', 'description': 'Retrieve users subscribed to a Channel'}
        url=self.geturl(ep , channel_id)
        return self.genRequest(url, ep, kargs)

    def getSubscriberIdsChannel(self , channel_id, **kargs):
        """api.getSubscriberIdsChannel(channel_id) - Retrieve user ids subscribed to a Channel
        
        http://developers.app.net/docs/resources/channel/subscriptions/#retrieve-user-ids-subscribed-to-a-channel"""
        ep={'url_params': ['channel_id'], 'group': 'channel', 'name': 'getSubscriberIds', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['channels/', '/subscribers/ids'], 'token': 'None', 'link': 'http://developers.app.net/docs/resources/channel/subscriptions/#retrieve-user-ids-subscribed-to-a-channel', 'scope': 'messages', 'method': 'GET', 'description': 'Retrieve user ids subscribed to a Channel'}
        url=self.geturl(ep , channel_id)
        return self.genRequest(url, ep, kargs)

    def getSubscriberIdListChannel(self , **kargs):
        """api.getSubscriberIdListChannel(ids=[...]) - Retrieve user ids subscribed to multiple Channels
        
        http://developers.app.net/docs/resources/channel/subscriptions/#retrieve-user-ids-subscribed-to-a-channel"""
        ep={'url_params': [], 'group': 'channel', 'name': 'getSubscriberIdList', 'array_params': ['channel_ids'], 'data_params': [], 'get_params': [], 'url': ['channels/subscribers/ids'], 'token': 'Any', 'link': 'http://developers.app.net/docs/resources/channel/subscriptions/#retrieve-user-ids-subscribed-to-a-channel', 'scope': 'messages', 'method': 'GET', 'description': 'Retrieve user ids subscribed to multiple Channels'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def muteChannel(self , channel_id, **kargs):
        """api.muteChannel(channel_id) - Mute a Channel
        
        http://developers.app.net/docs/resources/channel/muting/#mute-a-channel"""
        ep={'url_params': ['channel_id'], 'group': 'channel', 'name': 'mute', 'array_params': [], 'data_params': [], 'get_params': ['general_channel'], 'url': ['channels/', '/mute'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/channel/muting/#mute-a-channel', 'scope': 'messages', 'method': 'POST', 'description': 'Mute a Channel'}
        url=self.geturl(ep , channel_id)
        return self.genRequest(url, ep, kargs)

    def unmuteChannel(self , channel_id, **kargs):
        """api.unmuteChannel(channel_id) - Unmute a Channel
        
        http://developers.app.net/docs/resources/channel/muting/#unmute-a-channel"""
        ep={'url_params': ['channel_id'], 'group': 'channel', 'name': 'unmute', 'array_params': [], 'data_params': [], 'get_params': ['general_channel'], 'url': ['channels/', '/mute'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/channel/muting/#unmute-a-channel', 'scope': 'messages', 'method': 'DELETE', 'description': 'Unmute a Channel'}
        url=self.geturl(ep , channel_id)
        return self.genRequest(url, ep, kargs)

    def getMutedChannel(self , **kargs):
        """api.getMutedChannel() - Get current user's muted Channels
        
        http://developers.app.net/docs/resources/channel/muting/#get-current-users-muted-channels"""
        ep={'url_params': [], 'group': 'channel', 'name': 'getMuted', 'array_params': [], 'data_params': [], 'get_params': ['general_channel'], 'url': ['users/me/channels/muted'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/channel/muting/#get-current-users-muted-channels', 'scope': 'messages', 'method': 'GET', 'description': "Get current user's muted Channels"}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def searchChannel(self , **kargs):
        """api.searchChannel() - Search for Channels
        
        http://developers.app.net/docs/resources/channel/search/#search-for-channels"""
        ep={'url_params': [], 'group': 'channel', 'name': 'search', 'array_params': [], 'data_params': [], 'get_params': ['channel_search', 'general_channel'], 'url': ['channels/search'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/channel/search/#search-for-channels', 'scope': 'public_messages', 'method': 'GET', 'description': 'Search for Channels'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getChannelMessage(self , channel_id, **kargs):
        """api.getChannelMessage(channel_id) - Retrieve the Messages in a Channel
        
        http://developers.app.net/docs/resources/message/lifecycle/#retrieve-the-messages-in-a-channel"""
        ep={'url_params': ['channel_id'], 'group': 'message', 'name': 'getChannel', 'array_params': [], 'data_params': [], 'get_params': ['general_message', 'pagination'], 'url': ['channels/', '/messages'], 'token': 'None', 'link': 'http://developers.app.net/docs/resources/message/lifecycle/#retrieve-the-messages-in-a-channel', 'scope': 'messages', 'method': 'GET', 'description': 'Retrieve the Messages in a Channel'}
        url=self.geturl(ep , channel_id)
        return self.genRequest(url, ep, kargs)

    def createMessage(self , channel_id, **kargs):
        """api.createMessage(channel_id) - Create a Message
        
        http://developers.app.net/docs/resources/message/lifecycle/#create-a-message"""
        ep={'url_params': ['channel_id'], 'group': 'message', 'name': 'create', 'array_params': [], 'data_params': ['message'], 'get_params': ['general_message'], 'url': ['channels/', '/messages'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/message/lifecycle/#create-a-message', 'scope': 'messages', 'method': 'POST', 'description': 'Create a Message'}
        url=self.geturl(ep , channel_id)
        return self.genRequest(url, ep, kargs)

    def getMessage(self , channel_id, message_id, **kargs):
        """api.getMessage(channel_id, message_id) - Retrieve a Message
        
        http://developers.app.net/docs/resources/message/lookup/#retrieve-a-message"""
        ep={'url_params': ['channel_id', 'message_id'], 'group': 'message', 'name': 'get', 'array_params': [], 'data_params': [], 'get_params': ['general_message'], 'url': ['channels/', '/messages/'], 'token': 'None', 'link': 'http://developers.app.net/docs/resources/message/lookup/#retrieve-a-message', 'scope': 'messages', 'method': 'GET', 'description': 'Retrieve a Message'}
        url=self.geturl(ep , channel_id, message_id)
        return self.genRequest(url, ep, kargs)

    def getListMessage(self , **kargs):
        """api.getListMessage(ids=[...]) - Retrieve multiple Messages
        
        http://developers.app.net/docs/resources/message/lookup/#retrieve-multiple-messages"""
        ep={'url_params': [], 'group': 'message', 'name': 'getList', 'array_params': ['message_ids'], 'data_params': [], 'get_params': ['general_message'], 'url': ['channels/messages'], 'token': 'None', 'link': 'http://developers.app.net/docs/resources/message/lookup/#retrieve-multiple-messages', 'scope': 'messages', 'method': 'GET', 'description': 'Retrieve multiple Messages'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getUserMessage(self , **kargs):
        """api.getUserMessage() - Retrieve my Messages
        
        http://developers.app.net/docs/resources/message/lookup/#retrieve-my-messages"""
        ep={'url_params': [], 'group': 'message', 'name': 'getUser', 'array_params': [], 'data_params': [], 'get_params': ['general_message'], 'url': ['users/me/messages'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/message/lookup/#retrieve-my-messages', 'scope': 'messages', 'method': 'GET', 'description': 'Retrieve my Messages'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def destroyMessage(self , channel_id, message_id, **kargs):
        """api.destroyMessage(channel_id, message_id) - Delete a Message
        
        http://developers.app.net/docs/resources/message/lifecycle/#delete-a-message"""
        ep={'url_params': ['channel_id', 'message_id'], 'group': 'message', 'name': 'destroy', 'array_params': [], 'data_params': [], 'get_params': ['general_message'], 'url': ['channels/', '/messages/'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/message/lifecycle/#delete-a-message', 'scope': 'messages', 'method': 'DELETE', 'description': 'Delete a Message'}
        url=self.geturl(ep , channel_id, message_id)
        return self.genRequest(url, ep, kargs)

    def createFile(self , **kargs):
        """api.createFile() - Create a File
        
        http://developers.app.net/docs/resources/file/lifecycle/#create-a-file"""
        ep={'url_params': [], 'group': 'file', 'name': 'create', 'array_params': [], 'data_params': ['file'], 'get_params': ['general_file'], 'url': ['files'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/file/lifecycle/#create-a-file', 'scope': 'files', 'method': 'POST-RAW', 'description': 'Create a File'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def createPlaceholderFile(self , **kargs):
        """api.createPlaceholderFile() - Create a File Placeholder
        
        http://developers.app.net/docs/resources/file/lifecycle/#create-a-file"""
        ep={'url_params': [], 'group': 'file', 'name': 'createPlaceholder', 'array_params': [], 'data_params': ['file'], 'get_params': ['general_file'], 'url': ['files'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/file/lifecycle/#create-a-file', 'scope': 'files', 'method': 'POST', 'description': 'Create a File Placeholder'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getFile(self , file_id, **kargs):
        """api.getFile(file_id) - Retrieve a File
        
        http://developers.app.net/docs/resources/file/lookup/#retrieve-a-file"""
        ep={'url_params': ['file_id'], 'group': 'file', 'name': 'get', 'array_params': [], 'data_params': [], 'get_params': ['general_file'], 'url': ['files/'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/file/lookup/#retrieve-a-file', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve a File'}
        url=self.geturl(ep , file_id)
        return self.genRequest(url, ep, kargs)

    def getListFile(self , **kargs):
        """api.getListFile(ids=[...]) - Retrieve multiple Files
        
        http://developers.app.net/docs/resources/file/lookup/#retrieve-multiple-files"""
        ep={'url_params': [], 'group': 'file', 'name': 'getList', 'array_params': ['file_ids'], 'data_params': [], 'get_params': ['general_file'], 'url': ['files'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/file/lookup/#retrieve-multiple-files', 'scope': 'files', 'method': 'GET', 'description': 'Retrieve multiple Files'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def destroyFile(self , file_id, **kargs):
        """api.destroyFile(file_id) - Delete a File
        
        http://developers.app.net/docs/resources/file/lifecycle/#delete-a-file"""
        ep={'url_params': ['file_id'], 'group': 'file', 'name': 'destroy', 'array_params': [], 'data_params': [], 'get_params': ['general_file'], 'url': ['files/'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/file/lifecycle/#delete-a-file', 'scope': 'files', 'method': 'DELETE', 'description': 'Delete a File'}
        url=self.geturl(ep , file_id)
        return self.genRequest(url, ep, kargs)

    def getUserFile(self , **kargs):
        """api.getUserFile() - Retrieve my Files
        
        http://developers.app.net/docs/resources/file/lookup/#retrieve-my-files"""
        ep={'url_params': [], 'group': 'file', 'name': 'getUser', 'array_params': [], 'data_params': [], 'get_params': ['general_file', 'pagination'], 'url': ['users/me/files'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/file/lookup/#retrieve-my-files', 'scope': 'files', 'method': 'GET', 'description': 'Retrieve my Files'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def updateFile(self , file_id, **kargs):
        """api.updateFile(file_id) - Update a File
        
        http://developers.app.net/docs/resources/file/lifecycle/#update-a-file"""
        ep={'url_params': ['file_id'], 'group': 'file', 'name': 'update', 'array_params': [], 'data_params': ['file'], 'get_params': ['general_file'], 'url': ['files/'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/file/lifecycle/#update-a-file', 'scope': 'files', 'method': 'PUT', 'description': 'Update a File'}
        url=self.geturl(ep , file_id)
        return self.genRequest(url, ep, kargs)

    def getContentFile(self , file_id, **kargs):
        """api.getContentFile(file_id) - Get File content
        
        http://developers.app.net/docs/resources/file/content/#get-file-content"""
        ep={'url_params': ['file_id'], 'group': 'file', 'name': 'getContent', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['files/', '/content'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/file/content/#get-file-content', 'scope': 'files', 'method': 'GET', 'description': 'Get File content'}
        url=self.geturl(ep , file_id)
        return self.genRequest(url, ep, kargs)

    def setContentFile(self , file_id, **kargs):
        """api.setContentFile(file_id) - Set File content
        
        http://developers.app.net/docs/resources/file/content/#set-file-content"""
        ep={'url_params': ['file_id'], 'group': 'file', 'name': 'setContent', 'array_params': [], 'data_params': ['content'], 'get_params': [], 'url': ['files/', '/content'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/file/content/#set-file-content', 'scope': 'files', 'method': 'PUT', 'description': 'Set File content'}
        url=self.geturl(ep , file_id)
        return self.genRequest(url, ep, kargs)

    def createAppStream(self , **kargs):
        """api.createAppStream() - Create a Stream
        
        http://developers.app.net/docs/resources/stream/lifecycle/#create-a-stream"""
        ep={'url_params': [], 'group': 'AppStream', 'name': 'create', 'array_params': [], 'data_params': ['stream'], 'get_params': [], 'url': ['streams'], 'token': 'App', 'link': 'http://developers.app.net/docs/resources/stream/lifecycle/#create-a-stream', 'scope': 'basic', 'method': 'POST', 'description': 'Create a Stream'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getAppStream(self , stream_id, **kargs):
        """api.getAppStream(stream_id) - Retrieve a Stream
        
        http://developers.app.net/docs/resources/stream/lifecycle/#retrieve-a-stream"""
        ep={'url_params': ['stream_id'], 'group': 'AppStream', 'name': 'get', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['streams/'], 'token': 'App', 'link': 'http://developers.app.net/docs/resources/stream/lifecycle/#retrieve-a-stream', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve a Stream'}
        url=self.geturl(ep , stream_id)
        return self.genRequest(url, ep, kargs)

    def updateAppStream(self , stream_id, **kargs):
        """api.updateAppStream(stream_id) - Update a Stream
        
        http://developers.app.net/docs/resources/stream/lifecycle/#update-a-stream"""
        ep={'url_params': ['stream_id'], 'group': 'AppStream', 'name': 'update', 'array_params': [], 'data_params': ['stream'], 'get_params': [], 'url': ['streams/'], 'token': 'App', 'link': 'http://developers.app.net/docs/resources/stream/lifecycle/#update-a-stream', 'scope': 'basic', 'method': 'PUT', 'description': 'Update a Stream'}
        url=self.geturl(ep , stream_id)
        return self.genRequest(url, ep, kargs)

    def destroyAppStream(self , stream_id, **kargs):
        """api.destroyAppStream(stream_id) - Delete a Stream
        
        http://developers.app.net/docs/resources/stream/lifecycle/#delete-a-stream"""
        ep={'url_params': ['stream_id'], 'group': 'AppStream', 'name': 'destroy', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['streams/'], 'token': 'App', 'link': 'http://developers.app.net/docs/resources/stream/lifecycle/#delete-a-stream', 'scope': 'basic', 'method': 'DELETE', 'description': 'Delete a Stream'}
        url=self.geturl(ep , stream_id)
        return self.genRequest(url, ep, kargs)

    def getAllAppStream(self , **kargs):
        """api.getAllAppStream() - Retrieve all Streams for the current Token
        
        http://developers.app.net/docs/resources/stream/lifecycle/#get-current-tokens-streams"""
        ep={'url_params': [], 'group': 'AppStream', 'name': 'getAll', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['streams'], 'token': 'App', 'link': 'http://developers.app.net/docs/resources/stream/lifecycle/#get-current-tokens-streams', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve all Streams for the current Token'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def destroyAllAppStream(self , **kargs):
        """api.destroyAllAppStream() - Delete all Streams for the current Token
        
        http://developers.app.net/docs/resources/stream/lifecycle/#delete-all-of-the-current-users-streams"""
        ep={'url_params': [], 'group': 'AppStream', 'name': 'destroyAll', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['streams'], 'token': 'App', 'link': 'http://developers.app.net/docs/resources/stream/lifecycle/#delete-all-of-the-current-users-streams', 'scope': 'basic', 'method': 'DELETE', 'description': 'Delete all Streams for the current Token'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def destroyUserStream(self , connection_id, **kargs):
        """api.destroyUserStream(connection_id) - Delete a User Stream
        
        http://developers.app.net/docs/resources/user-stream/lifecycle/#delete-a-user-stream"""
        ep={'url_params': ['connection_id'], 'group': 'UserStream', 'name': 'destroy', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['streams/me/streams/'], 'token': 'user', 'link': 'http://developers.app.net/docs/resources/user-stream/lifecycle/#delete-a-user-stream', 'scope': 'basic', 'method': 'DELETE', 'description': 'Delete a User Stream'}
        url=self.geturl(ep , connection_id)
        return self.genRequest(url, ep, kargs)

    def destroySubscriptionUserStream(self , connection_id, subscription_id, **kargs):
        """api.destroySubscriptionUserStream(connection_id, subscription_id) - Delete a User Stream Subscription
        
        http://developers.app.net/docs/resources/user-stream/lifecycle/#delete-a-user-stream-subscription"""
        ep={'url_params': ['connection_id', 'subscription_id'], 'group': 'UserStream', 'name': 'destroySubscription', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['streams/me/streams/'], 'token': 'user', 'link': 'http://developers.app.net/docs/resources/user-stream/lifecycle/#delete-a-user-stream-subscription', 'scope': 'basic', 'method': 'DELETE', 'description': 'Delete a User Stream Subscription'}
        url=self.geturl(ep , connection_id, subscription_id)
        return self.genRequest(url, ep, kargs)

    def createFilter(self , **kargs):
        """api.createFilter() - Create a Filter
        
        http://developers.app.net/docs/resources/filter/lifecycle/#create-a-filter"""
        ep={'url_params': [], 'group': 'filter', 'name': 'create', 'array_params': [], 'data_params': ['filter'], 'get_params': [], 'url': ['filters'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/filter/lifecycle/#create-a-filter', 'scope': 'basic', 'method': 'POST', 'description': 'Create a Filter'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getFilter(self , filter_id, **kargs):
        """api.getFilter(filter_id) - Retrieve a Filter
        
        http://developers.app.net/docs/resources/filter/lifecycle/#retrieve-a-filter"""
        ep={'url_params': ['filter_id'], 'group': 'filter', 'name': 'get', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['filters/'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/filter/lifecycle/#retrieve-a-filter', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve a Filter'}
        url=self.geturl(ep , filter_id)
        return self.genRequest(url, ep, kargs)

    def updateFilter(self , filter_id, **kargs):
        """api.updateFilter(filter_id) - Update a Filter
        
        http://developers.app.net/docs/resources/filter/lifecycle/#update-a-filter"""
        ep={'url_params': ['filter_id'], 'group': 'filter', 'name': 'update', 'array_params': [], 'data_params': ['filter'], 'get_params': [], 'url': ['filters/'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/filter/lifecycle/#update-a-filter', 'scope': 'basic', 'method': 'PUT', 'description': 'Update a Filter'}
        url=self.geturl(ep , filter_id)
        return self.genRequest(url, ep, kargs)

    def destroyFilter(self , filter_id, **kargs):
        """api.destroyFilter(filter_id) - Delete a Filter
        
        http://developers.app.net/docs/resources/filter/lifecycle/#delete-a-filter"""
        ep={'url_params': ['filter_id'], 'group': 'filter', 'name': 'destroy', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['filters/'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/filter/lifecycle/#delete-a-filter', 'scope': 'basic', 'method': 'DELETE', 'description': 'Delete a Filter'}
        url=self.geturl(ep , filter_id)
        return self.genRequest(url, ep, kargs)

    def getUserFilter(self , **kargs):
        """api.getUserFilter() - Get the current User's Filters
        
        http://developers.app.net/docs/resources/filter/lifecycle/#get-current-users-filters"""
        ep={'url_params': [], 'group': 'filter', 'name': 'getUser', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['filters'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/filter/lifecycle/#get-current-users-filters', 'scope': 'basic', 'method': 'GET', 'description': "Get the current User's Filters"}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def destroyUserFilter(self , **kargs):
        """api.destroyUserFilter() - Delete the current User's Filters
        
        http://developers.app.net/docs/resources/filter/lifecycle/#delete-all-of-the-current-users-filters"""
        ep={'url_params': [], 'group': 'filter', 'name': 'destroyUser', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['filters'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/filter/lifecycle/#delete-all-of-the-current-users-filters', 'scope': 'basic', 'method': 'DELETE', 'description': "Delete the current User's Filters"}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getInteraction(self , **kargs):
        """api.getInteraction() - Retrieve Interactions with the current User
        
        http://developers.app.net/docs/resources/interaction/"""
        ep={'url_params': [], 'group': 'interaction', 'name': 'get', 'array_params': [], 'data_params': [], 'get_params': ['pagination'], 'url': ['users/me/interactions'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/interaction/', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve Interactions with the current User'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def updateMarker(self , **kargs):
        """api.updateMarker() - Update a Stream Marker
        
        http://developers.app.net/docs/resources/stream-marker/#update-a-stream-marker"""
        ep={'url_params': [], 'group': 'marker', 'name': 'update', 'array_params': [], 'data_params': ['marker'], 'get_params': [], 'url': ['posts/marker'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/stream-marker/#update-a-stream-marker', 'scope': 'basic', 'method': 'POST', 'description': 'Update a Stream Marker'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def processText(self , **kargs):
        """api.processText() - Process text
        
        http://developers.app.net/docs/resources/text-processor/"""
        ep={'url_params': [], 'group': 'text', 'name': 'process', 'array_params': [], 'data_params': ['post_or_message'], 'get_params': [], 'url': ['text/process'], 'token': 'Any', 'link': 'http://developers.app.net/docs/resources/text-processor/', 'scope': 'basic', 'method': 'POST', 'description': 'Process text'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getToken(self , **kargs):
        """api.getToken() - Retrieve the current token
        
        http://developers.app.net/docs/resources/token/#retrieve-current-token"""
        ep={'url_params': [], 'group': 'token', 'name': 'get', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['token'], 'token': 'Any', 'link': 'http://developers.app.net/docs/resources/token/#retrieve-current-token', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve the current token'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getAuthorizedIdsToken(self , **kargs):
        """api.getAuthorizedIdsToken() - Retrieve authorized User IDs for an app
        
        http://developers.app.net/docs/resources/token/#retrieve-authorized-user-ids-for-an-app"""
        ep={'url_params': [], 'group': 'token', 'name': 'getAuthorizedIds', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['tokens/user_ids'], 'token': 'App', 'link': 'http://developers.app.net/docs/resources/token/#retrieve-authorized-user-ids-for-an-app', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve authorized User IDs for an app'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getAuthorizedToken(self , **kargs):
        """api.getAuthorizedToken() - Retrieve authorized User tokens for an app
        
        http://developers.app.net/docs/resources/token/#retrieve-authorized-user-tokens-for-an-app"""
        ep={'url_params': [], 'group': 'token', 'name': 'getAuthorized', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['apps/me/token'], 'token': 'App', 'link': 'http://developers.app.net/docs/resources/token/#retrieve-authorized-user-tokens-for-an-app', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve authorized User tokens for an app'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getPlace(self , factual_id, **kargs):
        """api.getPlace(factual_id) - Retrieve a Place
        
        http://developers.app.net/docs/resources/place/#retrieve-a-place"""
        ep={'url_params': ['factual_id'], 'group': 'place', 'name': 'get', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['places/'], 'token': 'Any', 'link': 'http://developers.app.net/docs/resources/place/#retrieve-a-place', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve a Place'}
        url=self.geturl(ep , factual_id)
        return self.genRequest(url, ep, kargs)

    def searchPlace(self , **kargs):
        """api.searchPlace() - Search for Places
        
        http://developers.app.net/docs/resources/place/#search-for-a-place"""
        ep={'url_params': [], 'group': 'place', 'name': 'search', 'array_params': [], 'data_params': [], 'get_params': ['place_search'], 'url': ['places/search'], 'token': 'User', 'link': 'http://developers.app.net/docs/resources/place/#search-for-a-place', 'scope': 'basic', 'method': 'GET', 'description': 'Search for Places'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def showExplore(self , **kargs):
        """api.showExplore() - Retrieve all Explore Streams
        
        http://developers.app.net/docs/resources/explore/#retrieve-all-explore-streams"""
        ep={'url_params': [], 'group': 'explore', 'name': 'show', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['posts/stream/explore'], 'token': 'None', 'link': 'http://developers.app.net/docs/resources/explore/#retrieve-all-explore-streams', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve all Explore Streams'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getExplore(self , slug, **kargs):
        """api.getExplore(slug) - Retrieve an Explore Stream
        
        http://developers.app.net/docs/resources/explore/#retrieve-an-explore-stream"""
        ep={'url_params': ['slug'], 'group': 'explore', 'name': 'get', 'array_params': [], 'data_params': [], 'get_params': ['pagination'], 'url': ['posts/stream/explore/'], 'token': 'None', 'link': 'http://developers.app.net/docs/resources/explore/#retrieve-an-explore-stream', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve an Explore Stream'}
        url=self.geturl(ep , slug)
        return self.genRequest(url, ep, kargs)

    def getConfig(self , **kargs):
        """api.getConfig() - Retrieve the Configuration Object
        
        http://developers.app.net/docs/resources/config/#retrieve-the-configuration-object"""
        ep={'url_params': [], 'group': 'config', 'name': 'get', 'array_params': [], 'data_params': [], 'get_params': [], 'url': ['config/'], 'token': 'None', 'link': 'http://developers.app.net/docs/resources/config/#retrieve-the-configuration-object', 'scope': 'basic', 'method': 'GET', 'description': 'Retrieve the Configuration Object'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)
