from aiogram.types import InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def admin_kb():
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text='Добавить квест', callback_data='add_quest'))
    kb.add(InlineKeyboardButton(text='Удалить квест', callback_data='delete_quest'))
    return kb.as_markup()


def delete_quest_kb(all_quests):
    kb = InlineKeyboardBuilder()
    for quest in all_quests:
        kb.add(InlineKeyboardButton(text=f'{quest[3]}] {quest[1]}', callback_data=f'delete_quest:{quest[0]}'))
    return kb.as_markup()
