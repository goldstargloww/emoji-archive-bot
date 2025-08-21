# modified version of pytumblr for use here because i need rate limit access
# also allows the use of UUIDs
# https://github.com/tumblr/pytumblr

import urllib.parse
import requests
from functools import wraps
from requests_oauthlib import OAuth1
from requests.exceptions import TooManyRedirects, HTTPError


def validate_params(valid_options, params):
    """
    Helps us validate the parameters for the request

    :param valid_options: a list of strings of valid options for the
                          api request
    :param params: a dict, the key-value store which we really only care about
                   the key which has tells us what the user is using for the
                   API request

    :returns: None or throws an exception if the validation fails
    """
    #crazy little if statement hanging by himself :(
    if not params:
        return

    #We only allow one version of the data parameter to be passed
    data_filter = ['data', 'source', 'external_url', 'embed']
    multiple_data = [key for key in params.keys() if key in data_filter]
    if len(multiple_data) > 1:
        raise Exception("You can't mix and match data parameters")

    #No bad fields which are not in valid options can pass
    disallowed_fields = [key for key in params.keys() if key not in valid_options]
    if disallowed_fields:
        field_strings = ",".join(disallowed_fields)
        raise Exception("{} are not allowed fields".format(field_strings))

def validate_blogname(fn):
    """
    Decorator to validate the blogname and let you pass in a blogname like:
        client.blog_info('codingjester')
    or
        client.blog_info('codingjester.tumblr.com')
    or
        client.blog_info('blog.johnbunting.me')

    and query all the same blog.
    """
    @wraps(fn)
    def add_dot_tumblr(*args, **kwargs):
        if (len(args) > 1 and ("." not in args[1]) and ("t:" not in args[1])): # https://github.com/tumblr/pytumblr/pull/148
            args = list(args)
            args[1] += ".tumblr.com"
        return fn(*args, **kwargs)
    return add_dot_tumblr



class TumblrRequest(object):
    """
    A simple request object that lets us query the Tumblr API
    """

    __version = "0.1.2"

    def __init__(self, consumer_key, consumer_secret="", oauth_token="", oauth_secret="", host="https://api.tumblr.com"):
        self.host = host
        self.oauth = OAuth1(
            consumer_key,
            client_secret=consumer_secret,
            resource_owner_key=oauth_token,
            resource_owner_secret=oauth_secret
        )
        self.consumer_key = consumer_key

        self.headers = {
            "User-Agent": "pytumblr/" + self.__version,
        }
        
    def get(self, url, params):
        """
        Issues a GET request against the API, properly formatting the params

        :param url: a string, the url you are requesting
        :param params: a dict, the key-value of all the paramaters needed
                       in the request
        :returns: a dict parsed of the JSON response
        """
        url = self.host + url
        if params:
            url = url + "?" + urllib.parse.urlencode(params)

        try:
            resp = requests.get(url, allow_redirects=False, headers=self.headers, auth=self.oauth)
        except TooManyRedirects as e:
            resp = e.response

        return self.json_parse(resp), resp.headers

    def post(self, url, params={}, files=[]):
        """
        Issues a POST request against the API, allows for multipart data uploads

        :param url: a string, the url you are requesting
        :param params: a dict, the key-value of all the parameters needed
                       in the request
        :param files: a list, the list of tuples of files

        :returns: a dict parsed of the JSON response
        """
        url = self.host + url
        try:
            if files:
                return self.post_multipart(url, params, files)
            else:
                data = urllib.parse.urlencode(params)
                resp = requests.post(url, data=data, headers=self.headers, auth=self.oauth)
                return self.json_parse(resp)
        except HTTPError as e:
            return self.json_parse(e.response)

    def json_parse(self, response):
        """
        Wraps and abstracts response validation and JSON parsing
        to make sure the user gets the correct response.

        :param response: The response returned to us from the request

        :returns: a dict of the json response
        """
        try:
            data = response.json()
        except ValueError:
            data = {'meta': { 'status': 500, 'msg': 'Server Error'}, 'response': {"error": "Malformed JSON or HTML was returned."}}

        # NOTE: changed this to always return data instead of sometimes only data['response']
        return data

    def post_multipart(self, url, params, files):
        """
        Generates and issues a multipart request for data files

        :param url: a string, the url you are requesting
        :param params: a dict, a key-value of all the parameters
        :param files:  a dict, matching the form '{name: file descriptor}'

        :returns: a dict parsed from the JSON response
        """
        resp = requests.post(
            url,
            data=params,
            params=params,
            files=files,
            headers=self.headers,
            allow_redirects=False,
            auth=self.oauth
        )
        return self.json_parse(resp)

class TumblrClient(object):
    """
    A Python Client for the Tumblr API
    """

    def __init__(self, consumer_key, consumer_secret="", oauth_token="", oauth_secret="", host="https://api.tumblr.com"):
        """
        Initializes the TumblrRestClient object, creating the TumblrRequest
        object which deals with all request formatting.

        :param consumer_key: a string, the consumer key of your
                             Tumblr Application
        :param consumer_secret: a string, the consumer secret of
                                your Tumblr Application
        :param oauth_token: a string, the user specific token, received
                            from the /access_token endpoint
        :param oauth_secret: a string, the user specific secret, received
                             from the /access_token endpoint
        :param host: the host that are you trying to send information to,
                     defaults to https://api.tumblr.com

        :returns: None
        """
        self.request = TumblrRequest(consumer_key, consumer_secret, oauth_token, oauth_secret, host)

    def info(self):
        """
        Gets the information about the current given user

        :returns: A dict created from the JSON response
        """
        return self.send_api_request("get", "/v2/user/info")
    
    # NOTE: skipped methods that i didn't import:
    # avatar, likes, following, dashboard, blog_following, followers, blog_likes, drafts, submission, follow, unfollow, like, unlike, create_photo, create_quote, create_link, create_chat, create_audio, create_video, delete_post, edit_post, notes
    
    def tagged(self, tag, **kwargs):
        """
        Gets a list of posts tagged with the given tag

        :param tag: a string, the tag you want to look for
        :param before: a unix timestamp, the timestamp you want to start at
                       to look at posts.
        :param limit: the number of results you want
        :param filter: the post format that you want returned: html, text, raw

            client.tagged("gif", limit=10)

        :returns: a dict created from the JSON response
        """
        kwargs.update({'tag': tag})
        return self.send_api_request("get", '/v2/tagged', kwargs, ['before', 'limit', 'filter', 'tag', 'api_key'], True)
    
    @validate_blogname
    def posts(self, blogname, type=None, **kwargs):
        """
        Gets a list of posts from a particular blog

        :param blogname: a string, the blogname you want to look up posts
                         for. eg: codingjester.tumblr.com
        :param id: an int, the id of the post you are looking for on the blog
        :param tag: a string, the tag you are looking for on posts
        :param limit: an int, the number of results you want
        :param offset: an int, the offset of the posts you want to start at.
        :param before: an int, the timestamp for posts you want before.
        :param filter: the post format you want returned: HTML, text or raw.
        :param type: the type of posts you want returned, e.g. video. If omitted returns all post types.

        :returns: a dict created from the JSON response
        """
        url = f'/v2/blog/{blogname}/posts'
        if type:
            url += f'/{type}'
        return self.send_api_request("get", url, kwargs, ['id', 'tag', 'limit', 'offset', 'before', 'reblog_info', 'notes_info', 'filter', 'api_key', 'npf'], True)
    
    @validate_blogname
    def blog_info(self, blogname):
        """
        Gets the information of the given blog

        :param blogname: the name of the blog you want to information
                         on. eg: codingjester.tumblr.com

        :returns: a dict created from the JSON response of information
        """
        url = f"/v2/blog/{blogname}/info"
        return self.send_api_request("get", url, {}, ['api_key'], True)
    
    @validate_blogname
    def queue(self, blogname, **kwargs):
        """
        Gets posts that are currently in the blog's queue

        :param limit: an int, the number of posts you want returned
        :param offset: an int, the post you want to start at, for pagination.
        :param filter: the post format that you want returned: HTML, text, raw.

        :returns: a dict created from the JSON response
        """
        url = f"/v2/blog/{blogname}/posts/queue"
        return self.send_api_request("get", url, kwargs, ['limit', 'offset', 'filter', 'npf'])
    
    @validate_blogname
    def reblog(self, blogname, **kwargs):
        """
        Creates a reblog on the given blogname

        :param blogname: a string, the url of the blog you want to reblog to
        :param id: an int, the post id that you are reblogging
        :param reblog_key: a string, the reblog key of the post
        :param comment: a string, a comment added to the reblogged post

        :returns: a dict created from the JSON response
        """
        url = f"/v2/blog/{blogname}/post/reblog"

        valid_options = ['id', 'reblog_key', 'comment'] + self._post_valid_options(kwargs.get('type', None))
        if 'tags' in kwargs and kwargs['tags']:
            # Take a list of tags and make them acceptable for upload
            kwargs['tags'] = ",".join(kwargs['tags'])
        return self.send_api_request('post', url, kwargs, valid_options)
    
    @validate_blogname
    def create_text(self, blogname, **kwargs):
        """
        Create a text post on a blog

        :param blogname: a string, the url of the blog you want to post to.
        :param state: a string, The state of the post.
        :param tags: a list of tags that you want applied to the post
        :param tweet: a string, the customized tweet that you want
        :param date: a string, the GMT date and time of the post
        :param format: a string, sets the format type of the post. html or markdown
        :param slug: a string, a short text summary to the end of the post url
        :param title: a string, the optional title of a post
        :param body: a string, the body of the text post

        :returns: a dict created from the JSON response
        """
        kwargs.update({"type": "text"})
        return self._send_post(blogname, kwargs)
    
    def _post_valid_options(self, post_type=None):
        # Parameters valid for /post, /post/edit, and /post/reblog.
    
        # These options are always valid
        valid = ['type', 'state', 'tags', 'tweet', 'date', 'format', 'slug']

        # Other options are valid on a per-post-type basis
        if post_type == 'text':
            valid += ['title', 'body']
        elif post_type == 'photo':
            valid += ['caption', 'link', 'source', 'data', 'photoset_layout']
        elif post_type == 'quote':
            valid += ['quote', 'source']
        elif post_type == 'link':
            valid += ['title', 'url', 'description', 'thumbnail']
        elif post_type == 'chat':
            valid += ['title', 'conversation']
        elif post_type == 'audio':
            valid += ['caption', 'external_url', 'data']
        elif post_type == 'video':
            valid += ['caption', 'embed', 'data']

        return valid

    def _send_post(self, blogname, params):
        """
        Formats parameters and sends the API request off. Validates
        common and per-post-type parameters and formats your tags for you.

        :param blogname: a string, the blogname of the blog you are posting to
        :param params: a dict, the key-value of the parameters for the api request
        :param valid_options: a list of valid options that the request allows

        :returns: a dict parsed from the JSON response
        """
        url = f"/v2/blog/{blogname}/post"
        valid_options = self._post_valid_options(params.get('type', None))

        if len(params.get("tags", [])) > 0:
            # Take a list of tags and make them acceptable for upload
            params['tags'] = ",".join(params['tags'])

        return self.send_api_request("post", url, params, valid_options)

    def send_api_request(self, method, url, params={}, valid_parameters=[], needs_api_key=False):
        """
        Sends the url with parameters to the requested url, validating them
        to make sure that they are what we expect to have passed to us

        :param method: a string, the request method you want to make
        :param params: a dict, the parameters used for the API request
        :param valid_parameters: a list, the list of valid parameters
        :param needs_api_key: a boolean, whether or not your request needs an api key injected

        :returns: a dict parsed from the JSON response
        """
        if needs_api_key:
            params.update({'api_key': self.request.consumer_key})
            valid_parameters.append('api_key')

        files = {}
        if 'data' in params:
            if isinstance(params['data'], list):
                for idx, data in enumerate(params['data']):
                    files['data['+str(idx)+']'] =  open(params['data'][idx], 'rb')
            else:
                files = {'data': open(params['data'], 'rb')}
            del params['data']

        validate_params(valid_parameters, params)
        if method == "get":
            return self.request.get(url, params)
        elif method == "delete":
            return self.request.delete(url, params)
        else:
            return self.request.post(url, params, files)
        
        