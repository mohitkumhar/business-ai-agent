import psycopg2
import random
from faker import Faker
from datetime import datetime, timedelta
import uuid

fake = Faker()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "localhost"),
    database=os.getenv("DB_NAME", "test_db"),
    user=os.getenv("DB_USER", "admin"),
    password=os.getenv("DB_PASSWORD", "root")
)

cursor = conn.cursor()

# -------------------------------
# HELPER DATA
# -------------------------------
industries = ["Retail", "Food", "Tech", "Healthcare", "Finance"]
risk_levels = ["Low", "Medium", "High"]

revenue_categories = ["Product Sales", "Online Orders", "Subscription", "Services"]
expense_categories = ["Rent", "Salary", "Utilities", "Marketing", "Inventory"]

roles_list = ["Admin", "Manager", "Staff"]

product_names = ["Laptop", "Phone", "Shoes", "Burger", "Medicine", "Software"]

decision_types = ["Marketing", "Hiring", "Pricing", "Expansion"]
alert_types = ["Cash Flow", "Revenue Drop", "High Expense", "Inventory Issue"]

# -------------------------------
# CREATE SINGLE BUSINESS
# -------------------------------
business_id = str(uuid.uuid4())

cursor.execute("""
    INSERT INTO businesses (business_id, business_name, industry_type, owner_name, monthly_target_revenue, risk_appetite)
    VALUES (%s, %s, %s, %s, %s, %s)
""", (
    business_id,
    "Urban Retail Store",
    random.choice(industries),
    fake.name(),
    250000,
    random.choice(risk_levels)
))

conn.commit()

# -------------------------------
# ROLES + USERS
# -------------------------------
role_ids = []

for role in roles_list:
    cursor.execute("""
        INSERT INTO roles (business_id, role_name, description)
        VALUES (%s, %s, %s)
        RETURNING role_id
    """, (business_id, role, f"{role} role"))

    role_id = cursor.fetchone()[0]
    role_ids.append(role_id)

    cursor.execute("""
        INSERT INTO users (business_id, role_id, name, email, password_hash)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        business_id,
        role_id,
        fake.name(),
        fake.unique.email(),
        "hashed_password"
    ))

conn.commit()

# -------------------------------
# PRODUCTS
# -------------------------------
for _ in range(8):
    cost = random.randint(100, 1000)
    sell = cost + random.randint(50, 500)

    cursor.execute("""
        INSERT INTO products (business_id, product_name, cost_price, selling_price, stock_quantity)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        business_id,
        random.choice(product_names),
        cost,
        sell,
        random.randint(10, 200)
    ))

conn.commit()

# -------------------------------
# EMPLOYEES
# -------------------------------
for _ in range(8):
    cursor.execute("""
        INSERT INTO employees (business_id, name, role, salary, status)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        business_id,
        fake.name(),
        random.choice(["Sales", "Manager", "Support"]),
        random.randint(20000, 80000),
        random.choice(["Active", "Left"])
    ))

conn.commit()

# -------------------------------
# DAILY TRANSACTIONS (3 MONTHS)
# -------------------------------
start_date = datetime.now() - timedelta(days=90)

for day in range(90):
    current_date = start_date + timedelta(days=day)

    entries = random.randint(30, 50)

    for _ in range(entries):
        is_revenue = random.choice([True, False])

        if is_revenue:
            category = random.choice(revenue_categories)
            amount = round(random.uniform(500, 5000), 2)
            t_type = "Revenue"
        else:
            category = random.choice(expense_categories)
            amount = round(random.uniform(200, 3000), 2)
            t_type = "Expense"

        cursor.execute("""
            INSERT INTO daily_transactions (business_id, transaction_date, type, category, amount, description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            business_id,
            current_date.date(),
            t_type,
            category,
            amount,
            fake.sentence()
        ))

conn.commit()

# -------------------------------
# FINANCIAL RECORDS (MONTHLY)
# -------------------------------
for i in range(3):
    month_date = datetime.now() - timedelta(days=30*i)

    revenue = random.randint(150000, 500000)
    expenses = random.randint(80000, 300000)

    cursor.execute("""
        INSERT INTO financial_records (business_id, month, year, total_revenue, total_expenses, net_profit, cash_balance, loans_due)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        business_id,
        month_date.month,
        month_date.year,
        revenue,
        expenses,
        revenue - expenses,
        random.randint(20000, 100000),
        random.randint(0, 50000)
    ))

conn.commit()

# -------------------------------
# DECISIONS + OUTCOMES
# -------------------------------
decision_ids = []

for _ in range(15):
    cursor.execute("""
        INSERT INTO decisions (business_id, decision_text, decision_type, decision_score, risk_level, success_probability, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING decision_id
    """, (
        business_id,
        fake.sentence(),
        random.choice(decision_types),
        round(random.uniform(1, 10), 2),
        random.choice(risk_levels),
        round(random.uniform(0, 1), 2),
        random.choice(["Approved", "Rejected", "Modified"])
    ))

    decision_ids.append(cursor.fetchone()[0])

for d_id in decision_ids:
    cursor.execute("""
        INSERT INTO decision_outcomes (decision_id, actual_result, profit_impact, notes, evaluated_at)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        d_id,
        random.choice(["Success", "Failure"]),
        random.randint(-5000, 20000),
        fake.sentence(),
        datetime.now()
    ))

conn.commit()

# -------------------------------
# ALERTS
# -------------------------------
for _ in range(25):
    cursor.execute("""
        INSERT INTO alerts (business_id, alert_type, severity, message, status)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        business_id,
        random.choice(alert_types),
        random.choice(["Low", "Medium", "High"]),
        fake.sentence(),
        random.choice(["Active", "Resolved"])
    ))

conn.commit()

# -------------------------------
# HEALTH SCORES
# -------------------------------
for _ in range(15):
    cursor.execute("""
        INSERT INTO business_health_scores 
        (business_id, overall_score, cash_score, profitability_score, growth_score, cost_control_score, risk_score)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        business_id,
        round(random.uniform(1, 10), 2),
        round(random.uniform(1, 10), 2),
        round(random.uniform(1, 10), 2),
        round(random.uniform(1, 10), 2),
        round(random.uniform(1, 10), 2),
        round(random.uniform(1, 10), 2)
    ))

conn.commit()

cursor.close()
conn.close()

print("✅ Single business data inserted successfully!")