from datetime import timedelta
from telebot.types import Message
from telebot import TeleBot
from notion_handler import NotionHandler, SearchProperties
from dotenv import load_dotenv, set_key
from os import environ
from file_manager import FileManager
from buttons import start_search_reply_buttons, continue_search_reply_buttons, use_selected_sp_reply_button
from timeloop import Timeloop

load_dotenv('.env')
token = environ["API_KEY"]
search_requests = {}
bot = TeleBot(token=token)
tl = Timeloop()
fm = FileManager(token=token)


def delete_prefix(message: Message):
    if "/search_name " in message.text:
        message.text = message.text.replace("/search_name ", "")
    if "/search_type " in message.text:
        message.text = message.text.replace("/search_type ", "")
    if "/search_status " in message.text:
        message.text = message.text.replace("/search_type ", "")
    return message


@bot.message_handler(commands=["start"])
def start_command(message):
    bot.send_message(message.chat.id, "Send /test to get started")


@bot.message_handler(commands=["test"])
def next_command(message):
    print(message.text)
    nh = NotionHandler(tg_id=message.chat.id)
    sp = SearchProperties()
    tasks = nh.find_tasks(search_prop=sp)
    bot.send_message(message.chat.id,
                     "Результатов по данному запросу может быть очень много, поэтому используйте кнопки "
                     "под этим сообщением, чтобы управлять поисковой выдачей",
                     reply_markup=start_search_reply_buttons)
    search_requests.update({message.chat.id: tasks})


@bot.message_handler(commands=["search"])
def search(message):
    bot.send_message(message.chat.id, text="Поиск по двум и более параметрам.\n"
                                           "Используйте комманды ниже, чтобы задать конкретные значения для поиска:\n"
                                           "/status [Значение]\n"
                                           "/type [Значение]\n"
                                           "/name [Значение]\n"
                                           "/date [Значение]\n")
    search_requests.update({message.chat.id: SearchProperties()})


@bot.message_handler(commands=["status", "type", "name", "date"])
def update_search_prop(message):
    if message.chat.id in search_requests:
        if isinstance(search_requests[message.chat.id], SearchProperties):
            sp = search_requests[message.chat.id]
            sp.update_search_properties(message)
            bot.send_message(chat_id=message.chat.id,
                             text=f"Параметры поиска были обновлены!\n"
                                  f"Текущие параметры:\n{sp.__repr__()}",
                             reply_markup=use_selected_sp_reply_button)
        else:
            bot.send_message(chat_id=message.chat.id,
                             text="Прежде чем начать новый поиск, завершите старый!",
                             reply_markup=continue_search_reply_buttons)
    else:
        bot.send_message(chat_id=message.chat.id,
                         text="Для начала создайте поисковой запрос с помощью комманды /search.")


@bot.message_handler(commands=['search_name', 'search_type', 'search_status'])
def search_name_command(message):
    print(message.text)
    nh = NotionHandler(tg_id=message.chat.id)
    sp = SearchProperties(message=message)
    tasks = nh.find_tasks(search_prop=sp)
    bot.send_message(message.chat.id,
                     "Результатов по данному запросу может быть очень много, поэтому используйте кнопки "
                     "под этим сообщением, чтобы управлять поисковой выдачей",
                     reply_markup=start_search_reply_buttons)
    search_requests.update({message.chat.id: tasks})


@bot.callback_query_handler(func=lambda x: True)
def callback_query_handler(call):
    bot.send_chat_action(call.message.chat.id, "typing", timeout=30)
    search_request_id = call.message.chat.id
    try:
        tasks = search_requests[search_request_id]
    except KeyError:
        bot.send_message(call.message.chat.id, "Поисковой запрос не найден, составьте новый поисковой запрос!")
        return None
    if "next" in call.data:
        how_much_tasks = int(call.data.replace("next", ""))
        for i in range(how_much_tasks):
            try:
                task = next(tasks)
            except StopIteration:
                task = "Конец поисковой выдачи"
                bot.send_message(call.message.chat.id, task, parse_mode="MarkdownV2", disable_web_page_preview=True)
                bot.send_message(call.message.chat.id, "Поиск завершен")
                return None
            files_to_upload = fm.get_downloaded_files(search_request_id)
            print(files_to_upload)
            bot.send_message(call.message.chat.id, task, parse_mode="MarkdownV2", disable_web_page_preview=True)
            if files_to_upload:
                for file in files_to_upload:
                    fm.upload_file(call.message.chat.id, file)

        bot.send_message(call.message.chat.id, "Меню поиска:", reply_markup=continue_search_reply_buttons)
    if "stop" in call.data:
        search_requests.pop(search_request_id)
        fm.delete_downloaded_files(search_request_id)
        bot.send_message(call.message.chat.id, "Поиск завершен")
    if "sp" in call.data:
        nh = NotionHandler(tg_id=call.message.chat.id)
        sp = search_requests[search_request_id]
        tasks = nh.find_tasks(search_prop=sp)
        bot.send_message(search_request_id,
                         "Результатов по данному запросу может быть очень много, поэтому используйте кнопки "
                         "под этим сообщением, чтобы управлять поисковой выдачей",
                         reply_markup=continue_search_reply_buttons)
        search_requests[search_request_id] = tasks


@tl.job(interval=timedelta(minutes=30))
def is_new_task_available():
    load_dotenv(".env")
    nh = NotionHandler()
    task = nh.new_task_available()
    bot.send_chat_action(environ["ADMIN_TG_ID"], "typing", timeout=10)
    if task:
        if environ["LAST_TASK_ID"] != task.id:
            new_task_txt = nh.get_new_task(task)
            bot.send_message(environ["ADMIN_TG_ID"], new_task_txt, parse_mode="MarkdownV2")
            set_key(".env", "\nLAST_TASK_ID", task.id)


@tl.job(interval=timedelta(hours=12))
def if_status_almost_done_in_more_than_4_tasks():
    nh = NotionHandler()
    status_almost_done_in_more_than_4_tasks = nh.check_almst_done_statuses()
    bot.send_chat_action(environ["ADMIN_TG_ID"], "typing", timeout=10)
    if status_almost_done_in_more_than_4_tasks:
        bot.send_message(chat_id=environ["ADMIN_TG_ID"],
                         text="Уведомление:\n"
                              "Статус 'Почти готово' в более чем 4 задачах\n"
                              "Чтобы отобразить задачи используйте комманду: /search_status Почти готово",
                         parse_mode="MarkdownV2")


@tl.job(interval=timedelta(milliseconds=15))
def pooling():
    bot.polling()


while True:
    try:
        tl.start(block=True)
    except Exception as e:
        bot.send_message(environ["ADMIN_TG_ID"], e.__repr__())
