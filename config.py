"""
Central configuration for the Minecraft Rank Bot — TCC Server
"""

# ── Telegram ──────────────────────────────────────────────────────────────────
BOT_TOKEN: str = "8318145383:AAF8e1Me5GTeNwiMbXIBVYCIJY5z-pPJ6RA"
ADMIN_IDS: list[int] = [5715055515, 8317211916]

# ── RCON (Minecraft server) ───────────────────────────────────────────────────
RCON_HOST: str = "46.38.138.212"
RCON_PORT: int = 19155
RCON_PASSWORD: str = "NeWgAmE147"

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_PATH: str = "data/orders.db"

# ── Shop catalogue ────────────────────────────────────────────────────────────
RANKS: dict = {
    "amethyst": {
        "label": "Amethyst",
        "emoji": "🟣",
        "luckperms_group": "amethyst",
        "durations": [
            {"label": "1 ماه",   "months": 1,  "price": 100000},
            {"label": "2 ماه",   "months": 2,  "price": 200000},
            {"label": "3 ماه",   "months": 3,  "price": 300000},
            {"label": "1 سال",   "months": 12, "price": 600000},
        ],
    },
    "lunar": {
        "label": "Lunar",
        "emoji": "🔵",
        "luckperms_group": "lunar",
        "durations": [
            {"label": "1 ماه",   "months": 1,  "price": 200000},
            {"label": "2 ماه",   "months": 2,  "price": 300000},
            {"label": "3 ماه",   "months": 3,  "price": 400000},
            {"label": "1 سال",   "months": 12, "price": 750000},
        ],
    },
    "sponsor": {
        "label": "Sponsor",
        "emoji": "💸",
        "luckperms_group": "sponsor",
        "durations": [
            {"label": "1 ماه",   "months": 1,  "price": 500000},
            {"label": "2 ماه",   "months": 2,  "price": 745000},
            {"label": "3 ماه",   "months": 3,  "price": 970000},
            {"label": "1 سال",   "months": 12, "price": 2500000},
        ],
    },
    "mythic": {
        "label": "Mythic",
        "emoji": "⚡️",
        "luckperms_group": "mythic",
        "durations": [
            {"label": "3 ماه",   "months": 3,  "price": 800000},
            {"label": "6 ماه",   "months": 6,  "price": 1000000},
            {"label": "1 سال",   "months": 12, "price": 3400000},
        ],
    },
}

# ── Add-ons ───────────────────────────────────────────────────────────────────
ADDONS = {
    "custom_prefix":  {"label": "پرفیکس دلخواه",     "emoji": "🏷️", "price": 100000},
    "custom_ability": {"label": "قابلیت دلخواه",      "emoji": "✨", "price": 150000},
}

# ── Payment info shown to users ───────────────────────────────────────────────
PAYMENT_INFO: str = (
    "💳 *روش پرداخت*\n\n"
    "برای خرید با ادمین‌های زیر در ارتباط باشید:\n"
    "👤 @Goodvilen\n"
    "👤 @DigiWinner12\n\n"
    "_بعد از پرداخت، تصویر رسید را اینجا ارسال کنید._"
)

ORDER_EXPIRY_SECONDS: int = 0

