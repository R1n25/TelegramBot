import sqlite3
import logging
import csv
from datetime import datetime

# Настраиваем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def init_db():
    try:
        conn = sqlite3.connect('finance.db')
        c = conn.cursor()
        
        # Создаем таблицу, если она не существует
        c.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT,
                user_id INTEGER NOT NULL
            )
        ''')
        
        # Сохраняем изменения
        conn.commit()
        conn.close()
        
        logger.info("База данных успешно инициализирована")
        return True
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        if conn:
            conn.close()
        return False

def add_transaction_db(date, trans_type, amount, user_id, category=None):
    conn = None
    try:
        logger.info(f"Подключение к БД для добавления транзакции...")
        conn = sqlite3.connect('finance.db')
        c = conn.cursor()
        
        logger.info(f"Выполнение INSERT запроса: date={date}, type={trans_type}, amount={amount}, user_id={user_id}")
        c.execute("""
            INSERT INTO transactions (date, type, amount, user_id, category) 
            VALUES (?, ?, ?, ?, ?)
        """, (date, trans_type, amount, user_id, category))
        
        conn.commit()
        logger.info("Транзакция успешно добавлена, изменения сохранены")
        
        # Проверим, что данные действительно добавились
        c.execute("SELECT * FROM transactions WHERE date=? AND type=? AND amount=? AND user_id=?", 
                 (date, trans_type, amount, user_id))
        result = c.fetchone()
        logger.info(f"Проверка добавленной записи: {result}")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка при добавлении транзакции в БД: {e}")
        if conn:
            conn.close()
        return False

def get_statistics_db(user_id):
    try:
        conn = sqlite3.connect('finance.db')
        c = conn.cursor()
        
        c.execute("SELECT SUM(amount) FROM transactions WHERE type='income' AND user_id=?", (user_id,))
        total_income = c.fetchone()[0] or 0
        
        c.execute("SELECT SUM(amount) FROM transactions WHERE type='expense' AND user_id=?", (user_id,))
        total_expense = c.fetchone()[0] or 0
        
        conn.close()
        return total_income, total_expense
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        return 0, 0

def get_transactions_history(user_id, limit=10):
    """Получает последние транзакции пользователя"""
    try:
        conn = sqlite3.connect('finance.db')
        c = conn.cursor()
        c.execute("""
            SELECT 
                strftime('%d.%m.%Y %H:%M', datetime(date)) as formatted_date,
                CASE 
                    WHEN type = 'income' THEN 'Доход'
                    WHEN type = 'expense' THEN 'Расход'
                END as type,
                amount 
            FROM transactions 
            WHERE user_id = ? 
            ORDER BY date DESC LIMIT ?
        """, (user_id, limit))
        return c.fetchall()
    except Exception as e:
        logger.error(f"Ошибка при получении истории: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_all_transactions_history(user_id):
    """Получает все транзакции пользователя"""
    try:
        conn = sqlite3.connect('finance.db')
        c = conn.cursor()
        c.execute("""
            SELECT date, type, amount FROM transactions 
            WHERE user_id = ? 
            ORDER BY date DESC
        """, (user_id,))
        return c.fetchall()
    except Exception as e:
        logger.error(f"Ошибка при получении полной истории: {e}")
        return []
    finally:
        if conn:
            conn.close()

def export_to_csv(user_id):
    """Экспортирует историю в CSV файл"""
    try:
        conn = sqlite3.connect('finance.db')
        c = conn.cursor()
        
        # Получаем данные с форматированной датой и русскими названиями
        c.execute("""
            SELECT 
                strftime('%d.%m.%Y %H:%M', datetime(date)) as formatted_date,
                CASE 
                    WHEN type = 'income' THEN 'Доход'
                    WHEN type = 'expense' THEN 'Расход'
                END as type,
                amount,
                CASE 
                    WHEN category IS NULL THEN 'Без категории'
                    ELSE category 
                END as category
            FROM transactions 
            WHERE user_id = ? 
            ORDER BY date DESC
        """, (user_id,))
        
        transactions = c.fetchall()
        if not transactions:
            return None
            
        file_path = f'finance_history_{user_id}.csv'
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file, delimiter=';')  # Используем ; для лучшей совместимости с Excel
            writer.writerow(['Дата и время', 'Тип операции', 'Сумма (руб.)', 'Категория'])
            writer.writerows(transactions)
        
        return file_path
        
    except Exception as e:
        logger.error(f"Ошибка при экспорте в CSV: {e}")
        return None
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    init_db()

import sqlite3

conn = sqlite3.connect('finance.db')
c = conn.cursor()
c.execute("SELECT * FROM transactions")
print(c.fetchall())
conn.close()
