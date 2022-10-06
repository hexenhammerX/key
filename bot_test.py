#!/usr/bin/python3

import requests
import json

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton

from aiogram.types import BotCommand
from aiogram.utils.helper import Helper, HelperMode, ListItem
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher.filters import Text
from aiogram.utils.markdown import hlink

import logging

from datetime import datetime

def toFixed(numObj, digits=0):
    return f"{numObj:.{digits}f}"

######## Aiogram системные переменные ########

logging.basicConfig(level=logging.INFO)

bot = Bot(token='5432519427:AAEJlcq3L7r-qI68mCz21SmLCUdifsCHSi0')

API_KEY = 'bb3dd426f9b9c2a97a32ff73493d86bc15697bfb'
API_KEYFSSP = 'e966544edcccf4ce5bbeead5a332bf0083e93a70'

dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())
data = {}

async def set_bot_commands(bot: Bot):
    bot_commands = [
        BotCommand(command="/help", description="Get info about me"),
        BotCommand(command="/subscribe", description="set bot for a QnA task"),
        BotCommand(command="/start", description="set bot for free chat")
    ]
    # await bot.set_my_commands(bot_commands)
    # for command in commands_list:
    await bot.set_my_commands(bot_commands)

# Обработка команды /start
@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):
    await message.answer('ybrat')

# Обработка запросов к Redmine пользователей прошедших авторизацию
@dp.message_handler()
async def filter_options(message: types.Message, state: FSMContext):

    await message.answer('Wait, please...')

    res1 = requests.get('https://api-fns.ru/api/search?q=' + message.text + '&key=' + API_KEY)
    json_res1 = res1.json()
    #print(json_res1)

    '''
    Кнопка 1:
    Попадаем в json_res1['items'][0], если ищем по ИНН, и далее варианты:
    ИП -> ИННФЛ
    ЮЛ -> ИНН

    Кнопка 2 (сделаем позже):
    Попадаем в json_res1['items'][0], если ищем по ФИО, и далее варианты:
    ИП -> ИНН
    ЮЛ -> ИНН
    '''
    res1_variable_path = json_res1['items'][0]
    correct_path_is_found = False
    for current_path in ('ЮЛ', 'ИП'):
        correct_path_is_found = False
        try:
            res1_variable_path = json_res1['items'][0][current_path]
        except KeyError as e:
            pass
        else:
            correct_path_is_found = True

        if (correct_path_is_found):
            break

    if (not correct_path_is_found):
        print('correct path is not found')

    #INN_or_INNFL = json_res1['items'][0]
    #OGRN_or_OGRNIP = json_res1['items'][0]
    #if (path == 'ЮЛ'):
    #    INN_or_INNFL = res1_variable_path['ИНН']
    #    #OGRN_or_OGRNIP = res1_variable_path['ОГРН']
    #elif (path == 'ИП'):
    #    INN_or_INNFL = res1_variable_path['ИННФЛ']
    #    #OGRN_or_OGRNIP = res1_variable_path['ОГРНИП']

    #res2 = requests.get(
    #    'https://api-fns.ru/api/egr?req=' + json_res1['items'][0]['ЮЛ']['ИНН'] + '&key=' + API_KEY)
    #json_res2 = res2.json()
    #print(json_res2)

    res2 = requests.get(
        'https://api-fns.ru/api/egr?req=' + res1_variable_path['ИНН'] + '&key=' + API_KEY)
    json_res2 = res2.json()
    res2_variable_path = json_res2['items'][0]
    correct_path_is_found = False
    for current_path in ('ЮЛ', 'ИП'):
        correct_path_is_found = False
        try:
            res2_variable_path = json_res2['items'][0][current_path]
        except KeyError as e:
            pass
        else:
            correct_path_is_found = True

        if (correct_path_is_found):
            break

    if (not correct_path_is_found):
        print('correct path is not found')

    res3 = requests.get(
        'https://api-fns.ru/api/multinfo?req=' + res1_variable_path['ИНН'] + ',' + '&key=' + API_KEY)
    json_res3 = res3.json()
    #print(json_res3)

    res4 = requests.get(
        'https://api.damia.ru/fssp/isps?inn=' + res1_variable_path['ИНН'] + '&key=' + API_KEYFSSP)
    json_res4 = res4.json()
    #print(json_res4)

    res5 = requests.get(
        'https://api-fns.ru/api/bo?req=' + res1_variable_path['ИНН'] + '&key=' + API_KEY)
    json_res5 = res5.json()
    #print(json_res5)

    def get_json_value(func, format):
        try:
            # для стандартных строк
            if (format == 0):
                return func()
            # вывод суммы в формате ххх.хх (два знака после запятой)
            elif (format == 1):
                return str(toFixed(func(), 2))
            # вывод суммы в формате ххх,ххх,ххх (разделение огромноего числа запятыми)
            elif (format == 2):
                return "{:,}".format(func())
        except KeyError as e:
            return 'NE NAIDENO'

    def func1():
        return res1_variable_path['НаимСокрЮЛ']
    def func2():
        return res1_variable_path['ИНН']
    def func3():
        company_age = datetime.now().year - int(res2_variable_path['ДатаРег'][:4])
        return str(company_age)
    def func4():
        return res2_variable_path['ДатаРег']
    #def funcN():
    #   total_sum = 0.0
    #   for current_ip_number in json_res4[res1_variable_path['ИНН']]:
    #        if (json_res4[res1_variable_path['ИНН']][current_ip_number]['Статус'] == 'Не завершено'):
    #            total_sum += json_res4[res1_variable_path['ИНН']][current_ip_number]['Остаток']
    #   return total_sum
    def funcN():
       income_2021 = int(res2_variable_path['История']['ОткрСведения'][0]['СумДоход']) - int(res2_variable_path['История']['ОткрСведения'][0]['СумРасход'])
       return income_2021

    total_sum = 0.0
    for current_ip_number in json_res4[res1_variable_path['ИНН']]:
        if (json_res4[res1_variable_path['ИНН']][current_ip_number]['Статус'] == 'Не завершено'):
            total_sum += json_res4[res1_variable_path['ИНН']][current_ip_number]['Остаток']

    #income_2021 = int(res2_variable_path['История']['ОткрСведения'][0]['СумДоход']) - int(res2_variable_path['История']['ОткрСведения'][0]['СумРасход'])
    #company_age = datetime.now().year - int(res2_variable_path['ДатаРег'][:4])

    income_for_three_years = int(json_res5[res1_variable_path['ИНН']][str(datetime.now().year - 1)]['2400']) \
                             + int(json_res5[res1_variable_path['ИНН']][str(datetime.now().year - 2)]['2400']) \
                             + int(json_res5[res1_variable_path['ИНН']][str(datetime.now().year - 3)]['2400'])

    message_info = ('*Наименование:* ' + get_json_value(func1, 0)
                    + '*\nОБЩАЯ ИНФОРМАЦИЯ*'
                    + '\n'
                    + '*\nИНН:* ' + get_json_value(func2, 0)
                    + '*\nВозраст:* ' + get_json_value(func3, 0) + ' регистрация: ' + get_json_value(func4, 0)
                    #+ '*\nОГРН:* ' + OGRN_or_OGRNIP
                    + '*\nАдрес:* ' + res1_variable_path['АдресПолн']
                    #+ '*\nДата Регистрации:* ' + json_res2['items'][0]['ЮЛ']['ДатаРег']
                    + '*\nУставный капитал:* ' + "{:,}".format(int(res2_variable_path['Капитал']['СумКап']))
                    + '*\nОсновной вид деятельности:* ' + res2_variable_path['ОснВидДеят']['Код'] + ' ' + res2_variable_path['ОснВидДеят']['Текст']
                    + '*\nРегистратор:* ' + res2_variable_path['НО']['Рег']
                    + '*\nОРГАНЫ УПРАВЛЕНИЯ*'
                    + '\n'
                    + '*\nГенеральный директор:* ' + res2_variable_path['Руководитель']['ФИОПолн']
                    + '*\nИНН:* ' + res2_variable_path['Руководитель']['ИННФЛ'] + ' ' + 'период с' + ' ' + res2_variable_path['Руководитель']['Дата']
                    + '*\nУчредители:* ' + res2_variable_path['Учредители'][0]['УчрФЛ']['ФИОПолн'] + ' ' + res2_variable_path['Учредители'][0]['СуммаУК']
                    + '*\nИНН:* ' + res2_variable_path['Учредители'][0]['УчрФЛ']['ИННФЛ'] + ' ' + 'Чистая прибыль от бизнеса на ' + res2_variable_path['Учредители'][0]['Дата'] + ' ~ ' + res2_variable_path['Учредители'][0]['СуммаУК']
                    + '*\nФИНАНСОВАЯ ИНФОРМАЦИЯ*'
                    + '\n'
                    + '*\nСреднесписочная численность:~ * ' + res2_variable_path['ОткрСведения']['КолРаб']
                    + '*\nВыручка от продажи за 2021:* ' + "{:,}".format(int(json_res3['items'][0]['ЮЛ']['Финансы']['Выручка']))
                    #+ '*\nЧистая прибыль за 2021:* ' + "{:,}".format(income_2021)
                    + '*\nЧистая прибыль за 2021:* ' + get_json_value(funcN, 2)
                    + '*\nЧистая прибыль за последние три года:* ' + "{:,}".format(income_for_three_years)
                #   + '*\nЧистая прибыль за последние три года:* ' + get_json_value(funcN, 2)
                    + '*\nИсполнительное производство:* '
                    + '*\nКак ответчик:* ' + str(toFixed(total_sum, 2))
                    #+ '*\nКак ответчик:* ' + get_json_value(funcN, 1)
                    + '*\nПоследние изменения были совершены* ')

    await message.answer(message_info, parse_mode='Markdown')


if __name__ == '__main__':
    # scheduler.start()
    executor.start_polling(dp, skip_updates=True)