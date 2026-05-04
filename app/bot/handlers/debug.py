import logging

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

router = Router()


@router.message()
async def bot_working_fallback(message: Message, state: FSMContext) -> None:
    logging.info(
        "Debug fallback message handler triggered: user_id=%s chat_id=%s text=%r",
        message.from_user.id if message.from_user else None,
        message.chat.id if message.chat else None,
        message.text,
    )
    try:
        current_state = await state.get_state()
        if current_state:
            logging.info(
                "Clearing stale FSM state in debug fallback: user_id=%s state=%s",
                message.from_user.id if message.from_user else None,
                current_state,
            )
            await state.clear()
    except Exception:
        logging.exception("Failed to inspect/clear FSM state in debug fallback")
    await message.answer("Bot working")
