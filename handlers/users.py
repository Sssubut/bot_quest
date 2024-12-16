import asyncio
import os
import random
import uuid
from qreader import QReader
import cv2

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, PreCheckoutQuery, LabeledPrice, CallbackQuery
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.state import StatesGroup, State
from geopy.distance import geodesic

from config_data.config import Config, load_config
from database import database
from keyboards.users import menu_kb, sub_kb, quests_kb, quest_info_kb, hint_kb
from modules.quest_step_handler import load_quest

user_router = Router()
config: Config = load_config()


class States(StatesGroup):
    main_menu = State()  # Обработка "Ближайший квест"
    in_quest = State()


@user_router.message(CommandStart())
@user_router.message(F.text == 'Главное меню')
async def start_menu(message: Message, state: FSMContext):
    await state.clear()

    profile = await database.user_profile(message.from_user.id)
    await message.answer(text=f'Вы попали в бота квесты-экскурсии по городам, {message.from_user.first_name}',
                         reply_markup=menu_kb(is_premium=profile[2]))
    await state.set_state(States.main_menu)  # Для обработки ближайшего квеста по гео


# Ближайшие квесты
@user_router.message(F.location, StateFilter(States.main_menu))
async def find_nearest_quest(message: Message, state: FSMContext):
    lat = message.location.latitude
    lon = message.location.longitude
    kb = await quests_kb(lat, lon)
    await message.answer(text='Ближайшие квесты', reply_markup=kb)


@user_router.message(F.text == 'Все квесты')
async def all_quests(message: Message):
    kb = await quests_kb()
    await message.answer(text='Все квесты', reply_markup=kb)


@user_router.message(F.text == 'Случайный квест')
async def random_quest(message: Message, state: FSMContext):
    all_quests = await database.get_all_quests()
    quest = random.choice(all_quests)

    message_text = f'Квест: {quest[1]}\nОписание: {quest[2]}\nСложность: {quest[3]}'
    await message.answer_photo(
        photo=quest[4],
        caption=message_text,
        reply_markup=quest_info_kb(quest[0]))


@user_router.callback_query(F.data.startswith('quest:'))
async def quest_view_details(callback: CallbackQuery, state: FSMContext):
    quest_id = int(callback.data.split(':')[1])

    quest = await database.get_quest(quest_id)
    message_text = f'Квест: {quest[1]}\nОписание: {quest[2]}\nСложность: {quest[3]}'
    await callback.message.answer_photo(
        photo=quest[4],
        caption=message_text,
        reply_markup=quest_info_kb(quest_id))


@user_router.callback_query(F.data.startswith('start_quest:'))
async def start_quest(callback: CallbackQuery, state: FSMContext):
    try:
        await database.process_user_quest(callback.from_user.id)
    except Exception:
        await callback.message.answer(
            text='У вас закончились бесплатные квесты! Вам необходимо купить подписку для продолжения!',
            reply_markup=sub_kb())
        return

    await state.set_state(States.in_quest)

    quest_id = int(callback.data.split(':')[1])
    await state.update_data(quest_id=quest_id)

    quest: list = load_quest(quest_id)
    await state.update_data(quest=quest)
    await state.update_data(current_step=0)
    await state.update_data(total_steps=len(quest))

    await process_quest_steps(callback.message, state)


async def process_quest_steps(message: Message, state: FSMContext):
    user_data = await state.get_data()
    quest_steps = user_data.get('quest')
    quest_id = user_data.get('quest_id')
    current_step = user_data.get('current_step')
    total_steps = user_data.get('total_steps')

    if current_step == total_steps:
        await message.answer('Вы закончили квест!')
        return

    task_text = quest_steps[current_step][0]
    photo_link = quest_steps[current_step][1]
    hint = quest_steps[current_step][2]
    task_type = quest_steps[current_step][3]
    task_answer = quest_steps[current_step][4]

    await state.update_data(task_type=task_type)
    await state.update_data(task_answer=task_answer)

    kb = hint_kb(quest_id=quest_id, step=current_step) if hint else None

    if photo_link:
        msg = await message.answer_photo(
            photo=photo_link,
            caption=task_text,
            reply_markup=kb
        )
    else:
        msg = await message.answer(
            text=task_text,
            reply_markup=kb
        )
    await state.update_data(last_bot_message_id=msg.message_id)  # Чтобы потом удалять


# Обработка ответов на квеста
@user_router.message(F.text, StateFilter(States.in_quest))
async def handle_quest_answer(message: Message, state: FSMContext):
    user_data = await state.get_data()
    task_type = user_data.get('task_type')
    task_answer = user_data.get('task_answer')

    current_step = user_data.get('current_step')
    if message.text.lower() == task_answer.lower() and task_type == 'question':
        await message.delete()
        msg = await message.answer('Верно!')
        await asyncio.sleep(1)
        await msg.delete()
        await message.bot.delete_message(chat_id=message.from_user.id,
                                         message_id=user_data.get('last_bot_message_id'))
        await state.update_data(current_step=current_step + 1)

        await process_quest_steps(message, state)  # Идем дальше
    else:
        await message.delete()
        msg = await message.answer('Неправильный ответ!')
        await asyncio.sleep(1)
        await msg.delete()


# Обработка qr-кодов внутри квеста
@user_router.message(F.photo, StateFilter(States.in_quest))
async def handle_quest_photo(message: Message, state: FSMContext):
    user_data = await state.get_data()
    current_step = user_data.get('current_step')
    task_answer = user_data.get('task_answer')

    await message.bot.download(
        message.photo[-1],
        destination='temp_image.jpg'
    )

    qreader = QReader()
    image = cv2.cvtColor(cv2.imread("temp_image.jpg"), cv2.COLOR_BGR2RGB)
    decoded_text = (qreader.detect_and_decode(image=image))[0]
    os.remove('temp_image.jpg')

    if task_answer == decoded_text:
        await message.delete()
        msg = await message.answer('Верно!')
        await asyncio.sleep(1)
        await msg.delete()
        await message.bot.delete_message(chat_id=message.from_user.id,
                                         message_id=user_data.get('last_bot_message_id'))
        await state.update_data(current_step=current_step + 1)

        await process_quest_steps(message, state)  # Идем дальше
    else:
        await message.delete()
        msg = await message.answer('Возможно qr-код плохо читаем, сделайте еще одно фото.')
        await asyncio.sleep(3)
        await msg.delete()


# Обработка локации внутри квеста
@user_router.message(F.location, StateFilter(States.in_quest))
async def handle_quest_location(message: Message, state: FSMContext):
    user_data = await state.get_data()
    task_answer = user_data.get('task_answer')
    current_step = user_data.get('current_step')

    lat, lon = task_answer.split(',')
    distance = geodesic((message.location.latitude, message.location.longitude), (lat, lon)).kilometers
    if distance < 1:  # Гео верное
        await message.delete()
        msg = await message.answer('Верно!')
        await asyncio.sleep(1)
        await msg.delete()
        await message.bot.delete_message(chat_id=message.from_user.id,
                                         message_id=user_data.get('last_bot_message_id'))
        await state.update_data(current_step=current_step + 1)

        await process_quest_steps(message, state)  # Идем дальше
    else:
        await message.delete()
        msg = await message.answer('Похоже, что вы находитесь слишком далеко от нужного места!')
        await asyncio.sleep(3)
        await msg.delete()


@user_router.callback_query(F.data.startswith('hint'))
async def show_hint(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    quest_id = user_data.get('quest_id')
    current_step = user_data.get('current_step')

    quest_data = load_quest(quest_id)
    hint = quest_data[current_step][2]
    await callback.answer(text=hint, show_alert=True)


@user_router.message(F.text == 'Личный кабинет')
async def user_info(message: Message):
    profile = await database.user_profile(message.from_user.id)
    is_premium = bool(profile[2])
    message_text = f'Информация о пользователе:\nusername: @{message.from_user.username}\nОсталось бесплатных квестов: '
    message_text += 'неограничено' if is_premium else f'{profile[1]}'

    kb = None if is_premium else sub_kb()
    await message.answer(text=message_text, reply_markup=kb)


@user_router.message(F.text == 'Купить неограниченный доступ')
async def buy_sub(message: Message):
    payment_id = str(uuid.uuid4())  # Идентификатор для платежа
    await message.answer_invoice(
        title='Подписка на безлимитные квесты',
        description='Бот Романа Мусина',
        payload=payment_id,
        provider_token=config.payment_token,
        currency='RUB',
        prices=[LabeledPrice(label='Оплата услуг', amount=99999)])
    await message.answer(text='Номер тест-карты: 4000 0000 0000 0408, остальные данные на рандом')


@user_router.pre_checkout_query()
async def process_pre_checkout_query(query: PreCheckoutQuery):
    await query.bot.answer_pre_checkout_query(pre_checkout_query_id=query.id, ok=True)


@user_router.message(F.successful_payment)
async def success_payment_handler(message: Message):
    await database.set_premium(message.from_user.id)
    await message.answer(text='Теперь у вас неограниченный доступ к квестам!')


@user_router.message(F.text == 'Помощь и поддержка')
async def help(message: Message):
    await message.answer(text='Если у вас возникли какие-либо проблемы, напишите мне в телеграм @wsxsss')
