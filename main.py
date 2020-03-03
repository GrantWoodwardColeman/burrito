import requests
import pymysql
import json
import numpy
import time
from config import *
import matplotlib.pyplot as plt

db = pymysql.connect(host=server, user=user, password=password, db=database)
mycursor = db.cursor()


def test_db(input_value):
    sql = "INSERT into `members` (`user_id`, `nickname`, `image_url`, `other_id`, `muted`, `autokicked`, `roles`, `name`)"
    sql +=  "VALUES (" + input_value + ", 'a', 'a', '1', '0', '0', 'a', 'a');"
    print(mycursor.execute(sql))

# The chat id is, quite descriptively, the id of the groupme chat you're pulling info from. It can be accessed in a
# number of ways, the easiest of which being a simple API call to grab all groups you are a part of.


def get_chat_data(chat_id):
    url = "https://api.groupme.com/v3/groups/" + chat_id + "?token=" + user_token
    headers = {'Content-Type': 'application/json'}
    response = requests.request('GET', url, headers=headers)
    # pprint(response.text.encode('utf8'))
    parsed = json.loads(response.text.encode('utf8'))
    meta = parsed['meta']
    members_info = parsed['response']['members']
    print_response(response)
    chat_details= parsed['response']
    chat_details.pop('members')

    save_members(members_info)
    save_chat_details(chat_details)

#    members = build_member_array(members_info)


def save_members(members_info):
    numpy.save('members_info', members_info)


def save_chat_details(chat_details):
    numpy.save('chat_details', chat_details)


def save_message_history(messages):
    numpy.save('message_history', messages)


def print_response(response):
    parsed = json.loads(response.text.encode('utf8'))
    print('\n')
    print(json.dumps(parsed,indent=4,sort_keys=True))


# NOTE: Run on Python 3.6 and above to avoid issues with unordered dictionaries


def get_messages(chat_details, chat_id):
    # Off by one error?
    messages = []
    payload = {}
    files = {}
    headers = {
        'Content-Type': 'application/json'
    }
    count = chat_details.item().get('messages').get('count')
    message_id = chat_details.item().get('messages').get('last_message_id')

    while(count > 0):
        url = "https://api.groupme.com/v3/groups/"
        url += str(chat_id)
        url += "/messages?token="
        url += user_token
        url += "&before_id="
        url += message_id
        if count >= 100:
            limit = 99
        else:
            limit = count

        url += "&limit=" + str(limit)

        response = requests.request("GET", url, headers=headers, data = payload, files = files)
        response = json.loads(response.text.encode('utf8'))
        print(response)
        print(url)
        for current_messages in response.get('response').get("messages"):
            messages.append(current_messages)
            message_id = current_messages.get("id")
        print(count)

        count -= limit

    save_message_history(messages)
    print('all done')


# def get_stats(message_history, members_info):
#     for message in message_history:


def populate_members_tables():
    members_info = numpy.load("members_info.npy", allow_pickle=True)
    for member in members_info:
        sql = "INSERT IGNORE into `members` (`user_id`, `nickname`, `image_url`, `other_id`, `muted`, `autokicked`, `roles`, `name`)"
        sql += "VALUES (" + member.get('user_id') + ", '"
        sql += member.get('nickname') + "', '"
        sql += str(member.get('image_url')) + "', '"
        sql += member.get('id') + "', '"
        sql += str(member.get('muted')) + "', '"
        sql += str(member.get('autokicked')) + "', '"
        sql += "no" + "', '"
        sql += member.get('name')
        sql += "');"
        print(sql)
        print(mycursor.execute(sql))

        sql = "INSERT IGNORE INTO `member_stats` (`user_id`, `messages_w_pic`, `additional_burritos`, `total_burritos`, `burritos_per_day`, `days_in_chat`, `most_liked_message`, `most_liked_pic`)"
        sql += "VALUES (" + member.get('user_id') + ", '"
        sql += "0', '0', '0', '0', '0', '0', '0');"
        print(sql)
        print(mycursor.execute(sql))


def record_the_damn_stats():
    message_history = numpy.load("message_history.npy", allow_pickle=True)

    for message in message_history:
        try:
            if (message.get('sender_id') == 'system'):
                for added_user in message.get('event')['data']['added_users']:
                    sql = "UPDATE `members` SET `join_date` = '"
                    sql += str(message.get('created_at'))
                    sql += "' WHERE `user_id` = '" + str(added_user['id'])
                    sql += "';"
                    print(sql)
                    print(mycursor.execute(sql))
        except:
            print('Not sure what to do here, probably temporary')

        user_id = (message.get('user_id'))

        if message.get("attachments") and message.get('sender_id') != 'system' and message.get('sender_id') != 'calendar':
            sql = "UPDATE `member_stats` SET `messages_w_pic` = `messages_w_pic` + 1 WHERE "
            sql += "`user_id` = " + (user_id) + ";"
            print(sql)
            print(mycursor.execute(sql))


def set_burritos_per_day():
    cur_time = time.time()
    sql = "SELECT member_stats.user_id, member_stats.messages_w_pic, members.join_date "
    sql += "FROM member_stats "
    sql += "INNER JOIN members USING (user_id) "
    sql += "WHERE member_stats.messages_w_pic > 0 "
    sql += "ORDER BY messages_w_pic DESC;"
    print(sql)
    mycursor.execute(sql)
    pic_stats = mycursor.fetchall()
    for user in pic_stats:
        print(cur_time)
        print(user[2])
        print(cur_time - user[2])
        bpd = user[1]/((cur_time - user[2])/86400)
        print(bpd)
        sql = "UPDATE `member_stats` SET `burritos_per_day` = " + "' " + str(bpd) + "' " + "WHERE "
        sql += "`user_id` = " + str(user[0]) + ';'
        print(sql)
        print(mycursor.execute(sql))


def display_some_stats():
    sql = "SELECT member_stats.user_id, member_stats.messages_w_pic, member_stats.burritos_per_day, members.nickname "
    sql += "FROM member_stats "
    sql += "INNER JOIN members USING (user_id) "
    sql += "WHERE member_stats.messages_w_pic > 4 "
    sql += "ORDER BY messages_w_pic DESC;"
    print(sql)
    print(mycursor.execute(sql))
    pic_stats = mycursor.fetchall()
    total_burritos = []
    user_names = []
    x_cords = []
    x_num = -10
    for stat in pic_stats:
        x_num += 2.5
        print(stat)
        print("\n")
        total_burritos.append(stat[1])
        user_names.append(stat[3] + ' ' + str(stat[1]))
        x_cords.append(x_num)

    fig, ax = plt.subplots(figsize=(17, 32))
    font = {'family': 'normal',
            'weight': 'bold',
            'size': 70}

    plt.rc('font', **font)

    ax.barh(x_cords, total_burritos, 1.45, left=None)
    ax.set_yticks(x_cords)
    ax.set_yticklabels(user_names)

    ax.invert_yaxis()
    ax.set_xlabel('Burritos', fontsize=40)
    ax.set_title('Total Burritos Eaten',)

    plt.savefig('total_burritos.png', format='png')


def display_some_stats_2():
    sql = "SELECT member_stats.user_id, member_stats.messages_w_pic, member_stats.burritos_per_day, members.nickname "
    sql += "FROM member_stats "
    sql += "INNER JOIN members USING (user_id) "
    sql += "WHERE member_stats.messages_w_pic > 4 "
    sql += "ORDER BY member_stats.burritos_per_day DESC;"
    print(sql)
    print(mycursor.execute(sql))
    pic_stats = mycursor.fetchall()
    bpd = []
    user_names = []
    x_cords = []
    x_num = -10
    for stat in pic_stats:
        x_num += 2.5
        print(stat)
        print("\n")
        bpd.append(stat[2])
        user_names.append(stat[3] + ' ' + str(round(stat[2],2)))
        x_cords.append(x_num)

    fig, ax = plt.subplots(figsize=(20, 32))
    font = {'family': 'normal',
            'weight': 'bold',
            'size': 70}

    plt.rc('font', **font)

    print(ax)

    ax.barh(x_cords, bpd, 1.45, left=None)
    ax.set_yticks(x_cords)
    ax.set_yticklabels(user_names)
    ax.invert_yaxis()
    ax.set_xlabel('Burritos Per Day in Chat', fontsize=40)
    ax.set_title('Average Burritos Per Day',)

    plt.savefig('bpd.png', format='png')


