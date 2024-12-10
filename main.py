from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from telegram import ReplyKeyboardMarkup, Update
import sqlite3
import requests
import logging
from datetime import datetime
from database import init_db, add_transaction_db, get_statistics_db, get_transactions_history, get_all_transactions_history, export_to_csv
import os
import csv
from datetime import datetime
from telegram.ext import CallbackContext

# В начале файла добавим настройку логирования я не бездарь
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Определяем все состояния
(
    CHOOSING_ACTION,  # 0
    ADDING_INCOME,    # 1
    ADDING_EXPENSE,   # 2
    HISTORY_CHOICE,   # 3
    CALCULATOR_INPUT, # 4
    CONVERTER_INPUT,  # 5
) = range(6)

# Определим клавиатуры
def get_main_keyboard():
    keyboard = [
        ['💰 Добавить доход', '💸 Добавить расход'],
        ['📊 Статистика', '📝 История'],
        ['💱 Конвертер валют', '📈 Курсы валют'],
        ['🔢 Калькулятор']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_cancel_keyboard():
    return ReplyKeyboardMarkup([
        ['❌ Отмена']
    ], resize_keyboard=True)

def start(update, context):
    update.message.reply_text(
        'Привет! Я помогу вести учет финансов.',
        reply_markup=get_main_keyboard()
    )
    return CHOOSING_ACTION

def get_currency_rates(update, context):
    """Показывает текущие курсы основных валют"""
    try:
        # Получаем курсы относительно USD
        response = requests.get("https://api.exchangerate-api.com/v4/latest/USD")
        rates = response.json()['rates']
        
        # Форматируем сообщение с курсами
        message = "📈 Курсы валют:\n\n"
        
        # Основные валюты для отображения
        main_currencies = {
            'USD': '🇺🇸',
            'EUR': '🇪🇺',
            'RUB': '🇷🇺',
            'GBP': '🇬🇧',
            'CNY': '🇨🇳',
            'JPY': '🇯🇵'
        }
        
        # Добавляем курсы в ��ообщение
        for currency, flag in main_currencies.items():
            if currency in rates:
                rate = rates[currency]
                message += f"{flag} {currency}: {rate:.2f}\n"
        
        update.message.reply_text(message)
        
    except Exception as e:
        logger.error(f"Ошибка при получении курсов валют: {e}")
        update.message.reply_text("❌ Не удалось получить курсы валют")
    
    keyboard = get_main_keyboard()
    update.message.reply_text('Выберите действие:', reply_markup=keyboard)
    return CHOOSING_ACTION

def calculator(update, context):
    try:
        expression = update.message.text
        # Заменяем умножение и деление на безопасные операторы
        expression = expression.replace('х', '*').replace('х', '*').replace('÷', '/')
        # Проверяем, что в выражении только цифры и операторы
        if not all(c in '0123456789+-/*() ' for c in expression):
            raise ValueError("Недопустимые символы")
            
        result = eval(expression)
        update.message.reply_text(f"Результат: {result}")
        
        # Возвращаем клавиа��уру с главным меню
        update.message.reply_text('Выберите действие:', reply_markup=get_main_keyboard())
        
    except Exception as e:
        logging.error(f"Ошибка в калькуляторе: {e}")
        update.message.reply_text("Ошибка в выражении. Используйте только числа и операторы +, -, *, /")
    
    return CHOOSING_ACTION

def add_transaction(update, context, trans_type):
    try:
        amount_text = update.message.text.strip().replace(',', '.')
        
        if not amount_text.replace('.', '').isdigit():
            raise ValueError("Не число")
            
        amount = float(amount_text)
        
        if amount <= 0:
            raise ValueError("Отрицательное число")
            
        user_id = update.effective_user.id
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Добавим отладочный вывод
        logger.info(f"Попытка добавить транзакцию: дата={current_date}, тип={trans_type}, сумма={amount}, user_id={user_id}")
        
        success = add_transaction_db(current_date, trans_type, amount, user_id)
        
        if success:
            logger.info("Транза��ция успешно добавлена в БД")
            if trans_type == "income":
                update.message.reply_text(f"✅ Доход в размере {amount:.2f} успешно добавлен!")
            else:
                update.message.reply_text(f"✅ Расход в размере {amount:.2f} успешно добавлен!")
        else:
            raise Exception("Ошибка при сохранении в БД")
        
        keyboard = get_main_keyboard()
        update.message.reply_text('Выберите действие:', reply_markup=keyboard)
        return CHOOSING_ACTION
        
    except ValueError as e:
        logger.error(f"Ошибка валидации: {e}")
        update.message.reply_text("❌ Пожалуйста, введите корректное положительное число")
        return ADDING_INCOME if trans_type == "income" else ADDING_EXPENSE
    except Exception as e:
        logger.error(f"Ошибка при добавлении транзакции: {e}")
        update.message.reply_text("❌ Произошла ошибка при добавлении транзакции")
        return ADDING_INCOME if trans_type == "income" else ADDING_EXPENSE

def calculator_start(update, context):
    update.message.reply_text(
        "🔢 Введите математическое выражение\n"
        "Например: 2 + 2 * 2\n"
        "Доступные операции: +, -, *, /"
    )
    return CALCULATOR_INPUT

def income_start(update, context):
    update.message.reply_text(
        "Введите сумму дохода:",
        reply_markup=get_cancel_keyboard()
    )
    return ADDING_INCOME

def expense_start(update, context):
    update.message.reply_text(
        "Введите сумму расхода:",
        reply_markup=get_cancel_keyboard()
    )
    return ADDING_EXPENSE

def cancel(update, context):
    """Отменяет текущее действие и возвращает в главное меню"""
    keyboard = get_main_keyboard()
    update.message.reply_text(
        'Действие отменено. Выберите новое действие:',
        reply_markup=keyboard
    )
    return CHOOSING_ACTION

# Функции для конвертера
def converter_start(update, context):
    update.message.reply_text(
        "💱 Введите сумму и валюты для конвертации\n"
        "Формат: 100 USD TO RUB\n"
        "Доступные валюты: USD, EUR, RUB, GBP и другие"
    )
    return CONVERTER_INPUT

def handle_converter(update, context):
    try:
        text = update.message.text.strip().upper()
        
        # Проверяем формат ввода (например: 100 USD TO RUB)
        parts = text.split()
        if len(parts) != 4 or parts[2] != 'TO':
            raise ValueError("Неверный формат")
            
        amount = float(parts[0])
        from_currency = parts[1]
        to_currency = parts[3]
        
        # Получаем курсы валют
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
        response = requests.get(url)
        rates = response.json()['rates']
        
        if to_currency not in rates:
            raise ValueError("Валюта не найдена")
            
        # Конвертируем
        result = amount * rates[to_currency]
        
        update.message.reply_text(
            f"💱 Результат конвертации:\n"
            f"{amount:.2f} {from_currency} = {result:.2f} {to_currency}"
        )
        
    except ValueError as e:
        update.message.reply_text(
            "❌ Ошибка в формате ввода.\n"
            "Используйте формат: 100 USD TO RUB"
        )
    except Exception as e:
        logger.error(f"Ошибка конвертера: {e}")
        update.message.reply_text("❌ Произошла ошибка при конвертации")
    
    # Возвращаемся к главному меню
    keyboard = get_main_keyboard()
    update.message.reply_text('Выберите действие:', reply_markup=keyboard)
    return CHOOSING_ACTION

def get_statistics(update, context):
    user_id = update.effective_user.id
    total_income, total_expense = get_statistics_db(user_id)
    balance = total_income - total_expense
    
    update.message.reply_text(
        f"📊 Статистика:\n"
        f"Общий доход: {total_income:.2f}\n"
        f"Общий расход: {total_expense:.2f}\n"
        f"Баланс: {balance:.2f}",
        reply_markup=get_main_keyboard()
    )
    
    return CHOOSING_ACTION

def show_history_menu(update, context):
    """Показывает меню истории операций"""
    keyboard = [
        ['📋 Последние операции'],
        ['📚 Вся история'],
        ['📥 Экспорт в CSV'],
        ['❌ Отмена']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text('Выберите тип истории:', reply_markup=reply_markup)
    return HISTORY_CHOICE

def get_recent_history(update, context):
    """Показывает последние операции"""
    user_id = update.effective_user.id
    transactions = get_transactions_history(user_id, limit=10)
    
    if not transactions:
        update.message.reply_text("📋 История операций пуста")
    else:
        message = "📋 Последние операции:\n\n"
        total_income = 0
        total_expense = 0
        
        for date, type_, amount in transactions:
            if type_ == "Доход":
                emoji = "💰"
                total_income += amount
            else:
                emoji = "💸"
                total_expense += amount
                
            message += f"{emoji} {date}\n"
            message += f"Тип: {type_}\n"
            message += f"Сумма: {amount:,.2f} ₽\n"
            message += "─────────────\n"
        
        # Добавляем итоги
        message += "\n📊 Итого за период:\n"
        message += f"Доходы: {total_income:,.2f} ₽\n"
        message += f"Расходы: {total_expense:,.2f} ₽\n"
        message += f"Баланс: {(total_income - total_expense):,.2f} ₽"
        
        update.message.reply_text(message)
    
    keyboard = get_main_keyboard()
    update.message.reply_text('Выберите действие:', reply_markup=keyboard)
    return CHOOSING_ACTION

def get_full_history(update, context):
    """Показывает полную историю операций"""
    user_id = update.effective_user.id
    transactions = get_all_transactions_history(user_id)
    
    if not transactions:
        update.message.reply_text("📚 История операций пуста")
    else:
        message = "📚 Вся история операций:\n\n"
        for date, type_, amount in transactions:
            emoji = "💰" if type_ == "income" else "💸"
            type_text = "Доход" if type_ == "income" else "Расход"
            message += f"{emoji} {type_text}: {amount:.2f} руб. ({date})\n"
        
        # Если сообщение слишком длинное, разбиваем его на части
        if len(message) > 4000:
            parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
            for part in parts:
                update.message.reply_text(part)
        else:
            update.message.reply_text(message)
    
    keyboard = get_main_keyboard()
    update.message.reply_text('Выберите действие:', reply_markup=keyboard)
    return CHOOSING_ACTION

def export_history(update, context):
    """Экспортирует историю в CSV файл"""
    user_id = update.effective_user.id
    
    try:
        file_path = export_to_csv(user_id)
        if file_path:
            with open(file_path, 'rb') as file:
                update.message.reply_document(
                    document=file,
                    filename='finance_history.csv',
                    caption='📥 Ваша история операций'
                )
        else:
            update.message.reply_text("❌ История операций пуста")
    except Exception as e:
        logger.error(f"Ошибка при экспорте в CSV: {e}")
        update.message.reply_text("❌ Произошла ошибка при экспорте")
    
    keyboard = get_main_keyboard()
    update.message.reply_text('Выберите действие:', reply_markup=keyboard)
    return CHOOSING_ACTION

def handle_calculator(update, context):
    try:
        # Получаем выражение и удаляем пробелы
        expression = update.message.text.strip().replace(' ', '')
        
        # Проверяем на допустимые символы
        allowed = set('0123456789+-*/()')
        if not set(expression).issubset(allowed):
            raise ValueError("Недопустимые символы")
        
        # Безопасное вычисление
        def safe_eval(expr):
            # Компилируем выражение в режиме 'eval'
            code = compile(expr, '<string>', 'eval')
            
            # Проверяем, что в выражении только арифметические операции
            for name in code.co_names:
                if name not in {'abs', 'min', 'max'}:
                    raise NameError(f'Использование {name} запрещено')
            
            return eval(code)
        
        result = safe_eval(expression)
        
        # Форматируем результат
        if isinstance(result, (int, float)):
            if float(result).is_integer():
                formatted_result = str(int(result))
            else:
                formatted_result = f"{result:.2f}"
            
            update.message.reply_text(f"🔢 {expression} = {formatted_result}")
        else:
            raise ValueError("Некорректный результат")
            
    except (ValueError, SyntaxError, ZeroDivisionError, NameError):
        update.message.reply_text(
            "❌ Ошибка в выражении.\n"
            "Используйте только цифры и операторы +, -, *, /, (, )\n"
            "Например: 2+2*2"
        )
    except Exception as e:
        logger.error(f"Ошибка калькулятора: {str(e)}")
        update.message.reply_text("❌ Произошла ошибка при вычислении")
    
    keyboard = get_main_keyboard()
    update.message.reply_text('Выберите действие:', reply_markup=keyboard)
    return CHOOSING_ACTION

def main():
    # Инициализируем базу данных
    init_db()
    
    # Замените YOUR_BOT_TOKEN на ваш реальный токен
    # Например: "5555555555:AAHHHHzzzzzzzzzzzzzzzzzzzzzzzzzzz"
    updater = Updater("7303692897:AAH1-fxOntNfwZJiRiQ4b72ABlXTy_80y_0", use_context=True)
    
    # Получаем dispatcher для регистрации обработчиков
    dp = updater.dispatcher
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_ACTION: [
                MessageHandler(Filters.regex('^💰 Добавить доход$'), income_start),
                MessageHandler(Filters.regex('^💸 Добавить расход$'), expense_start),
                MessageHandler(Filters.regex('^📊 Статистика$'), get_statistics),
                MessageHandler(Filters.regex('^📝 История$'), show_history_menu),
                MessageHandler(Filters.regex('^💱 Конвертер валют$'), converter_start),
                MessageHandler(Filters.regex('^📈 Курсы валют$'), get_currency_rates),
                MessageHandler(Filters.regex('^🔢 Калькулятор$'), calculator_start),
                MessageHandler(Filters.regex('^❌ Отмена$'), cancel),
            ],
            ADDING_INCOME: [
                MessageHandler(Filters.regex('^❌ Отмена$'), cancel),
                MessageHandler(Filters.text & ~Filters.command, lambda update, context: add_transaction(update, context, "income")),
            ],
            ADDING_EXPENSE: [
                MessageHandler(Filters.regex('^❌ Отмена$'), cancel),
                MessageHandler(Filters.text & ~Filters.command, lambda update, context: add_transaction(update, context, "expense")),
            ],
            HISTORY_CHOICE: [
                MessageHandler(Filters.regex('^📋 Последние операции$'), get_recent_history),
                MessageHandler(Filters.regex('^📚 Вся история$'), get_full_history),
                MessageHandler(Filters.regex('^📥 Экспорт в CSV$'), export_history),
                MessageHandler(Filters.regex('^❌ Отмена$'), cancel),
            ],
            CALCULATOR_INPUT: [
                MessageHandler(Filters.regex('^❌ Отмена$'), cancel),
                MessageHandler(Filters.text & ~Filters.command, handle_calculator),
            ],
            CONVERTER_INPUT: [
                MessageHandler(Filters.regex('^❌ Отмена$'), cancel),
                MessageHandler(Filters.text & ~Filters.command, handle_converter),
            ],
        },
        fallbacks=[CommandHandler('start', start)]
    )

    dp.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
