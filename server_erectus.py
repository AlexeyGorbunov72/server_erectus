# uid -- уникальный id пользователя
# from fcm import push_service
from Crypto.Cipher import AES
from pyfcm import FCMNotification
from firebase_admin import credentials
import firebase_admin
import requests
import socket
import sqlite3
import time

from threading import Thread

db_adress = r"C:\Users\Admin\progect.db"
threads_list = []

cred = credentials.Certificate(r"C:\Users\Admin\Downloads\erectus-63adc-firebase-adminsdk-ax0i3-3c09203bb2.json")
firebase_admin.initialize_app(cred)

push_service = FCMNotification(api_key="<your api key>")
def fcm_notification(token, msg, nick, UID_to, UID_by, chatId, publickey='', privatekey=''):
    print("msg in notiff: ", msg)
    msg = msg[msg[10:].find(' ') + 40:]
    data_message = {
        "chatId": f"{chatId}",
        "title": f"{nick}",
        "body": f"{msg}",
        "uid": f'{UID_by}',
        "private_key": f'{privatekey}',
        "public_key": f"{publickey}"
    }

    print("msg in fcm notif: ", msg)
    result = push_service.notify_single_device(registration_id=token, data_message=data_message)
    print("FCM result: ", result)
    if result['success'] == 0:
        r = requests.get(r"https://erectus-63adc.firebaseio.com/Users.json?print=pretty")
        dict = r.json()
        try:
            token_new = dict[UID_to]['token']

            if token_new not in token:
                db = sqlite3.connect(db_adress)
                cur = db.cursor()
                cur.execute(f"UPDATE info_users SET token = '{token_new}' WHERE UID = '{UID_to}' ")
                db.commit()
                result = push_service.notify_single_device(registration_id=token_new, data_message=data_message)
            else:
                print("<sys><error> Incorrect work of firebase!!")

        except Exception as e:
            print("<sys><error> in fcm_notification: ", e)

    print(result)


def send_msg(chat_id, text, UID):
    connection = find_connection(UID)
    if connection is not None:
        msg = f"<send msg>{chat_id} {text}"
        print("Я отправил это: ", msg, " ему: ", UID)
        connection.send(msg.encode().aes.encode())
    else:
        db = sqlite3.connect(db_adress)
        cur = db.cursor()
        cur.execute(f"SELECT token FROM info_users WHERE UID = '{UID}'")
        data = cur.fetchall()
        if data:

            data_cloud_messange(data[0][0], text, UID)

        else:
            print('<sys> Uncorrect UID: ', UID)


class User:
    def __init__(self, connect, UID, public_key, private_key):
        self.connect = connect
        self.id = UID
        self.public = public_key
        self.private = private_key

    def recv_msg(self, bytes_):
        msg = self.connect.recv(bytes_).decode()
        return rsa.decrypt(msg, self.private).decode()

    def send_msg(self, msg):
        self.connect.send(rsa.encrypt(msg.encode(), self.public))


def check_chat(id1, id2):
    db = sqlite3.connect(db_adres)
    cur = db.cursor()
    request = f"{max(id1, id2)} {min(id1, id2)}"
    cur.execute(f"SELECT id_chat FROM chats WHERE users_ids = '{request}'")
    data = cur.fetchall()
    db.close()
    if data:
        return data

    else:
        return None


def find_connection(uid):
    global threads_list

    for thr in threads_list:

        if uid == thr[2].id:
            return [thr[2].connect, thr[2].public]
    return None


def chat_minu(user):
    while True:

        msg = user.recv_msg(2048)
        if msg[0:12] != '<keep-alive>':
            print("msg: ", msg)
        if msg[0:12] == '<keep-alive>':
            continue

        if msg == '':
            exit(f"<sys> Username ({user.id}) is leave!")

        if msg[0:10] == '<send msg>':  # отправить сообщение в чат
            # данный протокол выглядит так: <send msg><your id chat><text>; пример: <send msg>0000000001Hello, there!
            chat_id = ''
            for char in range(10, len(msg)):
                if msg[char] == ' ':
                    print("user_id: ", user.id)
                    msg = msg[0:char] + ' ' + f"{user.id}" + msg[char:]
                    break
                chat_id += msg[char]

            db = sqlite3.connect(db_adres)
            cur = db.cursor()
            cur.execute(f"""SELECT users_ids FROM chats WHERE id_chat = '{chat_id}'""")
            ids = cur.fetchall()
            ids = ids[0][0].split(' ')

            for userId in ids:
                if userId != user.id:
                    connection, publickey = find_connection(userId)

                    if connection is not None:
                        connection.send(rsa.encrypt(msg.encode(), publickey))
                        print("I send this: ", msg, " to: ", userId)
                    else:

                        cur.execute(f"SELECT token FROM info_users WHERE UID = '{userId}'")
                        token = cur.fetchall()[0][0]
                        r = requests.get(r'https://erectus-63adc.firebaseio.com/Users.json?print=pretty')
                        dict = r.json()
                        nick = dict[user.id]['name']
                        print("NICK: ", nick)
                        print("TOKEN: ", token)
                        fcm_notification(token, msg, nick, userId, user.id, chat_id)


        elif msg[0:13] == '<create chat>':  # СОЗДАНИЕ ЧАТА
            id_with = ''

            for char in range(13, len(msg)):
                if msg[char] == ' ':
                    text_msg = str(user.id) + msg[char:]
                    print("Text_msg:", text_msg)
                    break
                id_with += msg[char]

            print("Start create chat! ")
            db = sqlite3.connect(db_adres)
            cur = db.cursor()
            print("USER ID: ", user.id)
            answer = check_chat(id_with, user.id)

            if answer is None:
                data_create = time.time()
                cur.execute(f"""INSERT INTO des_chat VALUES (NULL, '1 to 1', '{data_create}')""")
                db.commit()
                cur.execute(f"""SELECT id FROM des_chat WHERE data_create = '{data_create}'""")
                id_chat = cur.fetchall()[0][0]
                print("я отправил это--", f"<chatID>{id_chat}", ' to him: ', user.id)
                user.send_msg(f"<chatID>{id_chat}")
                print("ID WITH: ", id_with)

                r = requests.get(r'https://erectus-63adc.firebaseio.com/Users.json?print=pretty')
                dict = r.json()
                nick = dict[user.id]['name']
                token = dict[id_with]['token']
                print("TEXT_MSG: ", text_msg)
                text_msg = '<send msg>0 ' + text_msg
                fcm_notification(token, text_msg, nick, id_with, user.id, id_chat)

                print("ID; ", id_chat)
                cur.execute(f"""INSERT INTO chats VALUES ('{int(id_chat)}', '{max(id_with, user.id)} {min(id_with,
                                                                                                          user.id)}' )""")
                db.commit()
                db.close()

            else:
                user.send_msg(f"<chatID>{answer[0][0]}")

                conn, publickey = find_connection(id_with)

                if conn is None:
                    r = requests.get(r'https://erectus-63adc.firebaseio.com/Users.json?print=pretty')
                    dict = r.json()
                    nick = dict[id_with]['name']
                    token = dict[id_with]['token']

                    fcm_notification(token, text_msg, nick, id_with, user.id, id_chat, '', '')
                else:
                    text = "<send msg>" + id_chat + ' ' + user.id + ' ' + text_msg
                    conn.send(aes.encrypt(text, publickey))


def trans(conn):
    db = sqlite3.connect(db_adress)
    cur = db.cursor()

    UID = conn.recv(100).decode()
    (publickey, privatekey) = aes.newkeys(512)


    cur.execute(f"SELECT token FROM info_users WHERE UID = '{UID}'")
    data = cur.fetchall()

    if data:
        token = data[0][0]
        print("TOKEN: ", token)
        fcm_notification(token, '', '', '', '', '', str(publickey), str(privatekey))

        user_ = User(conn, UID, publickey, privatekey)
        print("CONNECTION = ", conn, '   ', type(conn))
        threads_list.append([Thread(target=chat_minu, args=(user_,)), conn, 'a'])

        threads_list[-1][0].start()
        threads_list[-1][2] = user_
    else:
        r = requests.get(r'https://erectus-63adc.firebaseio.com/Users.json?print=pretty')
        dict = r.json()
        try:
            token = dict[UID]['token']
            print("TOKEN: ", token)
        except:
            exit(f"<sys>This UID None: {UID} ")
        fcm_notification(token,'','','','',str(publickey), str(privatekey))
        cur.execute(f"INSERT INTO info_users VALUES ('{UID}' , '{token}')")
        db.commit()
        user_ = User(conn, UID, publickey, privatekey)
        threads_list.append([Thread(target=chat_minu, args=(user_,)), conn, 'a'])

        threads_list[-1][0].start()
        threads_list[-1][2] = user_


def Wait_Connection():
    sock = socket.socket()
    port = '' #int значение
    sock.bind(("<your ip>", port))
    sock.listen(100)
    socket.setdefaulttimeout(20)

    while True:
        conn = sock.accept()[0]
        thread = Thread(target=trans, args=(conn,))
        thread.start()


def Trasher():
    global threads_list

    print("Trasher is all ready!", '\n')

    while True:
        if len(threads_list) > 0:

            for thread in threads_list:
                try:
                    if not thread[0].is_alive() and thread[2] != 'a':
                        print('\n', "<sys><thrasher?>Disconnect: ", thread[1])
                        threads_list.pop(threads_list.index(thread))

                except Exception as e:
                    print('\n', "<sys><thrasher?> ERROR: ", e)


w = Thread(target=Wait_Connection)
w.start()

T = Thread(target=Trasher)
T.start()
