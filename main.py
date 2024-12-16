import asyncio

from aiogram import Bot, Dispatcher
from config_data.config import Config, load_config
from database.database import init_db
from handlers.admin import admin_router
from handlers.users import user_router
from keyboards.admin import admin_kb


async def main():
    config: Config = load_config()

    bot = Bot(token=config.tg_bot.token)
    dp = Dispatcher()
    dp.include_router(admin_router)
    dp.include_routers(user_router)

    await init_db()

    await bot.send_message(chat_id=config.tg_bot.admin_id,
                           text='Панель администратора\n /start — для просмотра бота',
                           reply_markup=admin_kb())
    await dp.start_polling(bot)


asyncio.run(main())
