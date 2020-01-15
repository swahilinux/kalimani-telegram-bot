import configparser
import sqlite3

import emoji
import emojis
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

config = configparser.ConfigParser()
config.read('config.ini')
bot = telebot.TeleBot(config['BOT']['bot_api'])
chat_id = ''
checksum = ''
db_name = config['PERSISTENCE']['database_location']

checksums_list = []
print(db_name)
conn = sqlite3.connect(db_name)
exisiting_checksums_query = 'SELECT checksum from localisation_main where swahili_translation is not null'
exisiting_checksums_cursor = conn.execute(exisiting_checksums_query)
for entry in exisiting_checksums_cursor:
    checksums_list.append(entry[0])


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    global chat_id
    chat_id = message.chat.id
    bot.send_message(chat_id, "Jambo! Wataka kufanya nini?", reply_markup=gen_initial_markup())


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "tafsiri" or call.data == "endelea" or call.data == "ruka":
        initiate_translation(call.message.chat.id)
    elif call.data == "angalia_mabingwa":
        send_top_contributors(call.message.chat.id)
    elif call.data == "ondoka":
        send_welcome(call.message)


@bot.message_handler(commands=['tafsiri'])
def send_phrase(message):
    bot.reply_to(message, get_phrase_from_db())


def gen_initial_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton("Kutafsiri", callback_data="tafsiri"),
               InlineKeyboardButton("Kuangalia mabingwa", callback_data="angalia_mabingwa"),
               InlineKeyboardButton("Kuangalia maendeleo", callback_data="angalia_maendeleo"),
               InlineKeyboardButton("Kuondoka", callback_data="ondoka"))
    return markup


def gen_subsequent_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton("Endelea", callback_data='endelea'),
               InlineKeyboardButton("Ondoka", callback_data='ondoka'))
    return markup


def gen_skip_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton("Ruka neno", callback_data='ruka'),
               InlineKeyboardButton("Ondoka", callback_data='ondoka'))
    return markup


def gen_exit_rankings_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton("Nimetii!!", callback_data='ondoka'))
    return markup


def text_has_emoji(text):
    for character in text:
        if character in emoji.UNICODE_EMOJI:
            return True
    return False


def insert_phrase_to_db(translation):
    connection = sqlite3.connect(db_name)
    cursor = connection.cursor()
    try:
        print("current translation : > " + translation.text)
    except TypeError:
        bot.send_message(translation.chat.id, "Samahani, jaribu tena " + translation.from_user.first_name,
                         reply_markup=gen_subsequent_markup())
        return
    if text_has_emoji(translation.text) or translation.text in ['/start', '/stop']:
        bot.send_message(translation.chat.id, "Samahani, jaribu tena " + translation.from_user.first_name,
                         reply_markup=gen_subsequent_markup())
        return
    global checksums_list
    if checksum not in checksums_list:
        checksums_list.append(checksum)
        sql_query = 'UPDATE localisation_main set swahili_translation = "' + \
                    translation.text.replace('"', '#') + '" where checksum = "' + checksum + '" '
        cursor.execute(sql_query)
        sql_query = 'UPDATE localisation_main set translator = "' + str(
            translation.from_user.id) + '" where checksum = "' + checksum + '"'
        cursor.execute(sql_query)
        connection.commit()
        connection.close()
        update_translator_details(translation)
        update_translator_points(translation.from_user.id, 3)
        bot.send_message(translation.chat.id, "Hongera! " + translation.from_user.first_name,
                         reply_markup=gen_subsequent_markup())


def initiate_translation(chat_id_param):
    translation = bot.send_message(chat_id_param, "Twasemaje: \n" + get_phrase_from_db().replace('#', '"'),
                                   reply_markup=gen_skip_markup())
    if translation.text is not None and translation.text is not '':
        bot.register_next_step_handler(translation, insert_phrase_to_db)


def send_top_contributors(chat_id_param):
    top_contributors = get_top_contributors()
    total_top_contributors = top_contributors.__len__()
    list_of_top_contributors = ''
    first_place_emoji = emojis.encode(' :sunglasses: :goat:')
    second_place_emoji = emojis.encode(' :smirk: :fist:')
    third_place_emoji = emojis.encode(' :v:')
    subsequent_positions_emoji = ''
    for contributor_index in range(total_top_contributors):
        if contributor_index == 0:
            emoji_icon = first_place_emoji
        elif contributor_index == 1:
            emoji_icon = second_place_emoji
        elif contributor_index == 2:
            emoji_icon = third_place_emoji
        else:
            emoji_icon = subsequent_positions_emoji
        list_of_top_contributors += str(contributor_index + 1) + ". " + top_contributors[contributor_index][0] + " - " + \
                                    str(top_contributors[contributor_index][1]) + emoji_icon + "\n"
    bot.send_message(chat_id_param, "Wazito: \n" + list_of_top_contributors,
                     reply_markup=gen_exit_rankings_markup())


def get_translator_points(translator_id):
    connection = sqlite3.connect(db_name)
    cursor = connection.cursor()
    select_points_query = 'SELECT points from translators_ids where user_id = ' + str(translator_id)
    points = cursor.execute(select_points_query).fetchone()[0]
    connection.close()
    return points


def update_translator_details(translation):
    connection = sqlite3.connect(db_name)
    cursor = connection.cursor()
    select_user_query = 'SELECT * from translators_ids where user_id = ' + str(translation.from_user.id)
    insert_user_query = "insert into translators_ids(user_id, first_name, points) values (" + str(
        translation.from_user.id) + ", \"" + translation.from_user.first_name + "\", " + str(3) + ")"
    update_firstname_query = 'UPDATE translators_ids set first_name = "' + translation.from_user.first_name + \
                             '" where user_id = ' + str(translation.from_user.id)
    user = cursor.execute(select_user_query).fetchall()
    if user:
        cursor.execute(update_firstname_query)
        connection.commit()
    else:
        cursor.execute(insert_user_query)
        connection.commit()
    connection.close()


def update_translator_points(translator_id, awarded_points):
    connection = sqlite3.connect(db_name)
    cursor = connection.cursor()
    current_points = get_translator_points(translator_id)
    new_points = int(awarded_points) + int(current_points)
    update_points_query = 'UPDATE translators_ids set points = {0} where user_id = {1}'.format(str(new_points),
                                                                                               str(translator_id))
    cursor.execute(update_points_query)
    connection.commit()
    connection.close()


def get_phrase_from_db():
    connection = sqlite3.connect(db_name)
    cursor = connection.execute(
        "SELECT checksum, english_phrase from localisation_main where swahili_translation is  null order by random() "
        "limit 1")
    phrase = ''
    print("enterring for loop")
    for row in cursor:
        global checksum
        checksum = row[0]
        print(row[1])
        phrase = row[1]
    connection.close()
    return phrase


def get_top_contributors():
    connection = sqlite3.connect(db_name)
    cursor = connection.cursor()
    select_top_contributors_query = "select first_name, points from translators_ids order by points desc limit 10"
    top_contributors = cursor.execute(select_top_contributors_query).fetchall()
    return top_contributors


# conn.close()
bot.polling()
