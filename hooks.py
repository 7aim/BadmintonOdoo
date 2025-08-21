# -*- coding: utf-8 -*-

def post_init_hook(env):
    """Post-installation hook to update database"""
    
    # Check and add badminton_balance column if not exists
    try:
        env.cr.execute("SELECT badminton_balance FROM res_partner LIMIT 1")
    except Exception:
        # Column doesn't exist, add it
        env.cr.execute("ALTER TABLE res_partner ADD COLUMN badminton_balance INTEGER DEFAULT 0")
        env.cr.execute("UPDATE res_partner SET badminton_balance = 0 WHERE badminton_balance IS NULL")
        env.cr.commit()
        print("✅ Badminton balance column added successfully!")

def uninstall_hook(env):
    """Pre-uninstall hook to clean up"""
    try:
        env.cr.execute("ALTER TABLE res_partner DROP COLUMN IF EXISTS badminton_balance")
        env.cr.commit()
        print("✅ Badminton balance column removed successfully!")
    except Exception as e:
        print(f"⚠️ Warning during uninstall: {e}")
