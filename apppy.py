import requests
import itertools
import json

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
    """ Usage: apppy(access_token=None)"""
    
    public_api_anchor = "alpha-api.app.net"

    def set_accesstoken(self, token):
        self._access_token = token
    def get_accesstoken(self):
        return self._access_token
    def del_accesstoken(self):
        self._access_token = None
    access_token = property(get_accesstoken, set_accesstoken, del_accesstoken, "The access token")

    def set_gimme_429(self, token):
        self._gimme_429 = token
    def get_gimme_429(self):
        return self._gimme_429
    def del_gimme_429(self):
        self._gimme_429 = False
    gimme_429 = property(get_gimme_429, set_gimme_429, del_gimme_429,
                         "If true, tell API to return 429 error codes, instead of automaticallyh sleeping")

    def __init__(self, access_token=None):
        self.gimme_429 = False
        if access_token:
            self.set_accesstoken(access_token)

    def generateAuthUrl(self, client_id, client_secret, redirect_url, scopes=None):
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
        
    def getAuthResponse(self, code):
        #generate POST request
        url = "https://alpha.app.net/oauth/access_token"
        post_data = {'client_id':self.client_id,
        'client_secret':self.client_secret,
        'grant_type':'authorization_code',
        'redirect_uri':self.redirect_url,
        'code':code}

        r = requests.post(url,data=post_data)

        return r.text

    def geturl(self, e, *opts):
        lparam=len(e['url_params'])
        if len(opts) < lparam:
            raise
        url=self.base+"".join(sum(itertools.izip_longest(e['url'], opts[:lparam], fillvalue=''), ()))
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
            if c == "data" and (type(pl) == type('') or type(pl) == type(u'')):
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
            
        #print params
        if self.access_token:
            rp['headers']['Authorization'] = "Bearer " + self.access_token
        
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
                sleep(float(r.header['RetryAfter']))
                # repeat the call
                continue

            return r
        return r
    base="https://alpha-api.app.net/stream/0/"
    parameter_category={u'general_channel': [u'channel_types', u'include_marker', u'include_read', u'include_recent_message', u'include_annotations', u'include_user_annotations', u'include_message_annotations'], u'stream': [u'object_types', u'type', u'filter_id', u'key'], u'post_or_message': [u'text'], u'file_ids': [u'ids'], u'file': [u'text', u'reply_to', u'annotations', u'entities', u'machine_only'], u'marker': [u'id', u'name', u'percentage'], u'message': [u'text', u'reply_to', u'annotations', u'entities', u'machine_only', u'destinations'], u'message_ids': [u'ids'], u'general_message': [u'include_muted', u'include_deleted', u'include_machine', u'include_annotations', u'include_user_annotations', u'include_message_annotations', u'include_html'], u'content': u'content', u'channel': [u'readers', u'writers', u'annotations', u'type'], u'placesearch': [u'latitude', u'longitude', u'q', u'radius', u'count', u'remove_closed', u'altitude', u'horizontal_accuracy', u'vertical_accuracy'], u'channel_ids': [u'ids'], u'user_ids': [u'ids'], u'user': [u'name', u'locale', u'timezone', u'description'], u'post': [u'text', u'reply_to', u'machine_only', u'annotations', u'entities'], u'general_file': [u'file_types', u'include_incomplete', u'include_private', u'include_annotations', u'include_file_annotations', u'include_user_annotations'], u'general_post': [u'include_muted', u'include_deleted', u'include_directed_posts', u'include_machine', u'include_starred_by', u'include_reposters', u'include_annotations', u'include_post_annotations', u'include_user_annotations', u'include_html'], u'pagination': [u'since_id', u'before_id', u'count'], u'general_user': [u'include_annotations', u'include_user_annotations', u'include_html'], u'cover': u'image', u'filter': [u'name', u'match_policy', u'clauses'], u'avatar': u'image', u'post_ids': [u'ids']}
    allscopes=[u'files', u'update_profile', u'stream', u'messages', u'public_messages', u'export', u'write_post', u'basic', u'follow', u'email']

    def getUser(self , user_id, **kargs):
    	"""api.getUser(user_id) - Retrieve a User
        
        http://developers.app.net/docs/resources/user/lookup/#retrieve-a-user"""
        ep={u'url_params': [u'user_id'], u'group': u'user', u'name': u'get', u'array_params': [], u'data_params': [], u'get_params': [u'general_user'], u'method': u'GET', u'token': u'None', u'link': u'http://developers.app.net/docs/resources/user/lookup/#retrieve-a-user', u'url': [u'users/'], u'scope': u'basic', u'id': u'100', u'description': u'Retrieve a User'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def updateUser(self , **kargs):
    	"""api.updateUser() - Update a User
        
        http://developers.app.net/docs/resources/user/profile/#update-a-user"""
        ep={u'url_params': [], u'group': u'user', u'name': u'update', u'array_params': [], u'data_params': [u'user'], u'get_params': [u'general_user'], u'method': u'PUT', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/user/profile/#update-a-user', u'url': [u'users/me'], u'scope': u'update_profile', u'id': u'101', u'description': u'Update a User'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def partialUpdateUser(self , **kargs):
    	"""api.partialUpdateUser() - Partially Update a User
        
        http://developers.app.net/docs/resources/user/profile/#partially-update-a-user"""
        ep={u'url_params': [], u'group': u'user', u'name': u'partialUpdate', u'array_params': [], u'data_params': [u'user'], u'get_params': [u'general_user'], u'method': u'PATCH', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/user/profile/#partially-update-a-user', u'url': [u'users/me'], u'scope': u'update_profile', u'id': u'124', u'description': u'Partially Update a User'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getAvatarUser(self , user_id, **kargs):
    	"""api.getAvatarUser(user_id) - Retrieve a User's avatar image
        
        http://developers.app.net/docs/resources/user/profile/#retrieve-a-users-avatar-image"""
        ep={u'url_params': [u'user_id'], u'group': u'user', u'name': u'getAvatar', u'array_params': [], u'data_params': [], u'get_params': [], u'method': u'GET', u'token': u'None', u'link': u'http://developers.app.net/docs/resources/user/profile/#retrieve-a-users-avatar-image', u'url': [u'users/', u'/avatar'], u'scope': u'basic', u'id': u'102', u'description': u"Retrieve a User's avatar image"}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def updateAvatarUser(self , **kargs):
    	"""api.updateAvatarUser() - Update a User's avatar image
        
        http://developers.app.net/docs/resources/user/profile/#update-a-users-avatar-image"""
        ep={u'url_params': [], u'group': u'user', u'name': u'updateAvatar', u'array_params': [], u'data_params': [u'avatar'], u'get_params': [], u'method': u'POST-RAW', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/user/profile/#update-a-users-avatar-image', u'url': [u'users/me/avatar'], u'scope': u'update_profile', u'id': u'103', u'description': u"Update a User's avatar image"}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getCoverUser(self , user_id, **kargs):
    	"""api.getCoverUser(user_id) - Retrieve a User's cover image
        
        http://developers.app.net/docs/resources/user/profile/#retrieve-a-users-cover-image"""
        ep={u'url_params': [u'user_id'], u'group': u'user', u'name': u'getCover', u'array_params': [], u'data_params': [], u'get_params': [], u'method': u'GET', u'token': u'None', u'link': u'http://developers.app.net/docs/resources/user/profile/#retrieve-a-users-cover-image', u'url': [u'users/', u'/cover'], u'scope': u'basic', u'id': u'104', u'description': u"Retrieve a User's cover image"}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def updateCoverUser(self , **kargs):
    	"""api.updateCoverUser() - Update a User's cover image
        
        http://developers.app.net/docs/resources/user/profile/#update-a-users-cover-image"""
        ep={u'url_params': [], u'group': u'user', u'name': u'updateCover', u'array_params': [], u'data_params': [u'cover'], u'get_params': [], u'method': u'POST-RAW', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/user/profile/#update-a-users-cover-image', u'url': [u'users/me/cover'], u'scope': u'update_profile', u'id': u'105', u'description': u"Update a User's cover image"}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def followUser(self , user_id, **kargs):
    	"""api.followUser(user_id) - Follow a User
        
        http://developers.app.net/docs/resources/user/following/#follow-a-user"""
        ep={u'url_params': [u'user_id'], u'group': u'user', u'name': u'follow', u'array_params': [], u'data_params': [], u'get_params': [u'general_user'], u'method': u'POST', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/user/following/#follow-a-user', u'url': [u'users/', u'/follow'], u'scope': u'follow', u'id': u'106', u'description': u'Follow a User'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def unfollowUser(self , user_id, **kargs):
    	"""api.unfollowUser(user_id) - Unfollow a User
        
        http://developers.app.net/docs/resources/user/following/#unfollow-a-user"""
        ep={u'url_params': [u'user_id'], u'group': u'user', u'name': u'unfollow', u'array_params': [], u'data_params': [], u'get_params': [u'general_user'], u'method': u'DELETE', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/user/following/#unfollow-a-user', u'url': [u'users/', u'/follow'], u'scope': u'follow', u'id': u'107', u'description': u'Unfollow a User'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def muteUser(self , user_id, **kargs):
    	"""api.muteUser(user_id) - Mute a User
        
        http://developers.app.net/docs/resources/user/muting/#mute-a-user"""
        ep={u'url_params': [u'user_id'], u'group': u'user', u'name': u'mute', u'array_params': [], u'data_params': [], u'get_params': [u'general_user'], u'method': u'POST', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/user/muting/#mute-a-user', u'url': [u'users/', u'/mute'], u'scope': u'follow', u'id': u'108', u'description': u'Mute a User'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def unmuteUser(self , user_id, **kargs):
    	"""api.unmuteUser(user_id) - Unmute a User
        
        http://developers.app.net/docs/resources/user/muting/#unmute-a-user"""
        ep={u'url_params': [u'user_id'], u'group': u'user', u'name': u'unmute', u'array_params': [], u'data_params': [], u'get_params': [u'general_user'], u'method': u'DELETE', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/user/muting/#unmute-a-user', u'url': [u'users/', u'/mute'], u'scope': u'follow', u'id': u'109', u'description': u'Unmute a User'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def blockUser(self , user_id, **kargs):
    	"""api.blockUser(user_id) - Block a User
        
        http://developers.app.net/docs/resources/user/blocking/#block-a-user"""
        ep={u'url_params': [u'user_id'], u'group': u'user', u'name': u'block', u'array_params': [], u'data_params': [], u'get_params': [u'general_user'], u'method': u'POST', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/user/blocking/#block-a-user', u'url': [u'users/', u'/block'], u'scope': u'follow', u'id': u'110', u'description': u'Block a User'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def unblockUser(self , user_id, **kargs):
    	"""api.unblockUser(user_id) - Unblock a User
        
        http://developers.app.net/docs/resources/user/blocking/#unblock-a-user"""
        ep={u'url_params': [u'user_id'], u'group': u'user', u'name': u'unblock', u'array_params': [], u'data_params': [], u'get_params': [u'general_user'], u'method': u'DELETE', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/user/blocking/#unblock-a-user', u'url': [u'users/', u'/block'], u'scope': u'follow', u'id': u'111', u'description': u'Unblock a User'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def getListUser(self , **kargs):
    	"""api.getListUser(ids=[...]) - Retrieve multiple Users
        
        http://developers.app.net/docs/resources/user/lookup/#retrieve-multiple-users"""
        ep={u'url_params': [], u'group': u'user', u'name': u'getList', u'array_params': [u'user_ids'], u'data_params': [], u'get_params': [u'general_user'], u'method': u'GET', u'token': u'Any', u'link': u'http://developers.app.net/docs/resources/user/lookup/#retrieve-multiple-users', u'url': [u'users'], u'scope': u'basic', u'id': u'112', u'description': u'Retrieve multiple Users'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def searchUser(self , **kargs):
    	"""api.searchUser() - Search for Users
        
        http://developers.app.net/docs/resources/user/lookup/#search-for-users"""
        ep={u'url_params': [], u'group': u'user', u'name': u'search', u'array_params': [], u'data_params': [], u'get_params': [u'general_user'], u'method': u'GET', u'token': u'Any', u'link': u'http://developers.app.net/docs/resources/user/lookup/#search-for-users', u'url': [u'users/search'], u'scope': u'basic', u'id': u'113', u'description': u'Search for Users'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getFollowingUser(self , user_id, **kargs):
    	"""api.getFollowingUser(user_id) - Retrieve Users a User is following
        
        http://developers.app.net/docs/resources/user/following/#list-users-a-user-is-following"""
        ep={u'url_params': [u'user_id'], u'group': u'user', u'name': u'getFollowing', u'array_params': [], u'data_params': [], u'get_params': [u'general_user', u'pagination'], u'method': u'GET', u'token': u'Any', u'link': u'http://developers.app.net/docs/resources/user/following/#list-users-a-user-is-following', u'url': [u'users/', u'/following'], u'scope': u'basic', u'id': u'114', u'description': u'Retrieve Users a User is following'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def getFollowersUser(self , user_id, **kargs):
    	"""api.getFollowersUser(user_id) - Retrieve Users following a User
        
        http://developers.app.net/docs/resources/user/following/#list-users-following-a-user"""
        ep={u'url_params': [u'user_id'], u'group': u'user', u'name': u'getFollowers', u'array_params': [], u'data_params': [], u'get_params': [u'general_user', u'pagination'], u'method': u'GET', u'token': u'Any', u'link': u'http://developers.app.net/docs/resources/user/following/#list-users-following-a-user', u'url': [u'users/', u'/followers'], u'scope': u'basic', u'id': u'115', u'description': u'Retrieve Users following a User'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def getFollowingIdsUser(self , user_id, **kargs):
    	"""api.getFollowingIdsUser(user_id) - Retrieve IDs of Users a User is following
        
        http://developers.app.net/docs/resources/user/following/#list-user-ids-a-user-is-following"""
        ep={u'url_params': [u'user_id'], u'group': u'user', u'name': u'getFollowingIds', u'array_params': [], u'data_params': [], u'get_params': [], u'method': u'GET', u'token': u'Any', u'link': u'http://developers.app.net/docs/resources/user/following/#list-user-ids-a-user-is-following', u'url': [u'users/', u'/following/ids'], u'scope': u'basic', u'id': u'116', u'description': u'Retrieve IDs of Users a User is following'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def getFollowerIdsUser(self , user_id, **kargs):
    	"""api.getFollowerIdsUser(user_id) - Retrieve IDs of Users following a User
        
        http://developers.app.net/docs/resources/user/following/#list-user-ids-following-a-user"""
        ep={u'url_params': [u'user_id'], u'group': u'user', u'name': u'getFollowerIds', u'array_params': [], u'data_params': [], u'get_params': [], u'method': u'GET', u'token': u'Any', u'link': u'http://developers.app.net/docs/resources/user/following/#list-user-ids-following-a-user', u'url': [u'users/', u'/followers/ids'], u'scope': u'basic', u'id': u'117', u'description': u'Retrieve IDs of Users following a User'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def getMutedUser(self , user_id, **kargs):
    	"""api.getMutedUser(user_id) - Retrieve muted Users
        
        http://developers.app.net/docs/resources/user/muting/#list-muted-users"""
        ep={u'url_params': [u'user_id'], u'group': u'user', u'name': u'getMuted', u'array_params': [], u'data_params': [], u'get_params': [u'general_user'], u'method': u'GET', u'token': u'Any', u'link': u'http://developers.app.net/docs/resources/user/muting/#list-muted-users', u'url': [u'users/', u'/muted'], u'scope': u'basic', u'id': u'118', u'description': u'Retrieve muted Users'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def getMutedListUser(self , **kargs):
    	"""api.getMutedListUser(ids=[...]) - Retrieve muted User IDs for multiple Users
        
        http://developers.app.net/docs/resources/user/muting/#retrieve-muted-user-ids-for-multiple-users"""
        ep={u'url_params': [], u'group': u'user', u'name': u'getMutedList', u'array_params': [u'user_ids'], u'data_params': [], u'get_params': [], u'method': u'GET', u'token': u'App', u'link': u'http://developers.app.net/docs/resources/user/muting/#retrieve-muted-user-ids-for-multiple-users', u'url': [u'users/muted/ids'], u'scope': u'basic', u'id': u'119', u'description': u'Retrieve muted User IDs for multiple Users'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getBlockedUser(self , user_id, **kargs):
    	"""api.getBlockedUser(user_id) - Retrieve blocked Users
        
        http://developers.app.net/docs/resources/user/blocking/#list-blocked-users"""
        ep={u'url_params': [u'user_id'], u'group': u'user', u'name': u'getBlocked', u'array_params': [], u'data_params': [], u'get_params': [u'general_user'], u'method': u'GET', u'token': u'Any', u'link': u'http://developers.app.net/docs/resources/user/blocking/#list-blocked-users', u'url': [u'users/', u'/blocked'], u'scope': u'basic', u'id': u'120', u'description': u'Retrieve blocked Users'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def getBlockedListUser(self , **kargs):
    	"""api.getBlockedListUser(ids=[...]) - Retrieve blocked User IDs for multiple Users
        
        http://developers.app.net/docs/resources/user/blocking/#retrieve-blocked-user-ids-for-multiple-users"""
        ep={u'url_params': [], u'group': u'user', u'name': u'getBlockedList', u'array_params': [u'user_ids'], u'data_params': [], u'get_params': [], u'method': u'GET', u'token': u'App', u'link': u'http://developers.app.net/docs/resources/user/blocking/#retrieve-blocked-user-ids-for-multiple-users', u'url': [u'users/blocked/ids'], u'scope': u'basic', u'id': u'121', u'description': u'Retrieve blocked User IDs for multiple Users'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getRepostersUser(self , post_id, **kargs):
    	"""api.getRepostersUser(post_id) - Retrieve Users who reposted a Post
        
        http://developers.app.net/docs/resources/user/post-interactions/#list-users-who-have-reposted-a-post"""
        ep={u'url_params': [u'post_id'], u'group': u'user', u'name': u'getReposters', u'array_params': [], u'data_params': [], u'get_params': [u'general_user'], u'method': u'GET', u'token': u'Any', u'link': u'http://developers.app.net/docs/resources/user/post-interactions/#list-users-who-have-reposted-a-post', u'url': [u'posts/', u'/reposters'], u'scope': u'basic', u'id': u'122', u'description': u'Retrieve Users who reposted a Post'}
        url=self.geturl(ep , post_id)
        return self.genRequest(url, ep, kargs)

    def getStarsUser(self , post_id, **kargs):
    	"""api.getStarsUser(post_id) - Retrieve Users who starred a Post
        
        http://developers.app.net/docs/resources/user/post-interactions/#list-users-who-have-starred-a-post"""
        ep={u'url_params': [u'post_id'], u'group': u'user', u'name': u'getStars', u'array_params': [], u'data_params': [], u'get_params': [u'general_user'], u'method': u'GET', u'token': u'Any', u'link': u'http://developers.app.net/docs/resources/user/post-interactions/#list-users-who-have-starred-a-post', u'url': [u'posts/', u'/stars'], u'scope': u'basic', u'id': u'123', u'description': u'Retrieve Users who starred a Post'}
        url=self.geturl(ep , post_id)
        return self.genRequest(url, ep, kargs)

    def createPost(self , **kargs):
    	"""api.createPost() - Create a Post
        
        http://developers.app.net/docs/resources/post/lifecycle/#create-a-post"""
        ep={u'url_params': [], u'group': u'post', u'name': u'create', u'array_params': [], u'data_params': [u'post'], u'get_params': [u'general_post'], u'method': u'POST', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/post/lifecycle/#create-a-post', u'url': [u'posts'], u'scope': u'write_post', u'id': u'200', u'description': u'Create a Post'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getPost(self , post_id, **kargs):
    	"""api.getPost(post_id) - Retrieve a Post
        
        http://developers.app.net/docs/resources/post/lookup/#retrieve-a-post"""
        ep={u'url_params': [u'post_id'], u'group': u'post', u'name': u'get', u'array_params': [], u'data_params': [], u'get_params': [u'general_post'], u'method': u'GET', u'token': u'None', u'link': u'http://developers.app.net/docs/resources/post/lookup/#retrieve-a-post', u'url': [u'posts/'], u'scope': u'basic', u'id': u'201', u'description': u'Retrieve a Post'}
        url=self.geturl(ep , post_id)
        return self.genRequest(url, ep, kargs)

    def destroyPost(self , post_id, **kargs):
    	"""api.destroyPost(post_id) - Delete a Post
        
        http://developers.app.net/docs/resources/post/lifecycle/#delete-a-post"""
        ep={u'url_params': [u'post_id'], u'group': u'post', u'name': u'destroy', u'array_params': [], u'data_params': [], u'get_params': [u'general_post'], u'method': u'DELETE', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/post/lifecycle/#delete-a-post', u'url': [u'posts/'], u'scope': u'write_post', u'id': u'202', u'description': u'Delete a Post'}
        url=self.geturl(ep , post_id)
        return self.genRequest(url, ep, kargs)

    def repostPost(self , post_id, **kargs):
    	"""api.repostPost(post_id) - Repost a Post
        
        http://developers.app.net/docs/resources/post/reposts/#repost-a-post"""
        ep={u'url_params': [u'post_id'], u'group': u'post', u'name': u'repost', u'array_params': [], u'data_params': [], u'get_params': [u'general_post'], u'method': u'POST', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/post/reposts/#repost-a-post', u'url': [u'posts/', u'/repost'], u'scope': u'write_post', u'id': u'203', u'description': u'Repost a Post'}
        url=self.geturl(ep , post_id)
        return self.genRequest(url, ep, kargs)

    def unrepostPost(self , post_id, **kargs):
    	"""api.unrepostPost(post_id) - Unrepost a Post
        
        http://developers.app.net/docs/resources/post/reposts/#unrepost-a-post"""
        ep={u'url_params': [u'post_id'], u'group': u'post', u'name': u'unrepost', u'array_params': [], u'data_params': [], u'get_params': [u'general_post'], u'method': u'DELETE', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/post/reposts/#unrepost-a-post', u'url': [u'posts/', u'/repost'], u'scope': u'write_post', u'id': u'204', u'description': u'Unrepost a Post'}
        url=self.geturl(ep , post_id)
        return self.genRequest(url, ep, kargs)

    def starPost(self , post_id, **kargs):
    	"""api.starPost(post_id) - Star a Post
        
        http://developers.app.net/docs/resources/post/stars/#star-a-post"""
        ep={u'url_params': [u'post_id'], u'group': u'post', u'name': u'star', u'array_params': [], u'data_params': [], u'get_params': [u'general_post'], u'method': u'POST', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/post/stars/#star-a-post', u'url': [u'posts/', u'/star'], u'scope': u'write_post', u'id': u'205', u'description': u'Star a Post'}
        url=self.geturl(ep , post_id)
        return self.genRequest(url, ep, kargs)

    def unstarPost(self , post_id, **kargs):
    	"""api.unstarPost(post_id) - Unstar a Post
        
        http://developers.app.net/docs/resources/post/stars/#unstar-a-post"""
        ep={u'url_params': [u'post_id'], u'group': u'post', u'name': u'unstar', u'array_params': [], u'data_params': [], u'get_params': [u'general_post'], u'method': u'DELETE', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/post/stars/#unstar-a-post', u'url': [u'posts/', u'/star'], u'scope': u'write_post', u'id': u'206', u'description': u'Unstar a Post'}
        url=self.geturl(ep , post_id)
        return self.genRequest(url, ep, kargs)

    def getListPost(self , **kargs):
    	"""api.getListPost(ids=[...]) - Retrieve multiple Posts
        
        http://developers.app.net/docs/resources/post/lookup/#retrieve-multiple-posts"""
        ep={u'url_params': [], u'group': u'post', u'name': u'getList', u'array_params': [u'post_ids'], u'data_params': [], u'get_params': [u'general_post'], u'method': u'GET', u'token': u'Any', u'link': u'http://developers.app.net/docs/resources/post/lookup/#retrieve-multiple-posts', u'url': [u'posts'], u'scope': u'basic', u'id': u'207', u'description': u'Retrieve multiple Posts'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getUserPost(self , user_id, **kargs):
    	"""api.getUserPost(user_id) - Retrieve a User's posts
        
        http://developers.app.net/docs/resources/post/streams/#retrieve-posts-created-by-a-user"""
        ep={u'url_params': [u'user_id'], u'group': u'post', u'name': u'getUser', u'array_params': [], u'data_params': [], u'get_params': [u'general_post', u'pagination'], u'method': u'GET', u'token': u'None', u'link': u'http://developers.app.net/docs/resources/post/streams/#retrieve-posts-created-by-a-user', u'url': [u'users/', u'/posts'], u'scope': u'basic', u'id': u'208', u'description': u"Retrieve a User's posts"}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def getUserStarredPost(self , user_id, **kargs):
    	"""api.getUserStarredPost(user_id) - Retrieve a User's starred posts
        
        http://developers.app.net/docs/resources/post/stars/#retrieve-posts-starred-by-a-user"""
        ep={u'url_params': [u'user_id'], u'group': u'post', u'name': u'getUserStarred', u'array_params': [], u'data_params': [], u'get_params': [u'general_post', u'pagination'], u'method': u'GET', u'token': u'None', u'link': u'http://developers.app.net/docs/resources/post/stars/#retrieve-posts-starred-by-a-user', u'url': [u'users/', u'/stars'], u'scope': u'basic', u'id': u'209', u'description': u"Retrieve a User's starred posts"}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def getUserMentionsPost(self , user_id, **kargs):
    	"""api.getUserMentionsPost(user_id) - Retrieve Posts mentioning a User
        
        http://developers.app.net/docs/resources/post/streams/#retrieve-posts-mentioning-a-user"""
        ep={u'url_params': [u'user_id'], u'group': u'post', u'name': u'getUserMentions', u'array_params': [], u'data_params': [], u'get_params': [u'general_post', u'pagination'], u'method': u'GET', u'token': u'Any', u'link': u'http://developers.app.net/docs/resources/post/streams/#retrieve-posts-mentioning-a-user', u'url': [u'users/', u'/mentions'], u'scope': u'basic', u'id': u'210', u'description': u'Retrieve Posts mentioning a User'}
        url=self.geturl(ep , user_id)
        return self.genRequest(url, ep, kargs)

    def getHashtagPost(self , hashtag, **kargs):
    	"""api.getHashtagPost(hashtag) - Retrieve Posts containing a hashtag
        
        http://developers.app.net/docs/resources/post/streams/#retrieve-tagged-posts"""
        ep={u'url_params': [u'hashtag'], u'group': u'post', u'name': u'getHashtag', u'array_params': [], u'data_params': [], u'get_params': [u'general_post', u'pagination'], u'method': u'GET', u'token': u'None', u'link': u'http://developers.app.net/docs/resources/post/streams/#retrieve-tagged-posts', u'url': [u'posts/tag/'], u'scope': u'basic', u'id': u'211', u'description': u'Retrieve Posts containing a hashtag'}
        url=self.geturl(ep , hashtag)
        return self.genRequest(url, ep, kargs)

    def getThreadPost(self , post_id, **kargs):
    	"""api.getThreadPost(post_id) - Retrieve replies to a Post
        
        http://developers.app.net/docs/resources/post/replies"""
        ep={u'url_params': [u'post_id'], u'group': u'post', u'name': u'getThread', u'array_params': [], u'data_params': [], u'get_params': [u'general_post', u'pagination'], u'method': u'GET', u'token': u'Any', u'link': u'http://developers.app.net/docs/resources/post/replies', u'url': [u'posts/', u'/replies'], u'scope': u'basic', u'id': u'212', u'description': u'Retrieve replies to a Post'}
        url=self.geturl(ep , post_id)
        return self.genRequest(url, ep, kargs)

    def getUserStreamPost(self , **kargs):
    	"""api.getUserStreamPost() - Retrieve a User's personalized stream
        
        http://developers.app.net/docs/resources/post/streams/#retrieve-a-users-personalized-stream"""
        ep={u'url_params': [], u'group': u'post', u'name': u'getUserStream', u'array_params': [], u'data_params': [], u'get_params': [u'general_post', u'pagination'], u'method': u'GET', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/post/streams/#retrieve-a-users-personalized-stream', u'url': [u'posts/stream'], u'scope': u'stream', u'id': u'213', u'description': u"Retrieve a User's personalized stream"}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getUnifiedStreamStream(self , **kargs):
    	"""api.getUnifiedStreamStream() - Retrieve a User's unified stream
        
        http://developers.app.net/docs/resources/post/streams/#retrieve-a-users-unified-stream"""
        ep={u'url_params': [], u'group': u'stream', u'name': u'getUnifiedStream', u'array_params': [], u'data_params': [], u'get_params': [u'general_post', u'pagination'], u'method': u'GET', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/post/streams/#retrieve-a-users-unified-stream', u'url': [u'posts/stream/unified'], u'scope': u'stream', u'id': u'214', u'description': u"Retrieve a User's unified stream"}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getGlobalPost(self , **kargs):
    	"""api.getGlobalPost() - Retrieve the Global stream
        
        http://developers.app.net/docs/resources/post/streams/#retrieve-the-global-stream"""
        ep={u'url_params': [], u'group': u'post', u'name': u'getGlobal', u'array_params': [], u'data_params': [], u'get_params': [u'general_post', u'pagination'], u'method': u'GET', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/post/streams/#retrieve-the-global-stream', u'url': [u'posts/stream/global'], u'scope': u'basic', u'id': u'215', u'description': u'Retrieve the Global stream'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def reportPost(self , post_id, **kargs):
    	"""api.reportPost(post_id) - Report a Post
        
        http://developers.app.net/docs/resources/post/report/#report-a-post"""
        ep={u'url_params': [u'post_id'], u'group': u'post', u'name': u'report', u'array_params': [], u'data_params': [], u'get_params': [u'general_post'], u'method': u'POST', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/post/report/#report-a-post', u'url': [u'posts/', u'/report'], u'scope': u'basic', u'id': u'216', u'description': u'Report a Post'}
        url=self.geturl(ep , post_id)
        return self.genRequest(url, ep, kargs)

    def getUserSubscribedChannel(self , **kargs):
    	"""api.getUserSubscribedChannel() - Get current user's subscribed channels
        
        http://developers.app.net/docs/resources/channel/subscriptions/#get-current-users-subscribed-channels"""
        ep={u'url_params': [], u'group': u'channel', u'name': u'getUserSubscribed', u'array_params': [], u'data_params': [], u'get_params': [u'general_channel', u'pagination'], u'method': u'GET', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/channel/subscriptions/#get-current-users-subscribed-channels', u'url': [u'channels'], u'scope': u'messages', u'id': u'300', u'description': u"Get current user's subscribed channels"}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def createChannel(self , **kargs):
    	"""api.createChannel() - Create a Channel
        
        http://developers.app.net/docs/resources/channel/lifecycle/#create-a-channel"""
        ep={u'url_params': [], u'group': u'channel', u'name': u'create', u'array_params': [], u'data_params': [u'channel'], u'get_params': [u'general_channel'], u'method': u'POST', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/channel/lifecycle/#create-a-channel', u'url': [u'channels'], u'scope': u'messages', u'id': u'301', u'description': u'Create a Channel'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getChannel(self , channel_id, **kargs):
    	"""api.getChannel(channel_id) - Retrieve a Channel
        
        http://developers.app.net/docs/resources/channel/lookup/#retrieve-a-channel"""
        ep={u'url_params': [u'channel_id'], u'group': u'channel', u'name': u'get', u'array_params': [], u'data_params': [], u'get_params': [u'general_channel'], u'method': u'GET', u'token': u'Varies', u'link': u'http://developers.app.net/docs/resources/channel/lookup/#retrieve-a-channel', u'url': [u'channels/'], u'scope': u'messages', u'id': u'302', u'description': u'Retrieve a Channel'}
        url=self.geturl(ep , channel_id)
        return self.genRequest(url, ep, kargs)

    def getListChannel(self , **kargs):
    	"""api.getListChannel(ids=[...]) - Retrieve multiple Channels
        
        http://developers.app.net/docs/resources/channel/lookup/#retrieve-multiple-channels"""
        ep={u'url_params': [], u'group': u'channel', u'name': u'getList', u'array_params': [u'channel_ids'], u'data_params': [], u'get_params': [u'general_channel'], u'method': u'GET', u'token': u'Varies', u'link': u'http://developers.app.net/docs/resources/channel/lookup/#retrieve-multiple-channels', u'url': [u'channels'], u'scope': u'messages', u'id': u'303', u'description': u'Retrieve multiple Channels'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getCreatedChannel(self , **kargs):
    	"""api.getCreatedChannel() - Retrieve my Channels
        
        http://developers.app.net/docs/resources/channel/lookup/#retrieve-my-channels"""
        ep={u'url_params': [], u'group': u'channel', u'name': u'getCreated', u'array_params': [], u'data_params': [], u'get_params': [u'general_channel', u'pagination'], u'method': u'GET', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/channel/lookup/#retrieve-my-channels', u'url': [u'users/me/channels'], u'scope': u'messages', u'id': u'304', u'description': u'Retrieve my Channels'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getUnreadCountChannel(self , **kargs):
    	"""api.getUnreadCountChannel() - Retrieve number of unread PM Channels
        
        http://developers.app.net/docs/resources/channel/lookup/#retrieve-number-of-unread-pm-channels"""
        ep={u'url_params': [], u'group': u'channel', u'name': u'getUnreadCount', u'array_params': [], u'data_params': [], u'get_params': [], u'method': u'GET', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/channel/lookup/#retrieve-number-of-unread-pm-channels', u'url': [u'users/me/channels/pm/num_unread'], u'scope': u'messages', u'id': u'305', u'description': u'Retrieve number of unread PM Channels'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def updateChannel(self , channel_id, **kargs):
    	"""api.updateChannel(channel_id) - Update a Channel
        
        http://developers.app.net/docs/resources/channel/lifecycle/#update-a-channel"""
        ep={u'url_params': [u'channel_id'], u'group': u'channel', u'name': u'update', u'array_params': [], u'data_params': [u'channel'], u'get_params': [u'general_channel'], u'method': u'PUT', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/channel/lifecycle/#update-a-channel', u'url': [u'channels/'], u'scope': u'messages', u'id': u'306', u'description': u'Update a Channel'}
        url=self.geturl(ep , channel_id)
        return self.genRequest(url, ep, kargs)

    def subscribeChannel(self , channel_id, **kargs):
    	"""api.subscribeChannel(channel_id) - Subscribe to a Channel
        
        http://developers.app.net/docs/resources/channel/subscriptions/#subscribe-to-a-channel"""
        ep={u'url_params': [u'channel_id'], u'group': u'channel', u'name': u'subscribe', u'array_params': [], u'data_params': [], u'get_params': [u'general_channel'], u'method': u'POST', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/channel/subscriptions/#subscribe-to-a-channel', u'url': [u'channels/', u'/subscribe'], u'scope': u'messages', u'id': u'307', u'description': u'Subscribe to a Channel'}
        url=self.geturl(ep , channel_id)
        return self.genRequest(url, ep, kargs)

    def unsubscribeChannel(self , channel_id, **kargs):
    	"""api.unsubscribeChannel(channel_id) - Unsubscribe from a Channel
        
        http://developers.app.net/docs/resources/channel/subscriptions/#unsubscribe-from-a-channel"""
        ep={u'url_params': [u'channel_id'], u'group': u'channel', u'name': u'unsubscribe', u'array_params': [], u'data_params': [], u'get_params': [u'general_channel'], u'method': u'DELETE', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/channel/subscriptions/#unsubscribe-from-a-channel', u'url': [u'channels/', u'/subscribe'], u'scope': u'messages', u'id': u'308', u'description': u'Unsubscribe from a Channel'}
        url=self.geturl(ep , channel_id)
        return self.genRequest(url, ep, kargs)

    def getSubscribersChannel(self , channel_id, **kargs):
    	"""api.getSubscribersChannel(channel_id) - Retrieve users subscribed to a Channel
        
        http://developers.app.net/docs/resources/channel/subscriptions/#retrieve-users-subscribed-to-a-channel"""
        ep={u'url_params': [u'channel_id'], u'group': u'channel', u'name': u'getSubscribers', u'array_params': [], u'data_params': [], u'get_params': [u'general_channel', u'pagination'], u'method': u'GET', u'token': u'None', u'link': u'http://developers.app.net/docs/resources/channel/subscriptions/#retrieve-users-subscribed-to-a-channel', u'url': [u'channels/', u'/subscribers'], u'scope': u'messages', u'id': u'309', u'description': u'Retrieve users subscribed to a Channel'}
        url=self.geturl(ep , channel_id)
        return self.genRequest(url, ep, kargs)

    def getSubscriberIdsChannel(self , channel_id, **kargs):
    	"""api.getSubscriberIdsChannel(channel_id) - Retrieve user ids subscribed to a Channel
        
        http://developers.app.net/docs/resources/channel/subscriptions/#retrieve-user-ids-subscribed-to-a-channel"""
        ep={u'url_params': [u'channel_id'], u'group': u'channel', u'name': u'getSubscriberIds', u'array_params': [], u'data_params': [], u'get_params': [], u'method': u'GET', u'token': u'None', u'link': u'http://developers.app.net/docs/resources/channel/subscriptions/#retrieve-user-ids-subscribed-to-a-channel', u'url': [u'channels/', u'/subscribers/ids'], u'scope': u'messages', u'id': u'310', u'description': u'Retrieve user ids subscribed to a Channel'}
        url=self.geturl(ep , channel_id)
        return self.genRequest(url, ep, kargs)

    def getSubscriberIdListChannel(self , **kargs):
    	"""api.getSubscriberIdListChannel(ids=[...]) - Retrieve user ids subscribed to multiple Channels
        
        http://developers.app.net/docs/resources/channel/subscriptions/#retrieve-user-ids-subscribed-to-a-channel"""
        ep={u'url_params': [], u'group': u'channel', u'name': u'getSubscriberIdList', u'array_params': [u'channel_ids'], u'data_params': [], u'get_params': [], u'method': u'GET', u'token': u'Any', u'link': u'http://developers.app.net/docs/resources/channel/subscriptions/#retrieve-user-ids-subscribed-to-a-channel', u'url': [u'channels/subscribers/ids'], u'scope': u'messages', u'id': u'311', u'description': u'Retrieve user ids subscribed to multiple Channels'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def muteChannel(self , channel_id, **kargs):
    	"""api.muteChannel(channel_id) - Mute a Channel
        
        http://developers.app.net/docs/resources/channel/muting/#mute-a-channel"""
        ep={u'url_params': [u'channel_id'], u'group': u'channel', u'name': u'mute', u'array_params': [], u'data_params': [], u'get_params': [u'general_channel'], u'method': u'POST', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/channel/muting/#mute-a-channel', u'url': [u'channels/', u'/mute'], u'scope': u'messages', u'id': u'312', u'description': u'Mute a Channel'}
        url=self.geturl(ep , channel_id)
        return self.genRequest(url, ep, kargs)

    def unmuteChannel(self , channel_id, **kargs):
    	"""api.unmuteChannel(channel_id) - Unmute a Channel
        
        http://developers.app.net/docs/resources/channel/muting/#unmute-a-channel"""
        ep={u'url_params': [u'channel_id'], u'group': u'channel', u'name': u'unmute', u'array_params': [], u'data_params': [], u'get_params': [u'general_channel'], u'method': u'DELETE', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/channel/muting/#unmute-a-channel', u'url': [u'channels/', u'/mute'], u'scope': u'messages', u'id': u'313', u'description': u'Unmute a Channel'}
        url=self.geturl(ep , channel_id)
        return self.genRequest(url, ep, kargs)

    def getMutedChannel(self , **kargs):
    	"""api.getMutedChannel() - Get current user's muted Channels
        
        http://developers.app.net/docs/resources/channel/muting/#get-current-users-muted-channels"""
        ep={u'url_params': [], u'group': u'channel', u'name': u'getMuted', u'array_params': [], u'data_params': [], u'get_params': [u'general_channel'], u'method': u'GET', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/channel/muting/#get-current-users-muted-channels', u'url': [u'users/me/channels/muted'], u'scope': u'messages', u'id': u'314', u'description': u"Get current user's muted Channels"}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getChannelMessage(self , channel_id, **kargs):
    	"""api.getChannelMessage(channel_id) - Retrieve the Messages in a Channel
        
        http://developers.app.net/docs/resources/message/lifecycle/#retrieve-the-messages-in-a-channel"""
        ep={u'url_params': [u'channel_id'], u'group': u'message', u'name': u'getChannel', u'array_params': [], u'data_params': [], u'get_params': [u'general_message', u'pagination'], u'method': u'GET', u'token': u'None', u'link': u'http://developers.app.net/docs/resources/message/lifecycle/#retrieve-the-messages-in-a-channel', u'url': [u'channels/', u'/messages'], u'scope': u'messages', u'id': u'400', u'description': u'Retrieve the Messages in a Channel'}
        url=self.geturl(ep , channel_id)
        return self.genRequest(url, ep, kargs)

    def createMessage(self , channel_id, **kargs):
    	"""api.createMessage(channel_id) - Create a Message
        
        http://developers.app.net/docs/resources/message/lifecycle/#create-a-message"""
        ep={u'url_params': [u'channel_id'], u'group': u'message', u'name': u'create', u'array_params': [], u'data_params': [u'message'], u'get_params': [u'general_message'], u'method': u'POST', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/message/lifecycle/#create-a-message', u'url': [u'channels/', u'/messages'], u'scope': u'messages', u'id': u'401', u'description': u'Create a Message'}
        url=self.geturl(ep , channel_id)
        return self.genRequest(url, ep, kargs)

    def getMessage(self , channel_id, message_id, **kargs):
    	"""api.getMessage(channel_id, message_id) - Retrieve a Message
        
        http://developers.app.net/docs/resources/message/lookup/#retrieve-a-message"""
        ep={u'url_params': [u'channel_id', u'message_id'], u'group': u'message', u'name': u'get', u'array_params': [], u'data_params': [], u'get_params': [u'general_message'], u'method': u'GET', u'token': u'None', u'link': u'http://developers.app.net/docs/resources/message/lookup/#retrieve-a-message', u'url': [u'channels/', u'/messages/'], u'scope': u'messages', u'id': u'402', u'description': u'Retrieve a Message'}
        url=self.geturl(ep , channel_id, message_id)
        return self.genRequest(url, ep, kargs)

    def getListMessage(self , **kargs):
    	"""api.getListMessage(ids=[...]) - Retrieve multiple Messages
        
        http://developers.app.net/docs/resources/message/lookup/#retrieve-multiple-messages"""
        ep={u'url_params': [], u'group': u'message', u'name': u'getList', u'array_params': [u'message_ids'], u'data_params': [], u'get_params': [u'general_message'], u'method': u'GET', u'token': u'None', u'link': u'http://developers.app.net/docs/resources/message/lookup/#retrieve-multiple-messages', u'url': [u'channels/messages'], u'scope': u'messages', u'id': u'403', u'description': u'Retrieve multiple Messages'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getUserMessage(self , **kargs):
    	"""api.getUserMessage() - Retrieve my Messages
        
        http://developers.app.net/docs/resources/message/lookup/#retrieve-my-messages"""
        ep={u'url_params': [], u'group': u'message', u'name': u'getUser', u'array_params': [], u'data_params': [], u'get_params': [u'general_message'], u'method': u'GET', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/message/lookup/#retrieve-my-messages', u'url': [u'users/me/messages'], u'scope': u'messages', u'id': u'404', u'description': u'Retrieve my Messages'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def destroyMessage(self , channel_id, message_id, **kargs):
    	"""api.destroyMessage(channel_id, message_id) - Delete a Message
        
        http://developers.app.net/docs/resources/message/lifecycle/#delete-a-message"""
        ep={u'url_params': [u'channel_id', u'message_id'], u'group': u'message', u'name': u'destroy', u'array_params': [], u'data_params': [], u'get_params': [u'general_message'], u'method': u'DELETE', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/message/lifecycle/#delete-a-message', u'url': [u'channels/', u'/messages/'], u'scope': u'messages', u'id': u'405', u'description': u'Delete a Message'}
        url=self.geturl(ep , channel_id, message_id)
        return self.genRequest(url, ep, kargs)

    def createFile(self , **kargs):
    	"""api.createFile() - Create a File
        
        http://developers.app.net/docs/resources/file/lifecycle/#create-a-file"""
        ep={u'url_params': [], u'group': u'file', u'name': u'create', u'array_params': [], u'data_params': [u'file'], u'get_params': [u'general_file'], u'method': u'POST-RAW', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/file/lifecycle/#create-a-file', u'url': [u'files'], u'scope': u'files', u'id': u'500', u'description': u'Create a File'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def createPlaceholderFile(self , **kargs):
    	"""api.createPlaceholderFile() - Create a File Placeholder
        
        http://developers.app.net/docs/resources/file/lifecycle/#create-a-file"""
        ep={u'url_params': [], u'group': u'file', u'name': u'createPlaceholder', u'array_params': [], u'data_params': [u'file'], u'get_params': [u'general_file'], u'method': u'POST', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/file/lifecycle/#create-a-file', u'url': [u'files'], u'scope': u'files', u'id': u'501', u'description': u'Create a File Placeholder'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getFile(self , file_id, **kargs):
    	"""api.getFile(file_id) - Retrieve a File
        
        http://developers.app.net/docs/resources/file/lookup/#retrieve-a-file"""
        ep={u'url_params': [u'file_id'], u'group': u'file', u'name': u'get', u'array_params': [], u'data_params': [], u'get_params': [u'general_file'], u'method': u'GET', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/file/lookup/#retrieve-a-file', u'url': [u'files/'], u'scope': u'basic', u'id': u'502', u'description': u'Retrieve a File'}
        url=self.geturl(ep , file_id)
        return self.genRequest(url, ep, kargs)

    def getListFile(self , **kargs):
    	"""api.getListFile(ids=[...]) - Retrieve multiple Files
        
        http://developers.app.net/docs/resources/file/lookup/#retrieve-multiple-files"""
        ep={u'url_params': [], u'group': u'file', u'name': u'getList', u'array_params': [u'file_ids'], u'data_params': [], u'get_params': [u'general_file'], u'method': u'GET', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/file/lookup/#retrieve-multiple-files', u'url': [u'files'], u'scope': u'files', u'id': u'503', u'description': u'Retrieve multiple Files'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def destroyFile(self , file_id, **kargs):
    	"""api.destroyFile(file_id) - Delete a File
        
        http://developers.app.net/docs/resources/file/lifecycle/#delete-a-file"""
        ep={u'url_params': [u'file_id'], u'group': u'file', u'name': u'destroy', u'array_params': [], u'data_params': [], u'get_params': [u'general_file'], u'method': u'DELETE', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/file/lifecycle/#delete-a-file', u'url': [u'files/'], u'scope': u'files', u'id': u'504', u'description': u'Delete a File'}
        url=self.geturl(ep , file_id)
        return self.genRequest(url, ep, kargs)

    def getUserFile(self , **kargs):
    	"""api.getUserFile() - Retrieve my Files
        
        http://developers.app.net/docs/resources/file/lookup/#retrieve-my-files"""
        ep={u'url_params': [], u'group': u'file', u'name': u'getUser', u'array_params': [], u'data_params': [], u'get_params': [u'general_file', u'pagination'], u'method': u'GET', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/file/lookup/#retrieve-my-files', u'url': [u'users/me/files'], u'scope': u'files', u'id': u'505', u'description': u'Retrieve my Files'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def updateFile(self , file_id, **kargs):
    	"""api.updateFile(file_id) - Update a File
        
        http://developers.app.net/docs/resources/file/lifecycle/#update-a-file"""
        ep={u'url_params': [u'file_id'], u'group': u'file', u'name': u'update', u'array_params': [], u'data_params': [u'file'], u'get_params': [u'general_file'], u'method': u'PUT', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/file/lifecycle/#update-a-file', u'url': [u'files/'], u'scope': u'files', u'id': u'506', u'description': u'Update a File'}
        url=self.geturl(ep , file_id)
        return self.genRequest(url, ep, kargs)

    def getContentFile(self , file_id, **kargs):
    	"""api.getContentFile(file_id) - Get File content
        
        http://developers.app.net/docs/resources/file/content/#get-file-content"""
        ep={u'url_params': [u'file_id'], u'group': u'file', u'name': u'getContent', u'array_params': [], u'data_params': [], u'get_params': [], u'method': u'GET', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/file/content/#get-file-content', u'url': [u'files/', u'/content'], u'scope': u'files', u'id': u'507', u'description': u'Get File content'}
        url=self.geturl(ep , file_id)
        return self.genRequest(url, ep, kargs)

    def setContentFile(self , file_id, **kargs):
    	"""api.setContentFile(file_id) - Set File content
        
        http://developers.app.net/docs/resources/file/content/#set-file-content"""
        ep={u'url_params': [u'file_id'], u'group': u'file', u'name': u'setContent', u'array_params': [], u'data_params': [u'content'], u'get_params': [], u'method': u'PUT', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/file/content/#set-file-content', u'url': [u'files/', u'/content'], u'scope': u'files', u'id': u'508', u'description': u'Set File content'}
        url=self.geturl(ep , file_id)
        return self.genRequest(url, ep, kargs)

    def createStream(self , **kargs):
    	"""api.createStream() - Create a Stream
        
        http://developers.app.net/docs/resources/stream/lifecycle/#create-a-stream"""
        ep={u'url_params': [], u'group': u'stream', u'name': u'create', u'array_params': [], u'data_params': [u'stream'], u'get_params': [], u'method': u'POST', u'token': u'App', u'link': u'http://developers.app.net/docs/resources/stream/lifecycle/#create-a-stream', u'url': [u'streams'], u'scope': u'basic', u'id': u'600', u'description': u'Create a Stream'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getStream(self , stream_id, **kargs):
    	"""api.getStream(stream_id) - Retrieve a Stream
        
        http://developers.app.net/docs/resources/stream/lifecycle/#retrieve-a-stream"""
        ep={u'url_params': [u'stream_id'], u'group': u'stream', u'name': u'get', u'array_params': [], u'data_params': [], u'get_params': [], u'method': u'GET', u'token': u'App', u'link': u'http://developers.app.net/docs/resources/stream/lifecycle/#retrieve-a-stream', u'url': [u'streams/'], u'scope': u'basic', u'id': u'601', u'description': u'Retrieve a Stream'}
        url=self.geturl(ep , stream_id)
        return self.genRequest(url, ep, kargs)

    def updateStream(self , stream_id, **kargs):
    	"""api.updateStream(stream_id) - Update a Stream
        
        http://developers.app.net/docs/resources/stream/lifecycle/#update-a-stream"""
        ep={u'url_params': [u'stream_id'], u'group': u'stream', u'name': u'update', u'array_params': [], u'data_params': [u'stream'], u'get_params': [], u'method': u'PUT', u'token': u'App', u'link': u'http://developers.app.net/docs/resources/stream/lifecycle/#update-a-stream', u'url': [u'streams/'], u'scope': u'basic', u'id': u'602', u'description': u'Update a Stream'}
        url=self.geturl(ep , stream_id)
        return self.genRequest(url, ep, kargs)

    def destroyStream(self , stream_id, **kargs):
    	"""api.destroyStream(stream_id) - Delete a Stream
        
        http://developers.app.net/docs/resources/stream/lifecycle/#delete-a-stream"""
        ep={u'url_params': [u'stream_id'], u'group': u'stream', u'name': u'destroy', u'array_params': [], u'data_params': [], u'get_params': [], u'method': u'DELETE', u'token': u'App', u'link': u'http://developers.app.net/docs/resources/stream/lifecycle/#delete-a-stream', u'url': [u'streams/'], u'scope': u'basic', u'id': u'603', u'description': u'Delete a Stream'}
        url=self.geturl(ep , stream_id)
        return self.genRequest(url, ep, kargs)

    def getAllStream(self , **kargs):
    	"""api.getAllStream() - Retrieve all Streams for the current Token
        
        http://developers.app.net/docs/resources/stream/lifecycle/#get-current-tokens-streams"""
        ep={u'url_params': [], u'group': u'stream', u'name': u'getAll', u'array_params': [], u'data_params': [], u'get_params': [], u'method': u'GET', u'token': u'App', u'link': u'http://developers.app.net/docs/resources/stream/lifecycle/#get-current-tokens-streams', u'url': [u'streams'], u'scope': u'basic', u'id': u'604', u'description': u'Retrieve all Streams for the current Token'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def destroyAllStream(self , **kargs):
    	"""api.destroyAllStream() - Delete all Streams for the current Token
        
        http://developers.app.net/docs/resources/stream/lifecycle/#delete-all-of-the-current-users-streams"""
        ep={u'url_params': [], u'group': u'stream', u'name': u'destroyAll', u'array_params': [], u'data_params': [], u'get_params': [], u'method': u'DELETE', u'token': u'App', u'link': u'http://developers.app.net/docs/resources/stream/lifecycle/#delete-all-of-the-current-users-streams', u'url': [u'streams'], u'scope': u'basic', u'id': u'605', u'description': u'Delete all Streams for the current Token'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def createFilter(self , **kargs):
    	"""api.createFilter() - Create a Filter
        
        http://developers.app.net/docs/resources/filter/lifecycle/#create-a-filter"""
        ep={u'url_params': [], u'group': u'filter', u'name': u'create', u'array_params': [], u'data_params': [u'filter'], u'get_params': [], u'method': u'POST', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/filter/lifecycle/#create-a-filter', u'url': [u'filters'], u'scope': u'basic', u'id': u'700', u'description': u'Create a Filter'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getFilter(self , filter_id, **kargs):
    	"""api.getFilter(filter_id) - Retrieve a Filter
        
        http://developers.app.net/docs/resources/filter/lifecycle/#retrieve-a-filter"""
        ep={u'url_params': [u'filter_id'], u'group': u'filter', u'name': u'get', u'array_params': [], u'data_params': [], u'get_params': [], u'method': u'GET', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/filter/lifecycle/#retrieve-a-filter', u'url': [u'filters/'], u'scope': u'basic', u'id': u'701', u'description': u'Retrieve a Filter'}
        url=self.geturl(ep , filter_id)
        return self.genRequest(url, ep, kargs)

    def updateFilter(self , filter_id, **kargs):
    	"""api.updateFilter(filter_id) - Update a Filter
        
        http://developers.app.net/docs/resources/filter/lifecycle/#update-a-filter"""
        ep={u'url_params': [u'filter_id'], u'group': u'filter', u'name': u'update', u'array_params': [], u'data_params': [u'filter'], u'get_params': [], u'method': u'PUT', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/filter/lifecycle/#update-a-filter', u'url': [u'filters/'], u'scope': u'basic', u'id': u'702', u'description': u'Update a Filter'}
        url=self.geturl(ep , filter_id)
        return self.genRequest(url, ep, kargs)

    def destroyFilter(self , filter_id, **kargs):
    	"""api.destroyFilter(filter_id) - Delete a Filter
        
        http://developers.app.net/docs/resources/filter/lifecycle/#delete-a-filter"""
        ep={u'url_params': [u'filter_id'], u'group': u'filter', u'name': u'destroy', u'array_params': [], u'data_params': [], u'get_params': [], u'method': u'DELETE', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/filter/lifecycle/#delete-a-filter', u'url': [u'filters/'], u'scope': u'basic', u'id': u'703', u'description': u'Delete a Filter'}
        url=self.geturl(ep , filter_id)
        return self.genRequest(url, ep, kargs)

    def getUserFilter(self , **kargs):
    	"""api.getUserFilter() - Get the current User's Filters
        
        http://developers.app.net/docs/resources/filter/lifecycle/#get-current-users-filters"""
        ep={u'url_params': [], u'group': u'filter', u'name': u'getUser', u'array_params': [], u'data_params': [], u'get_params': [], u'method': u'GET', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/filter/lifecycle/#get-current-users-filters', u'url': [u'filters'], u'scope': u'basic', u'id': u'704', u'description': u"Get the current User's Filters"}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def destroyUserFilter(self , **kargs):
    	"""api.destroyUserFilter() - Delete the current User's Filters
        
        http://developers.app.net/docs/resources/filter/lifecycle/#delete-all-of-the-current-users-filters"""
        ep={u'url_params': [], u'group': u'filter', u'name': u'destroyUser', u'array_params': [], u'data_params': [], u'get_params': [], u'method': u'DELETE', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/filter/lifecycle/#delete-all-of-the-current-users-filters', u'url': [u'filters'], u'scope': u'basic', u'id': u'705', u'description': u"Delete the current User's Filters"}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getInteraction(self , **kargs):
    	"""api.getInteraction() - Retrieve Interactions with the current User
        
        http://developers.app.net/docs/resources/interaction/"""
        ep={u'url_params': [], u'group': u'interaction', u'name': u'get', u'array_params': [], u'data_params': [], u'get_params': [u'pagination'], u'method': u'GET', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/interaction/', u'url': [u'users/me/interactions'], u'scope': u'basic', u'id': u'800', u'description': u'Retrieve Interactions with the current User'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def updateMarker(self , **kargs):
    	"""api.updateMarker() - Update a Stream Marker
        
        http://developers.app.net/docs/resources/stream-marker/#update-a-stream-marker"""
        ep={u'url_params': [], u'group': u'marker', u'name': u'update', u'array_params': [], u'data_params': [u'marker'], u'get_params': [], u'method': u'POST', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/stream-marker/#update-a-stream-marker', u'url': [u'posts/marker'], u'scope': u'basic', u'id': u'900', u'description': u'Update a Stream Marker'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def processText(self , **kargs):
    	"""api.processText() - Process text
        
        http://developers.app.net/docs/resources/text-processor/"""
        ep={u'url_params': [], u'group': u'text', u'name': u'process', u'array_params': [], u'data_params': [u'post_or_message'], u'get_params': [], u'method': u'POST', u'token': u'Any', u'link': u'http://developers.app.net/docs/resources/text-processor/', u'url': [u'text/process'], u'scope': u'basic', u'id': u'1000', u'description': u'Process text'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getToken(self , **kargs):
    	"""api.getToken() - Retrieve the current token
        
        http://developers.app.net/docs/resources/token/#retrieve-current-token"""
        ep={u'url_params': [], u'group': u'token', u'name': u'get', u'array_params': [], u'data_params': [], u'get_params': [], u'method': u'GET', u'token': u'Any', u'link': u'http://developers.app.net/docs/resources/token/#retrieve-current-token', u'url': [u'token'], u'scope': u'basic', u'id': u'1100', u'description': u'Retrieve the current token'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getAuthorizedIdsToken(self , **kargs):
    	"""api.getAuthorizedIdsToken() - Retrieve authorized User IDs for an app
        
        http://developers.app.net/docs/resources/token/#retrieve-authorized-user-ids-for-an-app"""
        ep={u'url_params': [], u'group': u'token', u'name': u'getAuthorizedIds', u'array_params': [], u'data_params': [], u'get_params': [], u'method': u'GET', u'token': u'App', u'link': u'http://developers.app.net/docs/resources/token/#retrieve-authorized-user-ids-for-an-app', u'url': [u'tokens/user_ids'], u'scope': u'basic', u'id': u'1101', u'description': u'Retrieve authorized User IDs for an app'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getAuthorizedToken(self , **kargs):
    	"""api.getAuthorizedToken() - Retrieve authorized User tokens for an app
        
        http://developers.app.net/docs/resources/token/#retrieve-authorized-user-tokens-for-an-app"""
        ep={u'url_params': [], u'group': u'token', u'name': u'getAuthorized', u'array_params': [], u'data_params': [], u'get_params': [], u'method': u'GET', u'token': u'App', u'link': u'http://developers.app.net/docs/resources/token/#retrieve-authorized-user-tokens-for-an-app', u'url': [u'apps/me/token'], u'scope': u'basic', u'id': u'1102', u'description': u'Retrieve authorized User tokens for an app'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getPlace(self , factual_id, **kargs):
    	"""api.getPlace(factual_id) - Retrieve a Place
        
        http://developers.app.net/docs/resources/place/#retrieve-a-place"""
        ep={u'url_params': [u'factual_id'], u'group': u'place', u'name': u'get', u'array_params': [], u'data_params': [], u'get_params': [], u'method': u'GET', u'token': u'Any', u'link': u'http://developers.app.net/docs/resources/place/#retrieve-a-place', u'url': [u'places/'], u'scope': u'basic', u'id': u'1200', u'description': u'Retrieve a Place'}
        url=self.geturl(ep , factual_id)
        return self.genRequest(url, ep, kargs)

    def searchPlace(self , **kargs):
    	"""api.searchPlace() - Search for Places
        
        http://developers.app.net/docs/resources/place/#search-for-a-place"""
        ep={u'url_params': [], u'group': u'place', u'name': u'search', u'array_params': [], u'data_params': [], u'get_params': [u'placesearch'], u'method': u'GET', u'token': u'User', u'link': u'http://developers.app.net/docs/resources/place/#search-for-a-place', u'url': [u'places/search'], u'scope': u'basic', u'id': u'1201', u'description': u'Search for Places'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def showExplore(self , **kargs):
    	"""api.showExplore() - Retrieve all Explore Streams
        
        http://developers.app.net/docs/resources/explore/#retrieve-all-explore-streams"""
        ep={u'url_params': [], u'group': u'explore', u'name': u'show', u'array_params': [], u'data_params': [], u'get_params': [], u'method': u'GET', u'token': u'None', u'link': u'http://developers.app.net/docs/resources/explore/#retrieve-all-explore-streams', u'url': [u'posts/stream/explore'], u'scope': u'basic', u'id': u'1300', u'description': u'Retrieve all Explore Streams'}
        url=self.geturl(ep )
        return self.genRequest(url, ep, kargs)

    def getExplore(self , slug, **kargs):
    	"""api.getExplore(slug) - Retrieve an Explore Stream
        
        http://developers.app.net/docs/resources/explore/#retrieve-an-explore-stream"""
        ep={u'url_params': [u'slug'], u'group': u'explore', u'name': u'get', u'array_params': [], u'data_params': [], u'get_params': [u'pagination'], u'method': u'GET', u'token': u'None', u'link': u'http://developers.app.net/docs/resources/explore/#retrieve-an-explore-stream', u'url': [u'stream/explore/'], u'scope': u'basic', u'id': u'1301', u'description': u'Retrieve an Explore Stream'}
        url=self.geturl(ep , slug)
        return self.genRequest(url, ep, kargs)
