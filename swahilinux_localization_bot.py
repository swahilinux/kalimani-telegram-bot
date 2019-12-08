import telebot
import sqlite3
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import configparser

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
    elif call.data == "ondoka":
        bot.answer_callback_query(call.id, "Ahsante sana!!" + str(chat_id))


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


def insert_phrase_to_db(translation):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    print("current translation : > " + translation.text)
    global checksums_list
    if checksum not in checksums_list:
        checksums_list.append(checksum)
        sql_query = 'UPDATE localisation_main set swahili_translation = "' + translation.text.replace('"',
                                                                                                      '#') + '" where checksum = "' + checksum + '"'
        cursor.execute(sql_query)
        sql_query = 'UPDATE localisation_main set translator = "' + str(
            translation.from_user.id) + '" where checksum = "' + checksum + '"'
        cursor.execute(sql_query)
        conn.commit()
        conn.close()
        update_translator_details(translation)
        # update_translator_points(translation.from_user.id, )
        bot.send_message(translation.chat.id, "Hongera! " + translation.from_user.first_name,
                         reply_markup=gen_subsequent_markup())


def initiate_translation(chat_id_param):
    translation = bot.send_message(chat_id_param, "Twasemaje: \n" + get_phrase_from_db().replace('#', '"'),
                                   reply_markup=gen_skip_markup())
    if translation.text is not None and translation.text is not '':
        print("translation text:--->" + translation.text)
        bot.register_next_step_handler(translation, insert_phrase_to_db)


def update_translator_details(translation):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    select_user_query = 'SELECT * from translators_ids where user_id = ' + str(translation.from_user.id)
    insert_user_query = 'insert into translators_ids(user_id, first_name, points) values (' + \
                        str(translation.from_user.id) + ', "' + translation.from_user.first_name + '", ' + str(3)
    update_firstname_query = 'UPDATE translators_ids set first_name = "' + translation.from_user.first_name + \
                             '" where user_id = ' + str(translation.from_user.id)
    user = conn.execute(select_user_query)
    if user.arraysize == 0:
        cursor.execute(insert_user_query)
        conn.commit()
    else:
        cursor.execute(update_firstname_query)
        conn.commit()
    conn.close()


def update_translator_points(id, points):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    update_points_query = 'UPDATE translators_ids set points = ' + str(points) + ' where user_id = ' + str(id)
    cursor.execute(update_points_query)
    conn.commit()
    conn.close()


def get_phrase_from_db():
    conn = sqlite3.connect(db_name)
    cursor = conn.execute(
        "SELECT checksum, english_phrase from localisation_main where swahili_translation is  null order by random() limit 1")
    phrase = ''
    print("enterring for loop")
    for row in cursor:
        global checksum
        checksum = row[0]
        print(row[1])
        phrase = row[1]
    conn.close()
    return phrase


# conn.close()
bot.polling()
