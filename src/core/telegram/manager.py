"""Менеджер Telegram ботов."""

import asyncio
import logging
from typing import Any

import redis.asyncio as redis
from aiogram import Bot, Dispatcher, Router
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command, CommandStart
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiohttp import web

from .config import BotMode, TelegramBotConfig, TelegramBotsConfig
from .decorators import get_command_registry
from .templates import get_template_manager

logger = logging.getLogger(__name__)


class TelegramBotInstance:
    """Экземпляр Telegram бота."""

    def __init__(self, config: TelegramBotConfig, global_config: TelegramBotsConfig):
        self.config = config
        self.global_config = global_config
        self.bot: Bot | None = None
        self.dispatcher: Dispatcher | None = None
        self.router: Router | None = None
        self.storage: RedisStorage | None = None
        self._polling_task: asyncio.Task | None = None

    async def initialize(self) -> None:
        """Инициализация бота."""
        try:
            # Создаем сессию с настройками
            session = AiohttpSession()

            # Создаем бота
            self.bot = Bot(token=self.config.token, session=session, parse_mode=self.config.parse_mode)

            # Создаем хранилище для FSM (если включено)
            if self.config.fsm_enabled and self.global_config.TELEGRAM_REDIS_HOST:
                redis_client = redis.Redis(
                    host=self.global_config.TELEGRAM_REDIS_HOST,
                    port=self.global_config.TELEGRAM_REDIS_PORT,
                    db=self.global_config.TELEGRAM_REDIS_DB,
                    password=self.global_config.TELEGRAM_REDIS_PASSWORD,
                )
                self.storage = RedisStorage(redis_client)

            # Создаем диспетчер
            self.dispatcher = Dispatcher(storage=self.storage)

            # Создаем роутер
            self.router = Router()
            self.dispatcher.include_router(self.router)

            # Регистрируем обработчики
            await self._register_handlers()

            # Устанавливаем команды бота
            await self._set_bot_commands()

            logger.info(f"Бот {self.config.name} инициализирован")

        except Exception as e:
            logger.error(f"Ошибка инициализации бота {self.config.name}: {e}")
            raise

    async def _register_handlers(self) -> None:
        """Регистрация обработчиков команд и сообщений."""
        registry = get_command_registry()

        # Регистрируем команды
        for cmd, cmd_info in registry.commands.items():
            if self.router is None:
                continue
            if cmd == "start":
                self.router.message.register(cmd_info["handler"], CommandStart())
            else:
                self.router.message.register(cmd_info["handler"], Command(commands=[cmd]))

        # Регистрируем обработчики сообщений
        for handler_info in registry.message_handlers:
            # Добавляем фильтры по типам контента
            filters: list[Any] = []
            if handler_info["content_types"]:
                # В aiogram 3.x фильтры по типам контента встроены
                pass

            if self.router is not None:
                self.router.message.register(handler_info["handler"], *filters)

        # Регистрируем callback обработчики
        for handler_info in registry.callback_handlers:
            callback_filters: list[Any] = []
            if handler_info["callback_data"]:
                # Добавляем фильтр по callback_data
                # Простой фильтр по строке
                callback_filters.append(lambda c: c.data == handler_info["callback_data"])

            if self.router is not None:
                self.router.callback_query.register(handler_info["handler"], *callback_filters)

        # Регистрируем middleware
        for middleware_handler in registry.middleware_handlers:
            if self.dispatcher is not None:
                self.dispatcher.message.middleware(middleware_handler)
                self.dispatcher.callback_query.middleware(middleware_handler)

    async def _set_bot_commands(self) -> None:
        """Установка команд бота в меню."""
        registry = get_command_registry()
        commands_info = registry.get_commands_info()

        # Создаем объекты команд для API
        bot_commands = [
            BotCommand(command=cmd_info["command"].replace("/", ""), description=cmd_info["description"])
            for cmd_info in commands_info
            if not cmd_info["command"].startswith("/start")  # start не добавляем в меню
        ]

        if bot_commands and self.bot is not None:
            await self.bot.set_my_commands(bot_commands)
            logger.info(f"Установлено {len(bot_commands)} команд для бота {self.config.name}")

    async def start_polling(self) -> None:
        """Запуск бота в режиме polling."""
        if self.config.mode != BotMode.POLLING:
            raise ValueError(f"Бот {self.config.name} не настроен для polling")

        if self._polling_task and not self._polling_task.done():
            logger.warning(f"Polling для бота {self.config.name} уже запущен")
            return

        logger.info(f"Запуск polling для бота {self.config.name}")

        try:
            if self.bot is None or self.dispatcher is None:
                raise ValueError(f"Бот {self.config.name} не инициализирован")

            # Пропускаем накопившиеся обновления если нужно
            if self.config.drop_pending_updates:
                await self.bot.delete_webhook(drop_pending_updates=True)

            # Запускаем polling
            self._polling_task = asyncio.create_task(
                self.dispatcher.start_polling(
                    self.bot,
                    polling_timeout=self.config.polling_timeout,
                    request_timeout=self.config.request_timeout,
                    allowed_updates=self.config.polling_allowed_updates,
                )
            )

            logger.info(f"Polling для бота {self.config.name} запущен")

        except Exception as e:
            logger.error(f"Ошибка запуска polling для бота {self.config.name}: {e}")
            raise

    async def stop_polling(self) -> None:
        """Остановка polling."""
        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
            logger.info(f"Polling для бота {self.config.name} остановлен")

    async def set_webhook(self, webhook_url: str) -> None:
        """Установка webhook."""
        if self.config.mode != BotMode.WEBHOOK:
            raise ValueError(f"Бот {self.config.name} не настроен для webhook")

        if self.bot is None:
            raise ValueError(f"Бот {self.config.name} не инициализирован")

        try:
            await self.bot.set_webhook(
                url=webhook_url,
                secret_token=self.config.webhook_secret,
                drop_pending_updates=self.config.drop_pending_updates,
            )
            logger.info(f"Webhook установлен для бота {self.config.name}: {webhook_url}")

        except Exception as e:
            logger.error(f"Ошибка установки webhook для бота {self.config.name}: {e}")
            raise

    async def delete_webhook(self) -> None:
        """Удаление webhook."""
        if self.bot is None:
            raise ValueError(f"Бот {self.config.name} не инициализирован")

        try:
            await self.bot.delete_webhook(drop_pending_updates=True)
            logger.info(f"Webhook удален для бота {self.config.name}")

        except Exception as e:
            logger.error(f"Ошибка удаления webhook для бота {self.config.name}: {e}")

    async def close(self) -> None:
        """Закрытие бота."""
        # Останавливаем polling если запущен
        await self.stop_polling()

        # Закрываем сессию бота
        if self.bot:
            await self.bot.session.close()

        # Закрываем хранилище
        if self.storage:
            await self.storage.close()

        logger.info(f"Бот {self.config.name} закрыт")


class TelegramBotManager:
    """Менеджер для управления несколькими Telegram ботами."""

    def __init__(self, config: TelegramBotsConfig | None = None):
        self.config = config or TelegramBotsConfig()
        self.bots: dict[str, TelegramBotInstance] = {}
        self.webhook_app: web.Application | None = None
        self._webhook_runner: web.AppRunner | None = None

        # Настраиваем логирование
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Настройка логирования для ботов."""
        level = getattr(logging, self.config.TELEGRAM_LOG_LEVEL.upper(), logging.INFO)

        # Настраиваем логгер для aiogram
        aiogram_logger = logging.getLogger("aiogram")
        aiogram_logger.setLevel(level)

        # Настраиваем логгер для telegram модуля
        telegram_logger = logging.getLogger("telegram")
        telegram_logger.setLevel(level)

    async def initialize_bots(self) -> None:
        """Инициализация всех ботов."""
        if not self.config.TELEGRAM_BOTS_ENABLED:
            logger.info("Telegram боты отключены в конфигурации")
            return

        enabled_bots = self.config.get_enabled_bots()
        if not enabled_bots:
            logger.warning("Не найдено конфигураций для ботов")
            return

        # Инициализируем менеджер шаблонов и создаем шаблоны по умолчанию
        template_manager = get_template_manager()
        template_manager.create_default_templates()

        for bot_name, bot_config in enabled_bots.items():
            try:
                bot_instance = TelegramBotInstance(bot_config, self.config)
                await bot_instance.initialize()
                self.bots[bot_name] = bot_instance
                logger.info(f"Бот {bot_name} добавлен в менеджер")

            except Exception as e:
                logger.error(f"Ошибка инициализации бота {bot_name}: {e}")

        logger.info(f"Инициализировано {len(self.bots)} ботов")

    async def start_polling_bots(self) -> None:
        """Запуск всех ботов в режиме polling."""
        polling_bots = [bot for bot in self.bots.values() if bot.config.mode == BotMode.POLLING]

        if not polling_bots:
            logger.info("Нет ботов для запуска в режиме polling")
            return

        # Запускаем все боты параллельно
        tasks = [bot.start_polling() for bot in polling_bots]
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(f"Запущено {len(polling_bots)} ботов в режиме polling")

    async def setup_webhooks(self) -> None:
        """Настройка webhook для всех ботов."""
        webhook_bots = [bot for bot in self.bots.values() if bot.config.mode == BotMode.WEBHOOK]

        if not webhook_bots:
            logger.info("Нет ботов для настройки webhook")
            return

        # Создаем веб-приложение для webhook
        self.webhook_app = web.Application()

        # Настраиваем обработчики для каждого бота
        for bot in webhook_bots:
            if not bot.config.webhook_path:
                logger.warning(f"Не указан webhook_path для бота {bot.config.name}")
                continue

            # Создаем обработчик запросов
            if bot.dispatcher is not None and bot.bot is not None:
                handler = SimpleRequestHandler(
                    dispatcher=bot.dispatcher, bot=bot.bot, secret_token=bot.config.webhook_secret
                )
            else:
                logger.warning(f"Бот {bot.config.name} не инициализирован для webhook")
                continue

            # Регистрируем путь
            self.webhook_app.router.add_post(bot.config.webhook_path, handler.handle)

            # Устанавливаем webhook
            if bot.config.webhook_url:
                webhook_url = f"{bot.config.webhook_url}{bot.config.webhook_path}"
                await bot.set_webhook(webhook_url)

        logger.info(f"Настроено {len(webhook_bots)} webhook ботов")

    async def start_webhook_server(self) -> None:
        """Запуск веб-сервера для webhook."""
        if not self.webhook_app:
            logger.info("Нет webhook приложения для запуска")
            return

        self._webhook_runner = web.AppRunner(self.webhook_app)
        await self._webhook_runner.setup()

        site = web.TCPSite(
            self._webhook_runner, host=self.config.TELEGRAM_WEBHOOK_HOST, port=self.config.TELEGRAM_WEBHOOK_PORT
        )

        await site.start()
        logger.info(
            f"Webhook сервер запущен на {self.config.TELEGRAM_WEBHOOK_HOST}:{self.config.TELEGRAM_WEBHOOK_PORT}"
        )

    async def stop_webhook_server(self) -> None:
        """Остановка веб-сервера для webhook."""
        if self._webhook_runner:
            await self._webhook_runner.cleanup()
            logger.info("Webhook сервер остановлен")

    async def stop_all_bots(self) -> None:
        """Остановка всех ботов."""
        if not self.bots:
            return

        # Останавливаем всех ботов параллельно
        tasks = [bot.close() for bot in self.bots.values()]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Останавливаем webhook сервер
        await self.stop_webhook_server()

        logger.info("Все боты остановлены")

    def get_bot(self, bot_name: str) -> TelegramBotInstance | None:
        """Получить экземпляр бота по имени."""
        return self.bots.get(bot_name)

    def get_bot_by_token(self, token: str) -> TelegramBotInstance | None:
        """Получить экземпляр бота по токену."""
        for bot in self.bots.values():
            if bot.config.token == token:
                return bot
        return None

    async def send_message_to_all_admins(self, message: str, parse_mode: str = "HTML") -> None:
        """Отправить сообщение всем администраторам через всех ботов."""
        if not self.config.TELEGRAM_ADMIN_USERS:
            return

        for admin_id in self.config.TELEGRAM_ADMIN_USERS:
            for bot in self.bots.values():
                if bot.bot is None:
                    continue
                try:
                    await bot.bot.send_message(chat_id=admin_id, text=message, parse_mode=parse_mode)
                except Exception as e:
                    logger.error(f"Ошибка отправки сообщения админу {admin_id} через бота {bot.config.name}: {e}")


# Глобальный менеджер ботов
_bot_manager: TelegramBotManager | None = None


def get_bot_manager() -> TelegramBotManager:
    """Получить глобальный менеджер ботов."""
    global _bot_manager
    if _bot_manager is None:
        _bot_manager = TelegramBotManager()
    return _bot_manager
