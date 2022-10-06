from random import randint
from time import sleep

import sqlite3

import requests

from redminelib import Redmine, exceptions

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.helper import Helper, HelperMode, ListItem
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher.filters import Text
from aiogram.utils.markdown import hlink

import datetime, threading

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import logging

import config


######## Aiogram системные переменные ########

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.TOKEN)  # brmoon_bot
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())
data = {}

scheduler = AsyncIOScheduler()


# Класс регистрации состояний пользователей
class reg(StatesGroup):
    auth = State()
    auth_accept = State()
    add_note = State()
    add_theme = State()
    add_descripton = State()
    add_issue = State()
    add_location = State()
    add_priority = State()
    add_service = State()
    add_project = State()
    add_whatcher = State()


######## Redmine API системные переменные ########

rm_url = config.rm_url
api_key = config.api_key
rm_project = config.rm_project
bot_token = config.TOKEN
chat_id = config.chat_id

######## База данных SQL ########

database = 'tg_auth_users.db'


# Новый пользователь БД
def bd_new(user_info):
    try:
        con = sqlite3.connect(database)
        cur = con.cursor()
        cur.execute(' ' ' CREATE TABLE IF NOT EXISTS auth_users ( \
						user_id INT AUTO_INCREMENT, \
						tg_chat_id varchar(20), \
						user_api_key varchar(50), \
						PRIMARY KEY (user_id) ) ' ' ')

        cur.execute(' ' ' INSERT INTO auth_users(tg_chat_id,user_api_key) VALUES (?, ?)' ' ', user_info)
        logging.info('Add user on database')
        con.commit()
        cur.close()

    except sqlite3.Error as e:
        if con:
            con.rollback()
            logging.error(e)

    finally:
        if con:
            cur.close()
            logging.info('Connection database closed')


# Существующий пользователь БД
def bd_current(tg_chat_id):
    try:
        con = sqlite3.connect(database)
        cur = con.cursor()

        info = cur.execute('SELECT * FROM auth_users WHERE tg_chat_id=?', (tg_chat_id,))
        info = info.fetchone()
        if info is None:
            # Делаем когда нету человека в бд
            return False
        else:
            # Делаем когда есть человек в бд
            logging.info('User on database')
            return True


    except sqlite3.Error as e:
        if con: con.rollback()
        print("Ошибка при работе с SQLite", e)

    finally:
        if con:
            cur.close()
            print("Соединение с SQLite закрыто")


# Существующий пользователь БД с валидным api ключом, 
def bd_user_api_key(tg_chat_id):
    try:
        con = sqlite3.connect(database)
        cur = con.cursor()

        info = cur.execute('SELECT * FROM auth_users WHERE tg_chat_id=?', (tg_chat_id,))
        info = info.fetchone()
        if info is None:
            # Делаем когда нету человека в бд
            return False
        else:
            # Делаем когда есть человек в бд
            user_api_key = info[2]
            if check_user_api_key(user_api_key):
                return user_api_key
            else:
                cur.execute('DELETE FROM auth_users where tg_chat_id=?', (tg_chat_id,))
                con.commit()
                return False

    except sqlite3.Error as e:
        if con: con.rollback()
        print("Ошибка при работе с SQLite", e)

    finally:
        if con:
            cur.close()
            print("Соединение с SQLite закрыто")


# Проверка существующих пользователей в БД
def bd_start_auth_users():
    try:
        con = sqlite3.connect(database)
        con.row_factory = lambda cursor, row: row[0]
        cur = con.cursor()

        info = cur.execute('SELECT tg_chat_id FROM auth_users')
        users_id = info.fetchall()

        return (users_id)

    except sqlite3.Error as e:
        if con: con.rollback()
        print("Ошибка при работе с SQLite", e)

    finally:
        if con:
            cur.close()
            print("Соединение с SQLite закрыто")


# Добавление наблюдателей к задаче
def bd_add_whatcher(tg_chat_id, whatcher):
    try:
        con = sqlite3.connect(database)
        cur = con.cursor()
        cur.execute(' ' ' CREATE TABLE IF NOT EXISTS user_whatcher ( \
						user_id INT AUTO_INCREMENT, \
						tg_chat_id, \
						whatchers, \
						PRIMARY KEY (user_id) ) ' ' ')

        cur.execute(' ' ' INSERT INTO user_whatcher(whatchers) VALUES (?)' ' ', whatcher)
        logging.info('Add user on database')
        con.commit()
        cur.close()

    except sqlite3.Error as e:
        if con:
            con.rollback()
            logging.error(e)

    finally:
        if con:
            cur.close()
            logging.info('Connection database closed')


######## Функции Redmine API ########

### Проверка на существование API ключа пользователя
def check_user_api_key(user_api_key):
    redmine = Redmine(url=rm_url, key=user_api_key)
    try:
        user = redmine.user.get('current')
        print('API validate')
        return True
    except exceptions.AuthError as e:
        print('Ошибка Redmine API', e)
        return False


### Создание новой задачи
def new_issue(theme, description, username_tg, user_api_key, location, priority_id, service_name, project_name):
    redmine = Redmine(url=rm_url, key=user_api_key)
    try:
        new_issue = redmine.issue.create(
            project_id=rm_project,
            assigned_to_id=46,
            subject=theme,
            description=description \
                        + '\n'
                        + 'Логин телеграм для связи: ' + str(username_tg),
            tracker_id=4,
            priority_id=priority_id,
            status_id=1,
            custom_fields=[{"id": 3, "value": location}, {"id": 12, "value": "0"}, {"id": 15, "value": "0"},
                           {"id": 13, "value": project_name},
                           {"id": 33, "value": service_name},  # TODO в продакшн Redmine id поля "Услуга = 32, а не 33
                           {'id': 17, 'value': 'telegram'},
                           {'id': 20, "name": "Тип заявки", 'value': 'Запрос на обслуживание'}],
        )
        return new_issue
    except Exception as e:
        print("ERROR: new_issue()", e)
        return False


### Создание новой задачи с файлом
def new_issue_upload(theme, description, username_tg, user_api_key, location, file, priority_id, service_name,
                     project_name):
    redmine = Redmine(url=rm_url, key=user_api_key)
    try:
        new_issue = redmine.issue.create(
            project_id=rm_project,
            assigned_to_id=46,
            subject=theme,
            description=description \
                        + '\n'
                        + 'Логин телеграм для связи: ' + str(username_tg),
            tracker_id=4,
            priority_id=priority_id,
            status_id=1,
            custom_fields=[{"id": 3, "value": location}, {"id": 12, "value": "0"}, {"id": 15, "value": "0"},
                           {"id": 13, "value": project_name},
                           {"id": 33, "value": service_name},  # TODO в продакшн Redmine id поля "Услуга = 32, а не 33
                           {'id': 17, 'value': 'telegram'},
                           {'id': 20, "name": "Тип заявки", 'value': 'Запрос на обслуживание'}],
            uploads=[{"path": "upload/" + file, 'filename': file}]
        )
        return new_issue
    except Exception as e:
        print("ERROR: new_issue_upload()", e)
        return False


### Открытые задачи пользователя
def issue_filter(user_api_key):
    redmine = Redmine(url=rm_url, key=user_api_key)
    user = redmine.user.get('current')
    # issues = list(redmine.issue.filter(project_id=1, status_id='open', author_id=user.id))
    issues = list(redmine.issue.filter(status_id='open', author_id=user.id))
    return issues


### Отслеживаемые задачи пользователя
def issue_watcher(user_api_key):
    redmine = Redmine(url=rm_url, key=user_api_key)
    user = redmine.user.get('current')
    issues = list(redmine.issue.filter(status_id='open', watcher_id=user.id))
    return issues


### Последняя задача пользователя
def last_issue_user(user_api_key):
    redmine = Redmine(url=rm_url, key=user_api_key)
    user = redmine.user.get('current')
    issues = list(redmine.issue.filter(status_id=1, author_id=user.id))
    return issues[0]


### Формирование информации по задаче в сообщение
# TODO подумать, добавлять ли сюда информацию об услуге
def issues_filter_send(issue_info):
    ilink = hlink(str(issue_info.id), issue_info.url)

    messageMail = ('Заявка №: ' + ilink + '\n' +
                   'Тема: ' + str(issue_info['subject']) + '\n' +
                   'Отдел: ' + str(issue_info['project']) + '\n' +
                   # 'Площадка: ' + str(issue_info['custom_fields'][0]['value']) + '\n' +
                   'Приоритет: ' + str(issue_info['priority']) + '\n' +
                   'Статус: ' + str(issue_info['status']))

    return messageMail


### Описание задачи
def issue_description(issue_id, user_api_key):
    redmine = Redmine(url=rm_url, key=user_api_key)
    issue = redmine.issue.get(issue_id)
    description = issue['description']
    return description


### Последний комментарий
def issue_last_comment(issue_id, user_api_key):
    redmine = Redmine(url=rm_url, key=user_api_key)
    issue = redmine.issue.get(issue_id, include=['journals'])
    last_comment = "Комментариев нет"
    for journal in reversed(issue.journals):
        if journal.notes != '':
            last_comment = str(journal.created_on) + "\n" + str(journal.user) + ' писал(а):' + "\n" + str(journal.notes)
            break
    return last_comment


### История комментариев
def issue_history_notes(issue_id, user_api_key):
    redmine = Redmine(url=rm_url, key=user_api_key)
    issue = redmine.issue.get(issue_id, include=['journals'])
    # last_comment = "Комментариев нет"
    last_comment = ''
    for journal in issue.journals:
        if journal.notes != '':
            last_comment = str(journal.created_on) + "\n" + str(journal.user) + ' писал(а):' + "\n" + str(journal.notes)

    return last_comment


### Добавление комментария к задаче
def issue_add_comment(issue_id, user_api_key, note):
    redmine = Redmine(url=rm_url, key=user_api_key)
    redmine.issue.update(issue_id, notes=note)


### Удалить себя из наблюдателей
def issue_remove_watcher(issue_id, user_api_key):
    redmine = Redmine(url=rm_url, key=user_api_key)
    user = redmine.user.get('current')
    issue = redmine.issue.get(issue_id)
    issue.watcher.remove(user.id)


### Добавить наблюдателей к задаче
def issue_add_watcher(issue_id, watcher):
    redmine = Redmine(url=rm_url, key=api_key)
    issue = redmine.issue.get(issue_id)
    issue.watcher.add(watcher)


# Список проектов
def redmine_projects_cf_13():
    redmine = Redmine(url=rm_url, key=api_key)
    fields = redmine.custom_field.get(13)
    projects_dict = {}
    i = 0
    for field in fields['possible_values']:
        projects_dict[i] = field['value']
        i += 1
    return projects_dict


# Имя проекта из словаря
def redmine_project_name(project_id):
    projects_dict = redmine_projects_cf_13()
    return projects_dict[int(project_id)]


# Список услуг
def redmine_services_cf_33():
    redmine = Redmine(url=rm_url, key=api_key)
    fields = redmine.custom_field.get(33)  # TODO в продакшн Redmine id поля "Услуга = 32, а не 33
    services_dict = {}
    i = 0
    for field in fields['possible_values']:
        services_dict[i] = field['value']
        i += 1
    return services_dict


# Имя услуги из словаря
def redmine_service_name(service_id):
    services_dict = redmine_services_cf_33()
    return services_dict[int(service_id)]


# Список наблюдателей
def redmine_whatchers(name):
    redmine = Redmine(url=rm_url, key=api_key)
    users = redmine.user.filter(name=name, limit=20)
    return users


########### Основная логика работы Telegram bot #############

############ Клавиатуры ##############
# Генерация основной клавиатуры
def main_keyboard(menu_status):
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton('Мои заявки'),
        types.KeyboardButton('Отслеживаемые заявки'),
        types.KeyboardButton('Создать заявку'),
    ]
    if menu_status == 'main':
        keyboard.add(*buttons)
    return keyboard


# Генерация callback кнопок и клавиатуры
cb = CallbackData("name", "id", "data")


def issue_kb(issue_info, watcher):
    buttons = [
        types.InlineKeyboardButton(text="Описание", callback_data=cb.new(id=1, data=f'{issue_info["id"]}')),
        types.InlineKeyboardButton(text='История комментариев', callback_data=cb.new(id=4, data=f'{issue_info["id"]}')),
        types.InlineKeyboardButton(text='Добавить комментарий', callback_data=cb.new(id=3, data=f'{issue_info["id"]}')),
    ]
    if watcher == 'yes':
        buttons.append(
            types.InlineKeyboardButton(text='Не следить', callback_data=cb.new(id=2, data=f'{issue_info["id"]}')))
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(*buttons)
    return keyboard


def kb_add_watcher(issue_id):
    buttons = [
        types.InlineKeyboardButton(text="Да", callback_data=cb.new(id=10, data=f'{issue_id}')),
        types.InlineKeyboardButton(text='Нет', callback_data='cancel_'),
    ]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(*buttons)
    return keyboard


# Клавиатура для выбора площадки
def kb_location():
    buttons = [
        InlineKeyboardButton(text="Брянск", callback_data="addissue_Брянск"),
        InlineKeyboardButton(text="Брянск-2", callback_data="addissue_Брянск-2"),
        InlineKeyboardButton(text="Череповец", callback_data="addissue_Череповец"),
        InlineKeyboardButton(text="Челябинск", callback_data="addissue_Челябинск"),
        InlineKeyboardButton(text="Ярославль", callback_data="addissue_Ярославль"),
        InlineKeyboardButton(text="Все", callback_data="addissue_Все"),
        InlineKeyboardButton(text="Отмена", callback_data="cancel_"),
    ]
    keyboard = InlineKeyboardMarkup()
    keyboard.add(*buttons)
    return keyboard


# Клавиатура выбора приоритета
def kb_priority():
    buttons = [
        InlineKeyboardButton(text="Нормальный", callback_data="addpriority_3"),
        InlineKeyboardButton(text="Высокий", callback_data="addpriority_4"),
        InlineKeyboardButton(text="Отмена", callback_data="cancel_"),
    ]
    keyboard = InlineKeyboardMarkup()
    keyboard.add(*buttons)
    return keyboard


# Клавиатура выбора услуги
def kb_services():
    services_dict = redmine_services_cf_33()
    buttons = []
    for key, value in services_dict.items():
        buttons.append(InlineKeyboardButton(text=value, callback_data=f"service_{key}"))
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(*buttons)
    return keyboard


# Клавиатура выбора проекта
def kb_projects():
    projects_dict = redmine_projects_cf_13()
    buttons = []
    for key, value in projects_dict.items():
        buttons.append(InlineKeyboardButton(text=value, callback_data=f"project_{key}"))
    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.add(*buttons)
    return keyboard


# Клавиатура выбора наблюдателей
def kb_users_id(user):
    buttons = [
        InlineKeyboardButton(text='Добавить', callback_data=f"userid_{user.id}"),
    ]
    keyboard = InlineKeyboardMarkup()
    keyboard.add(*buttons)
    return keyboard


# Клавиатура с кнопкой отмены
def kb_cancel():
    buttons = [
        InlineKeyboardButton(text="Отмена", callback_data="cancel_"),
    ]
    keyboard = InlineKeyboardMarkup()
    keyboard.add(*buttons)
    return keyboard


################# Message handlers ######################

# Обработка команды /start
@dp.message_handler(commands='start', state="*")
async def cmd_start(message: types.Message):
    tg_chat_id = message.from_user.id
    if bd_current(tg_chat_id):
        # Проверяем наличие chat_id пользователя в БД
        await reg.auth_accept.set()
        keyboard = main_keyboard('main')
        await message.answer('Выберите действие', reply_markup=keyboard)
    else:
        await message.answer('Введите ваш ключ доступа к API')
        await reg.auth.set()


# Состояние авторизации, проверка валидности api_key
@dp.message_handler(state=reg.auth)
async def auth_user(message: types.Message, state: FSMContext):
    await state.update_data()
    user_info = []
    api_key = str(message.text.lower())
    tg_chat_id = message.from_user.id
    tg_username = message.from_user.username
    check_auth = check_user_api_key(api_key)
    if check_auth:
        user_info.append(tg_chat_id)
        user_info.append(api_key)
        print('Пользователь', tg_username, 'авторизован')
        bd_new(user_info)
        await reg.auth_accept.set()
        keyboard = main_keyboard('main')
        await message.answer('Выберите действие', reply_markup=keyboard)

    else:
        await message.answer('Ошибка авторизации')
        print('Пользователь', tg_username, 'invalid api_key')


# Обработка запросов к Redmine пользователей прошедших авторизацию
@dp.message_handler(state=reg.auth_accept)
async def filter_options(message: types.Message, state: FSMContext):
    await state.update_data()

    if message.text.lower() == 'создать заявку':
        await message.answer('Введите тему заявки', reply_markup=kb_cancel())
        await reg.add_theme.set()
    if message.text.lower() == 'мои заявки':
        await check_issue_filter(message)
    if message.text.lower() == 'отслеживаемые заявки':
        await check_issue_watcher(message)


### Проверка задач и отправка каждой 
async def check_issue_filter(message: types.Message):
    tg_chat_id = message.from_user.id
    user_api_key = bd_user_api_key(tg_chat_id)
    if user_api_key:
        await message.answer('Проверяю заявки')
        if not issue_filter(user_api_key):
            await message.answer('Открытых заявок нет')
        else:
            for issue_info in reversed(issue_filter(user_api_key)):
                issue = issues_filter_send(issue_info)
                await message.answer(issue, reply_markup=issue_kb(issue_info, ''), parse_mode=types.ParseMode.HTML)
    else:
        remove_keyboard = types.ReplyKeyboardRemove()
        await message.answer('Ваш ключ доступа к API устарел, для прохождения авторизации пришлите команду /start',
                             reply_markup=remove_keyboard)
        await reg.auth.set()


### Отслеживаемые Проверка задач и отправка каждой
async def check_issue_watcher(message: types.Message):
    tg_chat_id = message.from_user.id
    user_api_key = bd_user_api_key(tg_chat_id)
    if user_api_key:
        await message.answer('Проверяю заявки')
        if not issue_watcher(user_api_key):
            await message.answer('Отслеживаемых заявок нет')
        else:
            for issue_info in reversed(issue_watcher(user_api_key)):
                issue = issues_filter_send(issue_info)
                await message.answer(issue, reply_markup=issue_kb(issue_info, 'yes'), parse_mode=types.ParseMode.HTML)
    else:
        remove_keyboard = types.ReplyKeyboardRemove()
        await reg.auth.set()


##### Создание новой задачи добавление темы
@dp.message_handler(state=reg.add_theme)
async def add_issue_theme(message: types.Message, state: FSMContext):
    tg_chat_id = message.from_user.id
    user_api_key = bd_user_api_key(tg_chat_id)
    if user_api_key:
        async with state.proxy() as issue_data:
            issue_data['theme'] = message.text
            issue_data['user_api_key'] = user_api_key
            issue_data['username_tg'] = message.from_user.username
            issue_data['upload_file'] = 'None'
            await message.answer(text='Ввведите описание заявки', reply_markup=kb_cancel())
            await reg.add_descripton.set()
    else:
        remove_keyboard = types.ReplyKeyboardRemove()
        await message.answer('Ваш ключ доступа к API устарел, для прохождения авторизации пришлите команду /start',
                             reply_markup=remove_keyboard)
        await reg.auth.set()


##### Создание новой задачи добавление описания
@dp.message_handler(state=reg.add_descripton)
async def add_issue_description(message: types.Message, state: FSMContext):
    async with state.proxy() as issue_data:
        issue_data['description'] = message.text
        await message.answer('Выберите площадку', reply_markup=kb_location())
        await reg.add_location.set()


##### Добавление комментария к задаче ##############
@dp.message_handler(state=reg.add_note)
async def add_notes(message: types.Message, state: FSMContext):
    tg_chat_id = message.chat.id
    user_api_key = bd_user_api_key(tg_chat_id)
    async with state.proxy() as data:
        issue_id = data['issue_id']
        note = message.text.lower()
        issue_add_comment(issue_id, user_api_key, note)
        await message.reply('Ваш комментарий добавлен к заявке № ' + issue_id)
        await reg.auth_accept.set()


# Скачивание фото и файлов
@dp.message_handler(content_types=['photo', 'document'], state=reg.add_descripton)
async def photo_or_doc_handler(message: types.Message, state: FSMContext):
    folder = "upload/"
    if message.content_type == 'photo':
        document_id = message.photo[0].file_id
        file_info = await bot.get_file(document_id)
        name_file = file_info.file_path.split("/")[1]
        async with state.proxy() as issue_data:
            issue_data['upload_file'] = file_info.file_unique_id + '_' + name_file
            await message.photo[-1].download(folder + file_info.file_unique_id + '_' + name_file)
    elif message.content_type == 'document':
        document = message.document
        async with state.proxy() as issue_data:
            issue_data['upload_file'] = document.file_unique_id + '_' + document.file_name
            await message.document.download(folder + document.file_unique_id + '_' + document.file_name)


# Добавление наблюдателей
@dp.message_handler(state=reg.add_whatcher)
async def add_whatcher(message: types.Message, state: FSMContext):
    name = message.text
    for user in redmine_whatchers(name):
        await message.answer(str(user), reply_markup=kb_users_id(user))


#################### Callback handlers ################## 

# Обработка Callback кнопок к задачам
@dp.callback_query_handler(cb.filter(), state=reg.auth_accept)
async def send_callback(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    await state.update_data()
    tg_chat_id = call.message.chat.id
    user_api_key = bd_user_api_key(tg_chat_id)
    if user_api_key:
        if callback_data['id'] == '1':
            description = issue_description(callback_data['data'], user_api_key)
            await call.message.reply(description)

        if callback_data['id'] == "2":
            issue_remove_watcher(callback_data['data'], user_api_key)
            await call.answer('Не следить')

        if callback_data['id'] == "3":
            async with state.proxy() as data:
                data['issue_id'] = callback_data['data']
                await call.message.reply('Пришлите комментарий к заявке ' + callback_data['data'],
                                         reply_markup=kb_cancel())
                await reg.add_note.set()

        if callback_data['id'] == "4":
            history_notes = issue_history_notes(callback_data['data'], user_api_key)
            last_comment = issue_last_comment(callback_data['data'], user_api_key)
            if last_comment != "Комментариев нет":
                await call.message.reply(history_notes)
            else:
                await call.answer(last_comment, show_alert=True)

        if callback_data['id'] == "10":
            issue = callback_data['data']
            async with state.proxy() as data:
                data['issue_id'] = issue
                await call.message.edit_text(
                    f'Добавление наблюдателей к заявке {issue}. Для поиска наблюдателя пришлите его Фамилию, Имя или логин')
                await reg.add_whatcher.set()

    else:
        remove_keyboard = types.ReplyKeyboardRemove()
        await call.answer('Ваш ключ доступа к API устарел, для прохождения авторизации пришлите команду /start')
        await reg.auth.set()


#
async def get_description(callback_query: types.CallbackQuery):
    tg_chat_id = call.message.chat.id
    user_api_key = bd_user_api_key(tg_chat_id)
    if user_api_key:
        length_description = issue_description(callback_query.data, user_api_key)
        if len(length_description) > 200:
            await callback_query.message.reply(length_description)
        else:
            await callback_query.answer(length_description, show_alert=True)
    else:
        await call.answer('Ваш ключ доступа к API устарел, для прохождения авторизации пришлите команду /start')
        await reg.auth.set()


# Выбор площадки
@dp.callback_query_handler(Text(startswith="addissue_"), state=reg.add_location)
async def callback_add_issue_location(call: types.CallbackQuery, state: FSMContext):
    action = call.data.split("_")[1]  # Название площадки из колбэка
    async with state.proxy() as issue_data:
        issue_data['location'] = action
        await call.message.edit_text('Выберите приоритет', reply_markup=kb_priority())
        await reg.add_priority.set()


# Выбор приоритета
@dp.callback_query_handler(Text(startswith="addpriority_"), state=reg.add_priority)
async def callback_add_issue_location(call: types.CallbackQuery, state: FSMContext):
    priority_id = call.data.split("_")[1]  # Номер приоритета из колбэка
    async with state.proxy() as issue_data:
        issue_data['priority'] = priority_id
        await call.message.edit_text('Выберите услугу', reply_markup=kb_services())
        await reg.add_service.set()


# Выбор услуги
@dp.callback_query_handler(Text(startswith="service_"), state=reg.add_service)
async def callback_add_service(call: types.CallbackQuery, state: FSMContext):
    service_id = call.data.split("_")[1]  # Номер услуги из колбэка
    await call.answer()
    service_name = redmine_service_name(service_id)
    async with state.proxy() as issue_data:
        issue_data['service'] = service_name
        await call.message.edit_text('Выберите проект', reply_markup=kb_projects())
        await reg.add_project.set()


# Выбор Проекта
@dp.callback_query_handler(Text(startswith="project_"), state=reg.add_project)
async def callback_add_issue_location(call: types.CallbackQuery, state: FSMContext):
    project_id = call.data.split("_")[1]  # Номер проекта из колбэка
    await call.answer()
    project_name = redmine_project_name(project_id)
    async with state.proxy() as issue_data:
        if issue_data['upload_file'] == 'None':
            issue_create = new_issue(issue_data['theme'], issue_data['description'], issue_data['username_tg'],
                                     issue_data['user_api_key'], issue_data['location'], issue_data['priority'],
                                     issue_data['service'], project_name)
        else:
            issue_create = new_issue_upload(issue_data['theme'], issue_data['description'], issue_data['username_tg'],
                                            issue_data['user_api_key'], issue_data['location'],
                                            issue_data['upload_file'], issue_data['priority'], issue_data['service'],
                                            project_name)
        if issue_create:
            await call.message.edit_text(f'Создана заявка {str(issue_create.url)}')
            await call.message.answer('Добавить наблюдателей?', reply_markup=kb_add_watcher(issue_create.id))
        else:
            await call.message.edit_text('Возникла ошибка при создании, повторите попытку')
        await reg.auth_accept.set()


# Добавление наблюдателей
@dp.callback_query_handler(Text(startswith="userid_"), state=reg.add_whatcher)
async def callback_add_watcher(call: types.CallbackQuery, state: FSMContext):
    whatcher_id = call.data.split("_")[1]  # ID наблюдателя из колбэка
    async with state.proxy() as data:
        issue = data['issue_id']
        issue_add_watcher(issue, whatcher_id)
    await call.answer('наблюдатель добавлен')
    await call.message.answer('Завершить добавление', reply_markup=kb_cancel())


# Отмена всех callback
@dp.callback_query_handler(text="cancel_", state='*')
async def callback_loc_cancel(call: types.CallbackQuery, state: FSMContext):
    await bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)
    await reg.auth_accept.set()


#### Авторизация пользователей при перезапуске бота
async def set_user_state():
    try:
        for user_id in bd_start_auth_users():
            state = dp.current_state(user=user_id)
            await state.set_state(reg.auth_accept)
    except:
        print('None users in Database')


async def on_startup(dp):
    await set_user_state()


if __name__ == '__main__':
    # scheduler.start()
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
