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

Apppy.py is machine generated. It uses [Duerig's endpoints.json library](https://github.com/duerig/appnet.js/blob/master/hbs/endpoints.json) to generate all the endpoints. The code that generates the endpoints is not part 
of this distribution, so while I will work hard to fix any problems, I won't accept pull requests against 
apppy.py (but I will use them to correct the source files that generate apppy.py). This file is also machine 
generated.

##License:

MIT License

Copyright 2013 Michael Vezie

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

##Endpoints

###user
####* api.getUser(user_id) - [Retrieve a User](http://developers.app.net/docs/resources/user/lookup/#retrieve-a-user)

####* api.updateUser() - [Update a User](http://developers.app.net/docs/resources/user/profile/#update-a-user)

####* api.partialUpdateUser() - [Partially Update a User](http://developers.app.net/docs/resources/user/profile/#partially-update-a-user)

####* api.getAvatarUser(user_id) - [Retrieve a User's avatar image](http://developers.app.net/docs/resources/user/profile/#retrieve-a-users-avatar-image)

####* api.updateAvatarUser() - [Update a User's avatar image](http://developers.app.net/docs/resources/user/profile/#update-a-users-avatar-image)

####* api.getCoverUser(user_id) - [Retrieve a User's cover image](http://developers.app.net/docs/resources/user/profile/#retrieve-a-users-cover-image)

####* api.updateCoverUser() - [Update a User's cover image](http://developers.app.net/docs/resources/user/profile/#update-a-users-cover-image)

####* api.followUser(user_id) - [Follow a User](http://developers.app.net/docs/resources/user/following/#follow-a-user)

####* api.unfollowUser(user_id) - [Unfollow a User](http://developers.app.net/docs/resources/user/following/#unfollow-a-user)

####* api.muteUser(user_id) - [Mute a User](http://developers.app.net/docs/resources/user/muting/#mute-a-user)

####* api.unmuteUser(user_id) - [Unmute a User](http://developers.app.net/docs/resources/user/muting/#unmute-a-user)

####* api.blockUser(user_id) - [Block a User](http://developers.app.net/docs/resources/user/blocking/#block-a-user)

####* api.unblockUser(user_id) - [Unblock a User](http://developers.app.net/docs/resources/user/blocking/#unblock-a-user)

####* api.getListUser(ids=[...]) - [Retrieve multiple Users](http://developers.app.net/docs/resources/user/lookup/#retrieve-multiple-users)

####* api.searchUser() - [Search for Users](http://developers.app.net/docs/resources/user/lookup/#search-for-users)

####* api.getFollowingUser(user_id) - [Retrieve Users a User is following](http://developers.app.net/docs/resources/user/following/#list-users-a-user-is-following)

####* api.getFollowersUser(user_id) - [Retrieve Users following a User](http://developers.app.net/docs/resources/user/following/#list-users-following-a-user)

####* api.getFollowingIdsUser(user_id) - [Retrieve IDs of Users a User is following](http://developers.app.net/docs/resources/user/following/#list-user-ids-a-user-is-following)

####* api.getFollowerIdsUser(user_id) - [Retrieve IDs of Users following a User](http://developers.app.net/docs/resources/user/following/#list-user-ids-following-a-user)

####* api.getMutedUser(user_id) - [Retrieve muted Users](http://developers.app.net/docs/resources/user/muting/#list-muted-users)

####* api.getMutedListUser(ids=[...]) - [Retrieve muted User IDs for multiple Users](http://developers.app.net/docs/resources/user/muting/#retrieve-muted-user-ids-for-multiple-users)

####* api.getBlockedUser(user_id) - [Retrieve blocked Users](http://developers.app.net/docs/resources/user/blocking/#list-blocked-users)

####* api.getBlockedListUser(ids=[...]) - [Retrieve blocked User IDs for multiple Users](http://developers.app.net/docs/resources/user/blocking/#retrieve-blocked-user-ids-for-multiple-users)

####* api.getRepostersUser(post_id) - [Retrieve Users who reposted a Post](http://developers.app.net/docs/resources/user/post-interactions/#list-users-who-have-reposted-a-post)

####* api.getStarsUser(post_id) - [Retrieve Users who starred a Post](http://developers.app.net/docs/resources/user/post-interactions/#list-users-who-have-starred-a-post)
###post
####* api.createPost() - [Create a Post](http://developers.app.net/docs/resources/post/lifecycle/#create-a-post)

####* api.getPost(post_id) - [Retrieve a Post](http://developers.app.net/docs/resources/post/lookup/#retrieve-a-post)

####* api.destroyPost(post_id) - [Delete a Post](http://developers.app.net/docs/resources/post/lifecycle/#delete-a-post)

####* api.repostPost(post_id) - [Repost a Post](http://developers.app.net/docs/resources/post/reposts/#repost-a-post)

####* api.unrepostPost(post_id) - [Unrepost a Post](http://developers.app.net/docs/resources/post/reposts/#unrepost-a-post)

####* api.starPost(post_id) - [Star a Post](http://developers.app.net/docs/resources/post/stars/#star-a-post)

####* api.unstarPost(post_id) - [Unstar a Post](http://developers.app.net/docs/resources/post/stars/#unstar-a-post)

####* api.getListPost(ids=[...]) - [Retrieve multiple Posts](http://developers.app.net/docs/resources/post/lookup/#retrieve-multiple-posts)

####* api.getUserPost(user_id) - [Retrieve a User's posts](http://developers.app.net/docs/resources/post/streams/#retrieve-posts-created-by-a-user)

####* api.getUserStarredPost(user_id) - [Retrieve a User's starred posts](http://developers.app.net/docs/resources/post/stars/#retrieve-posts-starred-by-a-user)

####* api.getUserMentionsPost(user_id) - [Retrieve Posts mentioning a User](http://developers.app.net/docs/resources/post/streams/#retrieve-posts-mentioning-a-user)

####* api.getHashtagPost(hashtag) - [Retrieve Posts containing a hashtag](http://developers.app.net/docs/resources/post/streams/#retrieve-tagged-posts)

####* api.getThreadPost(post_id) - [Retrieve replies to a Post](http://developers.app.net/docs/resources/post/replies)

####* api.getUserStreamPost() - [Retrieve a User's personalized stream](http://developers.app.net/docs/resources/post/streams/#retrieve-a-users-personalized-stream)
###stream
####* api.getUnifiedStreamStream() - [Retrieve a User's unified stream](http://developers.app.net/docs/resources/post/streams/#retrieve-a-users-unified-stream)
###post
####* api.getGlobalPost() - [Retrieve the Global stream](http://developers.app.net/docs/resources/post/streams/#retrieve-the-global-stream)

####* api.reportPost(post_id) - [Report a Post](http://developers.app.net/docs/resources/post/report/#report-a-post)
###channel
####* api.getUserSubscribedChannel() - [Get current user's subscribed channels](http://developers.app.net/docs/resources/channel/subscriptions/#get-current-users-subscribed-channels)

####* api.createChannel() - [Create a Channel](http://developers.app.net/docs/resources/channel/lifecycle/#create-a-channel)

####* api.getChannel(channel_id) - [Retrieve a Channel](http://developers.app.net/docs/resources/channel/lookup/#retrieve-a-channel)

####* api.getListChannel(ids=[...]) - [Retrieve multiple Channels](http://developers.app.net/docs/resources/channel/lookup/#retrieve-multiple-channels)

####* api.getCreatedChannel() - [Retrieve my Channels](http://developers.app.net/docs/resources/channel/lookup/#retrieve-my-channels)

####* api.getUnreadCountChannel() - [Retrieve number of unread PM Channels](http://developers.app.net/docs/resources/channel/lookup/#retrieve-number-of-unread-pm-channels)

####* api.updateChannel(channel_id) - [Update a Channel](http://developers.app.net/docs/resources/channel/lifecycle/#update-a-channel)

####* api.subscribeChannel(channel_id) - [Subscribe to a Channel](http://developers.app.net/docs/resources/channel/subscriptions/#subscribe-to-a-channel)

####* api.unsubscribeChannel(channel_id) - [Unsubscribe from a Channel](http://developers.app.net/docs/resources/channel/subscriptions/#unsubscribe-from-a-channel)

####* api.getSubscribersChannel(channel_id) - [Retrieve users subscribed to a Channel](http://developers.app.net/docs/resources/channel/subscriptions/#retrieve-users-subscribed-to-a-channel)

####* api.getSubscriberIdsChannel(channel_id) - [Retrieve user ids subscribed to a Channel](http://developers.app.net/docs/resources/channel/subscriptions/#retrieve-user-ids-subscribed-to-a-channel)

####* api.getSubscriberIdListChannel(ids=[...]) - [Retrieve user ids subscribed to multiple Channels](http://developers.app.net/docs/resources/channel/subscriptions/#retrieve-user-ids-subscribed-to-a-channel)

####* api.muteChannel(channel_id) - [Mute a Channel](http://developers.app.net/docs/resources/channel/muting/#mute-a-channel)

####* api.unmuteChannel(channel_id) - [Unmute a Channel](http://developers.app.net/docs/resources/channel/muting/#unmute-a-channel)

####* api.getMutedChannel() - [Get current user's muted Channels](http://developers.app.net/docs/resources/channel/muting/#get-current-users-muted-channels)
###message
####* api.getChannelMessage(channel_id) - [Retrieve the Messages in a Channel](http://developers.app.net/docs/resources/message/lifecycle/#retrieve-the-messages-in-a-channel)

####* api.createMessage(channel_id) - [Create a Message](http://developers.app.net/docs/resources/message/lifecycle/#create-a-message)

####* api.getMessage(channel_id, message_id) - [Retrieve a Message](http://developers.app.net/docs/resources/message/lookup/#retrieve-a-message)

####* api.getListMessage(ids=[...]) - [Retrieve multiple Messages](http://developers.app.net/docs/resources/message/lookup/#retrieve-multiple-messages)

####* api.getUserMessage() - [Retrieve my Messages](http://developers.app.net/docs/resources/message/lookup/#retrieve-my-messages)

####* api.destroyMessage(channel_id, message_id) - [Delete a Message](http://developers.app.net/docs/resources/message/lifecycle/#delete-a-message)
###file
####* api.createFile() - [Create a File](http://developers.app.net/docs/resources/file/lifecycle/#create-a-file)

####* api.createPlaceholderFile() - [Create a File Placeholder](http://developers.app.net/docs/resources/file/lifecycle/#create-a-file)

####* api.getFile(file_id) - [Retrieve a File](http://developers.app.net/docs/resources/file/lookup/#retrieve-a-file)

####* api.getListFile(ids=[...]) - [Retrieve multiple Files](http://developers.app.net/docs/resources/file/lookup/#retrieve-multiple-files)

####* api.destroyFile(file_id) - [Delete a File](http://developers.app.net/docs/resources/file/lifecycle/#delete-a-file)

####* api.getUserFile() - [Retrieve my Files](http://developers.app.net/docs/resources/file/lookup/#retrieve-my-files)

####* api.updateFile(file_id) - [Update a File](http://developers.app.net/docs/resources/file/lifecycle/#update-a-file)

####* api.getContentFile(file_id) - [Get File content](http://developers.app.net/docs/resources/file/content/#get-file-content)

####* api.setContentFile(file_id) - [Set File content](http://developers.app.net/docs/resources/file/content/#set-file-content)
###stream
####* api.createStream() - [Create a Stream](http://developers.app.net/docs/resources/stream/lifecycle/#create-a-stream)

####* api.getStream(stream_id) - [Retrieve a Stream](http://developers.app.net/docs/resources/stream/lifecycle/#retrieve-a-stream)

####* api.updateStream(stream_id) - [Update a Stream](http://developers.app.net/docs/resources/stream/lifecycle/#update-a-stream)

####* api.destroyStream(stream_id) - [Delete a Stream](http://developers.app.net/docs/resources/stream/lifecycle/#delete-a-stream)

####* api.getAllStream() - [Retrieve all Streams for the current Token](http://developers.app.net/docs/resources/stream/lifecycle/#get-current-tokens-streams)

####* api.destroyAllStream() - [Delete all Streams for the current Token](http://developers.app.net/docs/resources/stream/lifecycle/#delete-all-of-the-current-users-streams)
###filter
####* api.createFilter() - [Create a Filter](http://developers.app.net/docs/resources/filter/lifecycle/#create-a-filter)

####* api.getFilter(filter_id) - [Retrieve a Filter](http://developers.app.net/docs/resources/filter/lifecycle/#retrieve-a-filter)

####* api.updateFilter(filter_id) - [Update a Filter](http://developers.app.net/docs/resources/filter/lifecycle/#update-a-filter)

####* api.destroyFilter(filter_id) - [Delete a Filter](http://developers.app.net/docs/resources/filter/lifecycle/#delete-a-filter)

####* api.getUserFilter() - [Get the current User's Filters](http://developers.app.net/docs/resources/filter/lifecycle/#get-current-users-filters)

####* api.destroyUserFilter() - [Delete the current User's Filters](http://developers.app.net/docs/resources/filter/lifecycle/#delete-all-of-the-current-users-filters)
###interaction
####* api.getInteraction() - [Retrieve Interactions with the current User](http://developers.app.net/docs/resources/interaction/)
###marker
####* api.updateMarker() - [Update a Stream Marker](http://developers.app.net/docs/resources/stream-marker/#update-a-stream-marker)
###text
####* api.processText() - [Process text](http://developers.app.net/docs/resources/text-processor/)
###token
####* api.getToken() - [Retrieve the current token](http://developers.app.net/docs/resources/token/#retrieve-current-token)

####* api.getAuthorizedIdsToken() - [Retrieve authorized User IDs for an app](http://developers.app.net/docs/resources/token/#retrieve-authorized-user-ids-for-an-app)

####* api.getAuthorizedToken() - [Retrieve authorized User tokens for an app](http://developers.app.net/docs/resources/token/#retrieve-authorized-user-tokens-for-an-app)
###place
####* api.getPlace(factual_id) - [Retrieve a Place](http://developers.app.net/docs/resources/place/#retrieve-a-place)

####* api.searchPlace() - [Search for Places](http://developers.app.net/docs/resources/place/#search-for-a-place)
###explore
####* api.showExplore() - [Retrieve all Explore Streams](http://developers.app.net/docs/resources/explore/#retrieve-all-explore-streams)

####* api.getExplore(slug) - [Retrieve an Explore Stream](http://developers.app.net/docs/resources/explore/#retrieve-an-explore-stream)
