from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, PreCheckoutQuery, LabeledPrice, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.state import StatesGroup, State

from database import database
from keyboards.admin import admin_kb, delete_quest_kb
from modules.quest_step_handler import save_quest

admin_router = Router()


class AdminStates(StatesGroup):
    adding_quest = State()


@admin_router.callback_query(F.data == 'add_quest')
async def add_quest(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.adding_quest)
    message_text = ('Отправьте данные квеста, где каждый пункт с новой строки\n'
                    'Название\nОписание\nСложность (словом)\n')
    await callback.message.answer(message_text)


@admin_router.message(F.text, StateFilter(AdminStates.adding_quest))
async def process_new_quest_data(message: Message, state: FSMContext):
    data = message.text.split('\n')
    await state.update_data(quest_name=data[0])
    await state.update_data(quest_desc=data[1])
    await state.update_data(quest_difficulty=data[2])

    await message.answer('Теперь пришлите главное фото')


@admin_router.message(F.photo, StateFilter(AdminStates.adding_quest))
async def process_new_quest_photo(message: Message, state: FSMContext):
    quest_photo_id = message.photo[-1].file_id
    await state.update_data(quest_photo_id=quest_photo_id)

    await message.answer('Теперь пришлите местоположение!')


@admin_router.message(F.location, StateFilter(AdminStates.adding_quest))
async def process_new_quest_location(message: Message, state: FSMContext):
    lat = message.location.latitude
    lon = message.location.longitude
    await state.update_data(quest_location=f'{lat},{lon}')

    await message.answer('Ниже есть xlsx шаблон для каждого шага квеста, пришлите обратно заполненный файл')
    await message.answer_document(document=FSInputFile(path='data/template.xlsx'))


@admin_router.message(F.document, StateFilter(AdminStates.adding_quest))
async def test(message: Message,  state: FSMContext):
    fsm_data = await state.get_data()
    quest_name = fsm_data['quest_name']
    quest_desc = fsm_data['quest_desc']
    quest_difficulty = fsm_data['quest_difficulty']
    quest_photo_id = fsm_data['quest_photo_id']
    quest_location = fsm_data['quest_location']
    await database.add_quest(name=quest_name, description=quest_desc, difficulty=quest_difficulty,
                             photo_id=quest_photo_id, location=quest_location)

    # Нужен id квеста нового из бд
    quest_id = (await database.get_all_quests())[-1][0]  # последний квест | id
    file = await message.bot.download(file=message.document)
    save_quest(file, quest_id)

    await message.answer('Квест добавлен!',
                         reply_markup=admin_kb())
    await state.clear()


@admin_router.callback_query(F.data == 'delete_quest')
async def delete_quest(callback: CallbackQuery):
    all_quests = await database.get_all_quests()
    await callback.message.answer(text='Нажмите на квест для удаления',
                                  reply_markup=delete_quest_kb(all_quests))


@admin_router.callback_query(F.data.startswith('delete_quest:'))
async def delete_quest_db(callback: CallbackQuery):
    quest_id = callback.data.split(':')[1]
    await database.delete_quest(int(quest_id))

    await callback.message.answer('Квест удален!',
                                  reply_markup=admin_kb())

