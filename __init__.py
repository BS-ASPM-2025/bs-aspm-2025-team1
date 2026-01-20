from shared.database import SessionLocal
from models.company import Company
from src.security.passwords import hash_password

# Create a database session
db = SessionLocal()

# Create the demo company if it doesn't exist
existing_company = db.query(Company).filter_by(company_name="Demo Company").first()
if not existing_company:
    demo_company = Company(
        company_name="Demo Company",
        password=hash_password("demo_password123")  # Replace it with your desired password
    )

    # Add and commit to the database
    db.add(demo_company)
    db.commit()
    db.refresh(demo_company)
    print(f"Company created with ID: {demo_company.id}")
else:
    print("Demo company already exists.")

# Close the session
db.close()
