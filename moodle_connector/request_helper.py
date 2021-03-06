import json
import urllib

from http.client import HTTPSConnection


class RequestHelper:
    """
    Encapsulates the recurring logic for sending out requests to the
    Moodle-System.
    """

    def __init__(self, moodle_domain: str, moodle_path: str = '/',
                 token: str = ''):
        """
        Opens a connection to the Moodle system
        """
        self.connection = HTTPSConnection(moodle_domain)

        self.token = token
        self.moodle_domain = moodle_domain
        self.moodle_path = moodle_path

        RequestHelper.stdHeader = {
            # 'Cookie': 'cookie1=' + cookie1,
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)' +
            ' AppleWebKit/537.36 (KHTML, like Gecko)' +
            ' Chrome/78.0.3904.108 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded'
            # copied straight out of Chrome
        }

    def post_REST(self, function: str, data: {str: str} = None) -> object:
        """
        Sends a POST request to the REST endpoint of the Moodle system
        @param function: The Web service function to be called.
        @param data: The optional data is added to the POST body.
        @return: The Json response returned by the Moodle system, already
        checked for errors.
        """

        if (self.token is None):
            raise ValueError('The required Token is not set!')

        data_urlencoded = self._get_POST_DATA(function, self.token, data)
        url = self._get_REST_POST_URL(self.moodle_path, function)

        # uncomment this print to debug requested post-urls
        # print(url)

        # uncomment this print to debug posted data
        # print(data_urlencoded)

        self.connection.request(
            'POST',
            url,
            body=data_urlencoded,
            headers=self.stdHeader
        )

        response = self.connection.getresponse()
        return self._initial_parse(response)

    @staticmethod
    def _get_REST_POST_URL(moodle_path: str, function: str) -> str:
        """
        Generates an url for a REST-POST request
        @params: The necessary parameters for a REST URL
        @return: A formatted url
        """
        url = (('%swebservice/rest/server.php?moodlewsrestformat=json&' % (
            moodle_path)) + ('wsfunction=%s' % (function)))

        return url

    @staticmethod
    def _get_POST_DATA(function: str, token: str,
                       data_obj: str) -> str:
        """
        Generates the data for a REST-POST request
        @params: The necessary parameters for a REST URL
        @return: A url-encoded data string
        """
        data = {'moodlewssettingfilter': 'true',
                'moodlewssettingfileurl': 'true'
                }

        if data_obj is not None:
            data.update(data_obj)

        data.update({'wsfunction': function,
                     'wstoken': token})

        return urllib.parse.urlencode(data)

    def get_login(self, data: {str: str}) -> object:
        """
        Sends a POST request to the login endpoint of the Moodle system to
        obtain a token in Json format.
        @param data: The data is inserted into the Post-Body as arguments. This
        should contain the logon data.
        @return: The json response returned by the Moodle System, already
        checked for errors.
        """

        self.connection.request(
            'POST',
            '%slogin/token.php' % (
                self.moodle_path),
            body=urllib.parse.urlencode(data),
            headers=self.stdHeader
        )

        response = self.connection.getresponse()
        return self._initial_parse(response)

    def _initial_parse(self, response) -> object:
        """
        The first time parsing the result of a REST request.
        It is checked for known errors.
        @param response: The json response of the moodle system
        @return: The paresed json object
        """

        # Normaly Moodle answer with response 200
        if (response.getcode() != 200):
            raise RuntimeError(
                'An Unexpected Error happened on side of the Moodle System!' +
                (' Status-Code: %s' % str(response.getcode())) +
                ('\nHeader: %s' % (response.getheaders())) +
                ('\nResponse: %s' % (response.read())))

        # Try to parse the json
        try:
            response_extracted = json.loads(response.read())
        except ValueError as error:
            raise RuntimeError('An Unexpected Error occurred while trying' +
                               ' to parse the json response! Moodle' +
                               ' response: %s.\nError: %s' % (
                                   response.read(), error))
        # Check for known erorrs
        if ("error" in response_extracted):
            error = response_extracted.get("error", "")
            errorcode = response_extracted.get("errorcode", "")
            stacktrace = response_extracted.get("stacktrace", "")
            debuginfo = response_extracted.get("debuginfo", "")
            reproductionlink = response_extracted.get("reproductionlink", "")

            raise RequestRejectedError(
                'The Moodle System rejected the Request.' +
                (' Details: %s (Errorcode: %s, ' % (error, errorcode)) +
                ('Stacktrace: %s, Debuginfo: %s, Reproductionlink: %s)' % (
                    stacktrace, debuginfo, reproductionlink)
                 )
            )

        if ("exception" in response_extracted):
            exception = response_extracted.get("exception", "")
            errorcode = response_extracted.get("errorcode", "")
            message = response_extracted.get("message", "")

            raise RequestRejectedError(
                'The Moodle System rejected the Request.' +
                ' Details: %s (Errorcode: %s, Message: %s)' % (
                    exception, errorcode, message
                )
            )

        return response_extracted


class RequestRejectedError(Exception):
    """An Exception which gets thrown if the Moodle-System answered with an
    Error to our Request"""
    pass
