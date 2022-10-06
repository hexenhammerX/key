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
    await message.answer('Выберите действие')


# Обработка запросов к Redmine пользователей прошедших авторизацию
@dp.message_handler()
async def filter_options(message: types.Message, state: FSMContext):
    await message.answer('Wait, please...')

    res1 = requests.get('https://api-fns.ru/api/search?q=' + message.text + '&key=' + API_KEY)
    #print(res1)
    json_res1 = res1.json()
    #print(json_res1)

    res2 = requests.get(
        'https://api-fns.ru/api/egr?req=' + json_res1['items'][0]['ЮЛ']['ИНН'] + '&key=' + API_KEY)
    json_res2 = res2.json()
    #print(json_res2)

    res3 = requests.get(
        'https://api-fns.ru/api/multinfo?req=' + json_res1['items'][0]['ЮЛ']['ИНН'] + ',' + json_res1['items'][0]['ЮЛ'][
            'ОГРН'] + '&key=' + API_KEY)
    json_res3 = res3.json()
    #print(json_res3)

    res4 = requests.get(
        'https://api.damia.ru/fssp/isps?inn=' + json_res1['items'][0]['ЮЛ']['ИНН'] + '&key=' + API_KEYFSSP)
    json_res4 = res4.json()
    #print(json_res4)

    res5 = requests.get(
        'https://api-fns.ru/api/bo?req=' + json_res1['items'][0]['ЮЛ']['ИНН'] + '&key=' + API_KEY)
    json_res5 = res5.json()
    #print(json_res5)

    total_sum = 0.0
    for current_ip_number in json_res4[json_res1['items'][0]['ЮЛ']['ИНН']]:
        if (json_res4[json_res1['items'][0]['ЮЛ']['ИНН']][current_ip_number]['Статус'] == 'Не завершено'):
            total_sum += json_res4[json_res1['items'][0]['ЮЛ']['ИНН']][current_ip_number]['Остаток']

    income_2021 = int(json_res2['items'][0]['ЮЛ']['История']['ОткрСведения'][0]['СумДоход']) - int(json_res2['items'][0]['ЮЛ']['История']['ОткрСведения'][0]['СумРасход'])
    company_age = datetime.now().year - int(json_res2['items'][0]['ЮЛ']['ДатаРег'][:4])

    income_for_three_years = int(json_res5[json_res1['items'][0]['ЮЛ']['ИНН']][str(datetime.now().year - 1)]['2400']) \
                             + int(json_res5[json_res1['items'][0]['ЮЛ']['ИНН']][str(datetime.now().year - 2)]['2400']) \
                             + int(json_res5[json_res1['items'][0]['ЮЛ']['ИНН']][str(datetime.now().year - 3)]['2400'])

    message_info = ('*Наименование:* ' + json_res1['items'][0]['ЮЛ']['НаимСокрЮЛ']
                    + '*\nОБЩАЯ ИНФОРМАЦИЯ*'
                    + '\n'
                    + '*\nИНН:* ' + json_res1['items'][0]['ЮЛ']['ИНН']
                    + '*\nВозраст:* ' + str(company_age) + 'регистрация: ' + json_res2['items'][0]['ЮЛ']['ДатаРег']
                    #+ '*\nОГРН:* ' + json_res1['items'][0]['ЮЛ']['ОГРН']
                    + '*\nАдрес:* ' + json_res1['items'][0]['ЮЛ']['АдресПолн']
                    #+ '*\nДата Регистрации:* ' + json_res2['items'][0]['ЮЛ']['ДатаРег']
                    + '*\nУставный капитал:* ' + json_res2['items'][0]['ЮЛ']['Капитал']['СумКап']
                    + '*\nОсновной вид деятельности:* ' + json_res2['items'][0]['ЮЛ']['ОснВидДеят']['Код'] + json_res2['items'][0]['ЮЛ']['ОснВидДеят']['Текст']
                    + '*\nРегистратор:* ' + json_res2['items'][0]['ЮЛ']['НО']['Рег']
                    + '*\nОРГАНЫ УПРАВЛЕНИЯ*'
                    + '\n'
                    + '*\nГенеральный директор:* ' + json_res2['items'][0]['ЮЛ']['Руководитель']['ФИОПолн']
                    + '*\nИНН:* ' + json_res2['items'][0]['ЮЛ']['Руководитель']['ИННФЛ'] + ' ' + 'период с'+  ' ' + json_res2['items'][0]['ЮЛ']['Руководитель']['Дата']
                    + '*\nУчредители:* ' + json_res2['items'][0]['ЮЛ']['Учредители'][0]['УчрФЛ']['ФИОПолн'] + ' ' + json_res2['items'][0]['ЮЛ']['Учредители'][0]['СуммаУК']
                    + '*\nИНН:* ' + json_res2['items'][0]['ЮЛ']['Учредители'][0]['УчрФЛ']['ИННФЛ'] + ' ' + 'Чистая прибыль от бизнеса на ' + json_res2['items'][0]['ЮЛ']['Учредители'][0]['Дата'] + ' ~ ' + json_res2['items'][0]['ЮЛ']['Учредители'][0]['СуммаУК']
                    + '*\nФИНАНСОВАЯ ИНФОРМАЦИЯ*'
                    + '\n'
                    + '*\nСреднесписочная численность:~ * ' + json_res2['items'][0]['ЮЛ']['ОткрСведения']['КолРаб']
                    + '*\nВыручка от продажи за 2021:* ' + "{:,}".format(int(json_res3['items'][0]['ЮЛ']['Финансы']['Выручка']))
                    + '*\nЧистая прибыль за 2021:* ' + "{:,}".format(income_2021)
                    + '*\nЧистая прибыль за последние три года:* ' + str(income_for_three_years)
                    + '*\nИсполнительное производство:* '
                    + '*\nКак ответчик:* ' + str(toFixed(total_sum, 2))
                    + '*\nПоследние изменения были совершены* ')

    await message.answer(message_info, parse_mode='Markdown')
    #message.edit_text('12345')
    #bot.edit_message_text(message_id=message.message_id, text='1235555')


if __name__ == '__main__':
    # scheduler.start()
    executor.start_polling(dp, skip_updates=True)