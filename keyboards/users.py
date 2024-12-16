from aiogram.types import InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from geopy.distance import geodesic

from database.database import get_all_quests


def menu_kb(is_premium: bool = False):
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text='Найти ближайший квест', request_location=True))
    kb.row(KeyboardButton(text='Все квесты'))
    kb.row(KeyboardButton(text='Случайный квест'))
    kb.row(KeyboardButton(text='Личный кабинет'))
    if not is_premium:
        kb.row(KeyboardButton(text='Купить неограниченный доступ'))
    kb.row(KeyboardButton(text='Помощь и поддержка'))
    return kb.as_markup()


async def quests_kb(user_lat: float = None, user_lon: float = None):
    kb = InlineKeyboardBuilder()

    all_quests = await get_all_quests()
    for quest in all_quests:
        if user_lat and user_lon:
            user_coordinates = (user_lat, user_lon)
            place_lat, place_lon = str(quest[5]).split(',')
            place_coordinates = (float(place_lat), float(place_lon))
            distance = geodesic(user_coordinates, place_coordinates).kilometers
            button_text = f'[{distance:.2f} км.] [{quest[3]}] {quest[1]}'  # Дистанция Сложность Название
        else:
            button_text = f'[{quest[3]}] {quest[1]}'
        kb.row(InlineKeyboardButton(text=button_text, callback_data=f'quest:{quest[0]}'))  # quest_id

    return kb.as_markup()


def quest_info_kb(quest_id: int):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text='Начать квест', callback_data=f'start_quest:{quest_id}'))
    kb.row(InlineKeyboardButton(text='Задать вопрос', url='https://t.me/wsxsss'))
    return kb.as_markup()


def hint_kb(quest_id: int, step: int):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text='Подсказка', callback_data=f'hint:{quest_id}:{step}'))
    return kb.as_markup()


def sub_kb():
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text='Купить неограниченный доступ'))
    kb.row(KeyboardButton(text='Главное меню'))
    return kb.as_markup()
