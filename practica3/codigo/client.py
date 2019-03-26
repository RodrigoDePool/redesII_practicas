from login import Login
from usuario import Usuario
from video_client import *

def main():

    # We keep going to login screen while the state says so
    while VideoClient.STATE is STATE_LOGIN:
        lg = Login("640x520")
        lg.start()

        if Usuario.APP_USER is  None:
            return

        vc = VideoClient("900x773")

        vc.start()


if __name__=='__main__':
    main()
