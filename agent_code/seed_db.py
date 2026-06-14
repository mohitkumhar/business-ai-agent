import psycopg2
import uuid
import random
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://business_ai_user:replace-with-a-local-db-password@db:5432/test_db",
)

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def seed_data():
    conn = get_db_connection()
    cur = conn.cursor()

    print("Cleaning existing data...")
    # Order matters for foreign keys
    cur.execute("TRUNCATE business_health_scores, alerts, daily_transactions, financial_records, products, employees, users, roles, businesses RESTART IDENTITY CASCADE;")

    print("Seeding Businesses...")
    biz_id = "550e8400-e29b-41d4-a716-446655440000"
    biz_name = "Urban Retail Store"
    cur.execute("""
        INSERT INTO businesses (business_id, business_name, industry_type, owner_name, monthly_target_revenue)
        VALUES (%s, %s, %s, %s, %s)
    """, (biz_id, biz_name, "Retail", "Kushal Mahawar", 400000))

    print("Seeding Roles & Users...")
    cur.execute("INSERT INTO roles (business_id, role_name) VALUES (%s, %s) RETURNING role_id", (biz_id, "Owner"))
    role_id = cur.fetchone()[0]
    
    cur.execute("""
        INSERT INTO users (business_id, role_id, name, email, password_hash)
        VALUES (%s, %s, %s, %s, %s)
    """, (biz_id, role_id, "Kushal Mahawar", "kushal@example.com", "hash"))

    print("Seeding Products...")
    products = []
    for i in range(20):
        p_name = f"Product {i+1}"
        price = random.uniform(500, 5000)
        cost = price * random.uniform(0.5, 0.8)
        stock = random.randint(10, 100)
        cur.execute("""
            INSERT INTO products (business_id, product_name, selling_price, cost_price, stock_quantity)
            VALUES (%s, %s, %s, %s, %s) RETURNING product_id
        """, (biz_id, p_name, price, cost, stock))
        products.append(cur.fetchone()[0])

    print("Seeding Employees...")
    statuses = ["Active", "Left"]
    for i in range(10):
        cur.execute("""
            INSERT INTO employees (business_id, name, role, salary, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (biz_id, f"Employee {i+1}", random.choice(["Sales Manager", "Stock Lead", "Clerk"]), random.uniform(15000, 50000), random.choice(statuses)))

    print("Seeding Daily Transactions (Last 30 Days)...")
    tx_types = ["Revenue", "Expense"]
    tx_categories = ["Product Sales", "Inventory", "Marketing", "Payroll", "Rent", "Utilities", "Consulting"]
    
    today = datetime.utcnow().date()
    for d in range(30):
        date = today - timedelta(days=d)
        # Multiple transactions per day
        for _ in range(random.randint(3, 8)):
            tx_type = random.choice(tx_types)
            if tx_type == "Revenue":
                cat = "Product Sales"
                amt = random.uniform(5000, 15000)
                desc = f"Sales from order #{random.randint(1000, 9999)}"
            else:
                cat = random.choice(["Marketing", "Payroll", "Rent", "Utilities", "Consulting"])
                amt = random.uniform(1000, 8000)
                desc = f"Payment for {cat}"
            
            cur.execute("""
                INSERT INTO daily_transactions (business_id, transaction_date, type, category, amount, description)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (biz_id, date, tx_type, cat, amt, desc))

    print("Seeding Financial Records (Last 6 Months)...")
    for m in range(6):
        month_date = today - timedelta(days=m*30)
        year = month_date.year
        month = month_date.month
        rev = random.uniform(250000, 450000)
        exp = random.uniform(150000, 250000)
        cur.execute("""
            INSERT INTO financial_records (business_id, year, month, total_revenue, total_expenses, net_profit, cash_balance)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (biz_id, year, month, rev, exp, rev-exp, random.uniform(500000, 800000)))

    print("Seeding Alerts...")
    severities = ["Low", "Medium", "High"]
    alert_types = ["Cash Flow", "Revenue Drop", "High Expense", "Inventory Issue"]
    for i in range(15):
        cur.execute("""
            INSERT INTO alerts (business_id, severity, alert_type, message, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (biz_id, random.choice(severities), random.choice(alert_types), f"Detected {random.choice(alert_types)} issue for business.", "Active"))


    print("Seeding Health Scores...")
    cur.execute("""
        INSERT INTO business_health_scores (business_id, overall_score, cash_score, profitability_score, growth_score, cost_control_score, risk_score)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (biz_id, 78.5, 82.0, 75.0, 68.0, 84.0, 71.0))

    conn.commit()
    cur.close()
    conn.close()
    print("Database seeded successfully!")

if __name__ == "__main__":
    seed_data()
