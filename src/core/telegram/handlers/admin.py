"""Административные команды Telegram ботов."""

import asyncio
from datetime import datetime

from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from ..decorators import admin_only, command, get_command_registry, rate_limit
from ..manager import get_bot_manager
from ..templates import get_template_manager


@command("admin", description="Панель администратора", admin_only=True)
async def cmd_admin(message: Message):
    """Обработчик команды /admin."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
                InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
            ],
            [
                InlineKeyboardButton(text="🤖 Боты", callback_data="admin_bots"),
                InlineKeyboardButton(text="📋 Шаблоны", callback_data="admin_templates"),
            ],
            [
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings"),
                InlineKeyboardButton(text="🔄 Перезагрузка", callback_data="admin_reload"),
            ],
        ]
    )

    admin_text = f"""🔧 <b>Панель администратора</b>

👤 <b>Администратор:</b> {message.from_user.first_name}
🕐 <b>Время:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Выберите действие:"""

    await message.answer(admin_text, parse_mode="HTML", reply_markup=keyboard)


@command("broadcast", description="Рассылка сообщения", admin_only=True)
@rate_limit(calls=1, period=300)  # Не чаще раза в 5 минут
async def cmd_broadcast(message: Message):
    """Обработчик команды /broadcast."""
    command_text = message.text or ""
    if " " not in command_text:
        await message.answer(
            "📢 <b>Рассылка сообщений</b>\n\n"
            "Использование: <code>/broadcast Ваше сообщение</code>\n"
            "Сообщение будет отправлено всем администраторам.",
            parse_mode="HTML",
        )
        return

    broadcast_text = command_text.split(" ", 1)[1]
    bot_manager = get_bot_manager()

    # Показываем прогресс
    status_message = await message.answer("📡 Отправка сообщений...")

    try:
        await bot_manager.send_message_to_all_admins(
            f"📢 <b>Рассылка от администратора</b>\n\n{broadcast_text}", parse_mode="HTML"
        )

        await status_message.edit_text("✅ Рассылка завершена успешно!")

    except Exception as e:
        await status_message.edit_text(f"❌ Ошибка рассылки: {e!s}")


@command("logs", description="Просмотр логов", admin_only=True)
async def cmd_logs(message: Message):
    """Обработчик команды /logs."""
    try:
        import logging

        # Получаем последние записи из логов
        log_text = "📝 <b>Последние записи логов:</b>\n\n"

        # Здесь можно добавить логику чтения из файла логов
        # Пока что показываем информацию о логгерах

        loggers_info = []
        for name in logging.Logger.manager.loggerDict:
            logger = logging.getLogger(name)
            if logger.handlers:
                loggers_info.append(f"• {name}: {logger.level}")

        if loggers_info:
            log_text += "\n".join(loggers_info[:10])  # Показываем первые 10
        else:
            log_text += "Активные логгеры не найдены"

        await message.answer(log_text, parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ Ошибка получения логов: {e!s}")


@command("restart_bots", description="Перезапуск ботов", admin_only=True)
@rate_limit(calls=1, period=600)  # Не чаще раза в 10 минут
async def cmd_restart_bots(message: Message):
    """Обработчик команды /restart_bots."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_restart"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_restart"),
            ]
        ]
    )

    await message.answer(
        "⚠️ <b>Перезапуск ботов</b>\n\n"
        "Вы уверены, что хотите перезапустить всех ботов?\n"
        "Это может временно прервать их работу.",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@command("create_template", description="Создать шаблон", admin_only=True)
async def cmd_create_template(message: Message):
    """Обработчик команды /create_template."""
    await message.answer(
        "📝 <b>Создание шаблона</b>\n\n"
        "Формат команды:\n"
        "<code>/create_template имя_шаблона|описание|содержимое</code>\n\n"
        "Пример:\n"
        "<code>/create_template hello|Приветствие|Привет, {{name}}!</code>",
        parse_mode="HTML",
    )


@command("delete_template", description="Удалить шаблон", admin_only=True)
async def cmd_delete_template(message: Message):
    """Обработчик команды /delete_template."""
    command_text = message.text or ""
    if " " not in command_text:
        template_manager = get_template_manager()
        templates = template_manager.list_templates()

        if templates:
            template_list = "\n".join([f"• <code>{t}</code>" for t in templates])
            await message.answer(
                f"🗑 <b>Удаление шаблона</b>\n\n"
                f"Доступные шаблоны:\n{template_list}\n\n"
                f"Использование: <code>/delete_template имя_шаблона</code>",
                parse_mode="HTML",
            )
        else:
            await message.answer("📋 Шаблоны не найдены")
        return

    template_name = command_text.split(" ", 1)[1].strip()
    template_manager = get_template_manager()

    if template_manager.remove_template(template_name):
        await message.answer(f"✅ Шаблон <code>{template_name}</code> удален", parse_mode="HTML")
    else:
        await message.answer(f"❌ Шаблон <code>{template_name}</code> не найден", parse_mode="HTML")


# Callback обработчики для админ панели
@admin_only
async def callback_admin_stats(callback: CallbackQuery):
    """Статистика системы."""
    bot_manager = get_bot_manager()
    active_bots = len(bot_manager.bots)

    stats_text = f"""📊 <b>Статистика системы</b>

🤖 <b>Активных ботов:</b> {active_bots}
📋 <b>Зарегистрированных команд:</b> {len(get_command_registry().commands)}
📝 <b>Шаблонов:</b> {len(get_template_manager().list_templates())}
🕐 <b>Время:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"""

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")]]
    )

    await callback.answer()
    if callback.message and isinstance(callback.message, Message):
        await callback.message.edit_text(stats_text, parse_mode="HTML", reply_markup=keyboard)


@admin_only
async def callback_admin_bots(callback: CallbackQuery):
    """Управление ботами."""
    bot_manager = get_bot_manager()

    bots_info = []
    for bot_name, bot_instance in bot_manager.bots.items():
        status = "🟢 Активен" if bot_instance.bot else "🔴 Не активен"
        mode = "📡 Polling" if bot_instance.config.mode.value == "polling" else "🌐 Webhook"
        bots_info.append(f"• <code>{bot_name}</code> - {status} ({mode})")

    bots_text = f"""🤖 <b>Управление ботами</b>

{chr(10).join(bots_info) if bots_info else "Боты не настроены"}"""

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Перезапустить", callback_data="restart_all_bots"),
                InlineKeyboardButton(text="📊 Статус", callback_data="bots_status"),
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")],
        ]
    )

    await callback.answer()
    if callback.message and isinstance(callback.message, Message):
        await callback.message.edit_text(bots_text, parse_mode="HTML", reply_markup=keyboard)


@admin_only
async def callback_admin_templates(callback: CallbackQuery):
    """Управление шаблонами."""
    template_manager = get_template_manager()
    templates = template_manager.list_templates()

    if templates:
        template_list = []
        for template_name in templates[:10]:  # Показываем первые 10
            template = template_manager.get_template(template_name)
            if template:
                desc = (
                    template.description[:30] + "..."
                    if template.description and len(template.description) > 30
                    else (template.description or "Без описания")
                )
                template_list.append(f"• <code>{template_name}</code> - {desc}")

        templates_text = f"""📋 <b>Управление шаблонами</b>

{chr(10).join(template_list)}

Всего шаблонов: {len(templates)}"""
    else:
        templates_text = "📋 <b>Управление шаблонами</b>\n\nШаблоны не найдены"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Создать", callback_data="create_template_dialog"),
                InlineKeyboardButton(text="🔄 Обновить", callback_data="reload_templates"),
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")],
        ]
    )

    await callback.answer()
    await callback.message.edit_text(templates_text, parse_mode="HTML", reply_markup=keyboard)


# Регистрируем callback обработчики
from ..decorators import callback_handler

callback_handler("admin_stats")(callback_admin_stats)
callback_handler("admin_bots")(callback_admin_bots)
callback_handler("admin_templates")(callback_admin_templates)


@callback_handler("back_to_admin")
@admin_only
async def callback_back_to_admin(callback: CallbackQuery):
    """Возврат к главной админ панели."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
                InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
            ],
            [
                InlineKeyboardButton(text="🤖 Боты", callback_data="admin_bots"),
                InlineKeyboardButton(text="📋 Шаблоны", callback_data="admin_templates"),
            ],
            [
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings"),
                InlineKeyboardButton(text="🔄 Перезагрузка", callback_data="admin_reload"),
            ],
        ]
    )

    admin_text = f"""🔧 <b>Панель администратора</b>

👤 <b>Администратор:</b> {callback.from_user.first_name}
🕐 <b>Время:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Выберите действие:"""

    await callback.answer()
    await callback.message.edit_text(admin_text, parse_mode="HTML", reply_markup=keyboard)


@callback_handler("confirm_restart")
@admin_only
async def callback_confirm_restart(callback: CallbackQuery):
    """Подтверждение перезапуска ботов."""
    await callback.answer("🔄 Перезапуск ботов...")

    status_text = "🔄 <b>Перезапуск ботов</b>\n\n"

    try:
        bot_manager = get_bot_manager()

        # Останавливаем ботов
        status_text += "⏹ Остановка ботов...\n"
        await callback.message.edit_text(status_text, parse_mode="HTML")

        await bot_manager.stop_all_bots()

        # Небольшая пауза
        await asyncio.sleep(2)

        # Запускаем заново
        status_text += "▶️ Запуск ботов...\n"
        await callback.message.edit_text(status_text, parse_mode="HTML")

        await bot_manager.initialize_bots()
        await bot_manager.start_polling_bots()

        status_text += "✅ Перезапуск завершен успешно!"
        await callback.message.edit_text(status_text, parse_mode="HTML")

    except Exception as e:
        status_text += f"❌ Ошибка перезапуска: {e!s}"
        await callback.message.edit_text(status_text, parse_mode="HTML")


@callback_handler("cancel_restart")
async def callback_cancel_restart(callback: CallbackQuery):
    """Отмена перезапуска."""
    await callback.answer("❌ Перезапуск отменен")
    await callback.message.edit_text("❌ Перезапуск ботов отменен")


@callback_handler("reload_templates")
@admin_only
async def callback_reload_templates(callback: CallbackQuery):
    """Перезагрузка шаблонов."""
    await callback.answer("🔄 Перезагрузка шаблонов...")

    try:
        template_manager = get_template_manager()
        template_manager._load_templates()

        await callback.answer("✅ Шаблоны перезагружены", show_alert=True)

        # Обновляем список шаблонов
        await callback_admin_templates(callback)

    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e!s}", show_alert=True)


def register_admin_handlers():
    """Регистрация административных обработчиков."""
    # Все обработчики регистрируются автоматически при импорте
    pass
