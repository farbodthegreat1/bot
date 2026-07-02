"""
Keyboard builders — all InlineKeyboardMarkup construction in one place.
"""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import config


def main_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("🛒 خرید رنک",      callback_data="shop")],
        [InlineKeyboardButton("📋 سفارش‌های من",   callback_data="my_orders")],
        [InlineKeyboardButton("ℹ️ راهنما",          callback_data="help")],
    ]
    return InlineKeyboardMarkup(buttons)


def rank_selection_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for key, rank in config.RANKS.items():
        label = f"{rank['emoji']} {rank['label']}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"rank:{key}")])
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)


def duration_keyboard(rank_key: str) -> InlineKeyboardMarkup:
    rank = config.RANKS[rank_key]
    buttons = []
    for i, dur in enumerate(rank["durations"]):
        label = f"{dur['label']}  —  {dur['price']:,} T"
        buttons.append(
            [InlineKeyboardButton(label, callback_data=f"dur:{rank_key}:{i}")]
        )
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="shop")])
    return InlineKeyboardMarkup(buttons)


def confirm_keyboard(rank_key: str, dur_index: int, cp: bool, ca: bool) -> InlineKeyboardMarkup:
    cp_str = "1" if cp else "0"
    ca_str = "1" if ca else "0"
    prefix_label  = f"{'✅' if cp else '➕'} Custom Prefix — 100,000 T"
    ability_label = f"{'✅' if ca else '➕'} Custom Ability — 100,000 T"
    buttons = [
        [InlineKeyboardButton(prefix_label,  callback_data=f"toggle:prefix:{rank_key}:{dur_index}:{cp_str}:{ca_str}")],
        [InlineKeyboardButton(ability_label, callback_data=f"toggle:ability:{rank_key}:{dur_index}:{cp_str}:{ca_str}")],
        [InlineKeyboardButton("✅ تأیید و ادامه", callback_data=f"confirm:{rank_key}:{dur_index}:{cp_str}:{ca_str}")],
        [InlineKeyboardButton("❌ انصراف",         callback_data="cancel_order")],
    ]
    return InlineKeyboardMarkup(buttons)


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ انصراف از سفارش", callback_data="cancel_order")]]
    )


def admin_order_keyboard(order_id: str) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("✅ تأیید و فعال‌سازی", callback_data=f"admin:approve:{order_id}"),
            InlineKeyboardButton("❌ رد سفارش",           callback_data=f"admin:reject:{order_id}"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)


def admin_manage_keyboard(order_id: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("🚫 لغو رنک", callback_data=f"admin:revoke:{order_id}")],
    ]
    return InlineKeyboardMarkup(buttons)


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_main")]]
    )


def my_orders_keyboard(has_pending: bool, order_id: str = None) -> InlineKeyboardMarkup:
    buttons = []
    if has_pending and order_id:
        buttons.append([InlineKeyboardButton("❌ لغو سفارش در انتظار", callback_data=f"cancel_pending:{order_id}")])
    buttons.append([InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)
