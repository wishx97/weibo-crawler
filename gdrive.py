import mimetypes

from io import BufferedReader, BytesIO
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from pydrive2.files import GoogleDriveFile


def initial_gdrive():
    '''
    Authorize and refresh Google Drive token.
    Reference: https://stackoverflow.com/a/24542604/10114014
    '''
    gauth = GoogleAuth()
    # Try to load saved client credentials
    gauth.LoadCredentialsFile("mycreds.txt")
    if gauth.credentials is None:
        # Authenticate if they're not there
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        # Refresh them if expired
        gauth.Refresh()
    else:
        # Initialize the saved creds
        gauth.Authorize()
    # Save the current credentials to a file
    gauth.SaveCredentialsFile("mycreds.txt")
    return GoogleDriveWithBytes(gauth)


class GoogleDriveFileWithBytes(GoogleDriveFile):
    def SetContentBytes(self, content, filename):
        self.content = BufferedReader(BytesIO(content))
        if self.get('title') is None:
            self['title'] = filename
        if self.get('mimeType') is None:
            self['mimeType'] = mimetypes.guess_type(filename)[0]


class GoogleDriveWithBytes(GoogleDrive):
    def CreateFile(self, metadata=None):
        return GoogleDriveFileWithBytes(auth=self.auth, metadata=metadata)
