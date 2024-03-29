from itsdangerous import JSONWebSignatureSerializer
from time import time
from hashids import Hashids
import mysql.connector
import requests
import hashlib
from dotenv import load_dotenv
from os import environ
load_dotenv(verbose=True, override=True)


def getUserInput(variable_name, default=None):
    user_input = input(f"Input {variable_name} (Default: {default})>>")
    if user_input == "":
        return default
    else:
        return user_input


class NuxtImageBoardSetup():
    def __init__(
        self,
        host,
        port,
        user,
        password,
        database,
        toymoney_pass_head,
        toymoney_endpoint,
        toymoney_token,
        salt_invite,
        salt_pass,
        salt_jwt,
        headless=False
    ):
        self.conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        self.cursor = self.conn.cursor()
        self.TOYMONEY_PASSWORD_HEAD = toymoney_pass_head
        self.TOYMONEY_ENDPOINT = toymoney_endpoint
        self.TOYMONEY_TOKEN = toymoney_token
        self.SALT_INVITE = salt_invite
        self.SALT_PASS = salt_pass
        self.SALT_JWT = salt_jwt
        if headless:
            self.createDatabase()
            self.createMainApiUser(self.createSubApiUser())

    def createDatabase(self):
        with open("init.sql", "r", encoding="utf8") as f:
            self.cursor.execute(f.read(), multi=True)
        self.conn.commit()
        return True

    def createSubApiUser(self, display_id="nib_admin"):
        toyApiResp = requests.post(
            f"{self.TOYMONEY_ENDPOINT}/users/create",
            json={
                "name": display_id,
                "password": f"{self.TOYMONEY_PASSWORD_HEAD}{display_id}"
            },
            headers={
                "Authorization": f"Bearer {self.TOYMONEY_TOKEN}"
            }
        )
        if toyApiResp.status_code != 200:
            raise Exception("ToyMoneyへのリクエストに失敗しました")
        resp = toyApiResp.json()
        return resp["apiKey"]

    def generateApiKey(self, accountID):
        self.cursor.execute(
            "SELECT userApiSeq,userPermission FROM data_user WHERE userID=%s",
            (accountID,)
        )
        apiSeq, apiPermission = self.cursor.fetchall()[0]
        serializer = JSONWebSignatureSerializer(self.SALT_JWT)
        token = serializer.dumps({
            'id': accountID,
            'seq': apiSeq + 1,
            'permission': apiPermission
        }).decode('utf-8')
        self.cursor.execute(
            """UPDATE data_user SET userApiSeq=userApiSeq+1, userApiKey=%s
            WHERE userID=%s""",
            (token, accountID)
        )
        self.conn.commit()
        return token

    def createMainApiUser(
        self,
        toyapi_key,
        display_id="nib_admin",
        username="nib_admin",
        password="nib_admin",
        permission=9
    ):
        # パスワードをハッシュ化
        password = self.SALT_PASS+password
        password = hashlib.sha256(password.encode("utf8")).hexdigest()
        # ユーザーを追加
        self.cursor.execute(
            """INSERT INTO data_user
            (userDisplayID, userName, userPassword,
            userToyApiKey, userPermission)
            VALUES (%s,%s,%s,%s,%s)""",
            (display_id, username, password, toyapi_key, permission)
        )
        # ユーザー内部IDを取得
        self.cursor.execute(
            """SELECT userID FROM data_user
            WHERE userDisplayID=%s AND userPassword=%s""",
            (display_id, password)
        )
        user_id = self.cursor.fetchall()[0][0]
        # APIキーの作成
        api_key = self.generateApiKey(user_id)
        # マイリストの作成
        self.cursor.execute(
            """INSERT INTO info_mylist
            (mylistName, mylistDescription, userID)
            VALUES (%s,%s,%s)""",
            (f"{username}のマイリスト", "", user_id)
        )
        self.conn.commit()
        return user_id, api_key

    def createInvitation(self, user_id, invite_code="RANDOM", code_count=1):
        invite_codes = []
        for _ in range(code_count):
            if invite_code == "RANDOM":
                hash_gen = Hashids(salt=self.SALT_INVITE, min_length=8)
                code = hash_gen.encode(int(time()) + user_id)
            else:
                code = invite_code
            invite_codes.append(code)
            self.cursor.execute(
                """INSERT INTO data_invite
                (inviter, inviteCode) VALUES (%s, %s)""",
                (user_id, code)
            )
        self.conn.commit()
        return invite_codes


if __name__ == "__main__":
    print("Welcome to NuxtImageBoard Setup wizard!")
    db_host = getUserInput("database host", "localhost")
    db_port = getUserInput("database port", 3306)
    db_user = getUserInput("database user", "nuxt_image_board")
    db_pass = getUserInput("database pass", "nuxt_image_board")
    db_name = getUserInput("database name", "nuxt_image_board")
    cl = NuxtImageBoardSetup(db_host, db_port, db_user, db_pass, db_name)
    while True:
        print("""Input operation
            1: Create database
            2: Create user
            3: Create invitation
            4: Exit""")
        op_type = 0
        while op_type not in [1, 2, 3, 4]:
            op_number = getUserInput("operation number", "1")
            if not op_number.isdecimal():
                print("Please input number.")
            elif int(op_number) not in [1, 2, 3, 4]:
                print("Invalid operation number.")
            else:
                op_type = int(op_number)
        if op_type == 1:
            print("Creating database...")
            cl.createDatabase()
            print("Create database success!")
        elif op_type == 2:
            print("Creating user...")
            display_id = getUserInput("display id", "nib_admin")
            username = getUserInput("username", "nib_admin")
            password = getUserInput("password", "nib_admin")
            permission = getUserInput("permission", "9")
            toyapi_key = cl.createSubApiUser(display_id)
            user_id, api_key = cl.createMainApiUser(
                toyapi_key,
                display_id,
                username,
                password,
                permission
            )
            print("Create user success!")
            print(f"User id: {user_id}")
            print(f"Api key: {api_key}")
        elif op_type == 3:
            print("Creating invite...")
            user_id = int(getUserInput("inviter user id", "1"))
            invite_code = getUserInput("invite code", "RANDOM")
            code_count = int(getUserInput("code count", "1"))
            codes = cl.createInvitation(
                user_id,
                invite_code,
                code_count
            )
            print("Create invite success!")
            print("Invite codes:")
            print("\n".join(codes))
        else:
            print("Bye")
            break
