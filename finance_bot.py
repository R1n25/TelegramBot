from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
import sqlite3
import requests
import logging

# Состояния для разговора
CHOOSING_ACTION, ADDING_INCOME, ADDING_EXPENSE, CALCULATOR = range(4)

def start(update, context):
    keyboard = [
        ['💰 Добавить доход', '💸 Добавить расход'],
        ['📊 Статистика', '💱 Курсы валют'],
        ['🔢 Калькулятор']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text(
        'Привет! Я помогу вести учет финансов.',
        reply_markup=reply_markup
    )
    return CHOOSING_ACTION

def init_db():
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (date TEXT, type TEXT, amount REAL, category TEXT)''')
    conn.commit()
    conn.close()

def get_currency_rates():
    url = "https://api.exchangerate-api.com/v4/latest/USD"
    response = requests.get(url)
    return response.json()['rates']

def calculator(update, context):
    try:
        expression = update.message.text
        result = eval(expression)
        update.message.reply_text(f"Результат: {result}")
    except:
        update.message.reply_text("Ошибка в выражении")

def add_transaction(update, context, trans_type):
    try:
        amount = float(update.message.text)
        conn = sqlite3.connect('finance.db')
        c = conn.cursor()
        c.execute("INSERT INTO transactions VALUES (datetime('now'), ?, ?, ?)",
                 (trans_type, amount, 'general'))
        conn.commit()
        conn.close()
        
        if trans_type == "income":
            update.message.reply_text(f"Доход в размере {amount} добавлен!")
        else:
            update.message.reply_text(f"Расход в размере {amount} добавлен!")
        return CHOOSING_ACTION
    except:
        update.message.reply_text("Пожалуйста, введите корректное число")
        return ADDING_INCOME if trans_type == "income" else ADDING_EXPENSE

def get_statistics(update, context):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    
    c.execute("SELECT SUM(amount) FROM transactions WHERE type='income'")
    total_income = c.fetchone()[0] or 0
    
    c.execute("SELECT SUM(amount) FROM transactions WHERE type='expense'")
    total_expense = c.fetchone()[0] or 0
    
    balance = total_income - total_expense
    
    update.message.reply_text(
        f"📊 Статистика:\n"
        f"Общий доход: {total_income}\n"
        f"Общий расход: {total_expense}\n"
        f"Баланс: {balance}"
    )
