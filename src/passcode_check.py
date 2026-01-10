import sqlite3

def check_passcode(passcode):
    conn = sqlite3.connect("my_database.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        "SELECT company_name FROM passcodes WHERE passcode = ?",
        (passcode,)
    )

    row = cur.fetchone()
    conn.close()

    if row:
        return True, row["company_name"]
    else:
        return False, None

print(check_passcode(123456))