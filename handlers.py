"""
All Telegram handler functions.
"""

from __future__ import annotations

import json
import logging
import re

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import config
import database as db
import keyboards as kb
import rcon

logger = logging.getLogger(__name__)

S_IDLE              = "idle"
S_AWAIT_IGN         = "await_ign"
S_AWAIT_RECEIPT     = "await_receipt"
S_AWAIT_PREFIX_DESC = "await_prefix_desc"
S_AWAIT_ABILITY_DESC= "await_ability_desc"

CUSTOM_PRICE = 100_000


def _is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


def _fmt_price(price: int) -> str:
    return f"{price:,} T"


def _rank_summary(rank_key: str, dur_index: int) -> str:
    rank = config.RANKS[rank_key]
    dur  = rank["durations"][dur_index]
    return (
        f"{rank['emoji']} *{rank['label']}* — {dur['label']}\n"
        f"💰 قیمت: *{_fmt_price(dur['price'])}*"
    )


def _order_summary(draft: dict) -> str:
    rank_key  = draft["rank_key"]
    dur_index = draft["dur_index"]
    rank = config.RANKS[rank_key]
    dur  = rank["durations"][dur_index]
    base_price = dur["price"]
    extras = []
    extra_price = 0
    if draft.get("custom_prefix"):
        extras.append(f"✅ 🎨 Custom Prefix — {_fmt_price(CUSTOM_PRICE)}")
        extra_price += CUSTOM_PRICE
    if draft.get("custom_ability"):
        extras.append(f"✅ ⚡ Custom Ability — {_fmt_price(CUSTOM_PRICE)}")
        extra_price += CUSTOM_PRICE
    total = base_price + extra_price
    text = (
        f"{rank['emoji']} *{rank['label']}* — {dur['label']}\n"
        f"💰 قیمت رنک: *{_fmt_price(base_price)}*"
    )
    if extras:
        text += "\n" + "\n".join(extras)
    text += f"\n\n💳 *مجموع: {_fmt_price(total)}*"
    return text


async def _send_main_menu(update: Update, text: str) -> None:
    msg = update.effective_message
    if update.callback_query:
        await msg.edit_text(
            text, reply_markup=kb.main_menu_keyboard(), parse_mode=ParseMode.MARKDOWN
        )
    else:
        await msg.reply_text(
            text, reply_markup=kb.main_menu_keyboard(), parse_mode=ParseMode.MARKDOWN
        )


# ── /start ────────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db.clear_user_state(user.id)
    welcome = (
        f"👋 سلام *{user.first_name}*!\n\n"
        "🏪 به فروشگاه رسمی رنک سرور *TCC* خوش آمدی!\n\n"
        "از منوی زیر رنک مورد نظرت رو انتخاب کن 👇"
    )
    await _send_main_menu(update, welcome)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📖 *راهنمای خرید رنک*\n\n"
        "1️⃣ روی *خرید رنک* بزن\n"
        "2️⃣ رنک و مدت زمان رو انتخاب کن\n"
        "3️⃣ افزودنی‌های دلخواه رو انتخاب کن\n"
        "4️⃣ نام کاربری ماینکرافتت رو بنویس\n"
        "5️⃣ پرداخت رو انجام بده و رسید بفرست\n"
        "6️⃣ ادمین بررسی می‌کنه و رنک فعال میشه ✅\n\n"
        "_برای خرید با @Goodvilen یا @DigiWinner12 در ارتباط باش._"
    )
    await update.effective_message.reply_text(
        text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back_to_menu_keyboard()
    )


# ── Shop callbacks ────────────────────────────────────────────────────────────

async def cb_shop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🛒 *انتخاب رنک*\n\nرنک مورد نظرت رو انتخاب کن:",
        reply_markup=kb.rank_selection_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )


async def cb_rank_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, rank_key = query.data.split(":", 1)

    if rank_key not in config.RANKS:
        await query.answer("رنک پیدا نشد.", show_alert=True)
        return

    rank = config.RANKS[rank_key]
    text = f"{rank['emoji']} *رنک {rank['label']}*\n\nمدت زمان رو انتخاب کن:"
    await query.edit_message_text(
        text,
        reply_markup=kb.duration_keyboard(rank_key),
        parse_mode=ParseMode.MARKDOWN,
    )


async def cb_duration_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, rank_key, dur_str = query.data.split(":")
    dur_index = int(dur_str)

    if rank_key not in config.RANKS:
        await query.answer("رنک پیدا نشد.", show_alert=True)
        return

    draft = {"rank_key": rank_key, "dur_index": dur_index, "custom_prefix": False, "custom_ability": False}
    text = (
        "🧾 *خلاصه سفارش*\n\n"
        f"{_order_summary(draft)}\n\n"
        "➕ *افزودنی‌های اختیاری* (هر کدام ۱۰۰٬۰۰۰ T):\n"
        "🎨 Custom Prefix\n"
        "⚡ Custom Ability\n\n"
        "آیا تأیید می‌کنی؟"
    )
    await query.edit_message_text(
        text,
        reply_markup=kb.confirm_keyboard(rank_key, dur_index, False, False),
        parse_mode=ParseMode.MARKDOWN,
    )


async def cb_toggle_extra(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    # toggle:prefix:rank_key:dur_index:cp:ca
    _, extra_type, rank_key, dur_str, cp_str, ca_str = parts
    dur_index = int(dur_str)
    cp = cp_str == "1"
    ca = ca_str == "1"

    if extra_type == "prefix":
        cp = not cp
    elif extra_type == "ability":
        ca = not ca

    draft = {"rank_key": rank_key, "dur_index": dur_index, "custom_prefix": cp, "custom_ability": ca}
    text = (
        "🧾 *خلاصه سفارش*\n\n"
        f"{_order_summary(draft)}\n\n"
        "➕ *افزودنی‌های اختیاری* (هر کدام ۱۰۰٬۰۰۰ T):\n"
        f"{'✅' if cp else '🎨'} Custom Prefix\n"
        f"{'✅' if ca else '⚡'} Custom Ability\n\n"
        "آیا تأیید می‌کنی؟"
    )
    await query.edit_message_text(
        text,
        reply_markup=kb.confirm_keyboard(rank_key, dur_index, cp, ca),
        parse_mode=ParseMode.MARKDOWN,
    )


async def cb_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    parts = query.data.split(":")
    # confirm:rank_key:dur_index:cp:ca
    _, rank_key, dur_str, cp_str, ca_str = parts
    dur_index = int(dur_str)
    cp = cp_str == "1"
    ca = ca_str == "1"

    if db.has_pending_order(user.id):
        await query.edit_message_text(
            "⚠️ شما یک سفارش *در انتظار بررسی* دارید.\n\n"
            "لطفاً منتظر بمانید تا ادمین سفارش قبلی را بررسی کند.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.back_to_menu_keyboard(),
        )
        return

    draft = {
        "rank_key": rank_key,
        "dur_index": dur_index,
        "custom_prefix": cp,
        "custom_ability": ca,
        "prefix_desc": None,
        "ability_desc": None,
    }

    if cp:
        db.set_user_state(user.id, S_AWAIT_PREFIX_DESC, json.dumps(draft))
        await query.edit_message_text(
            "🎨 *Custom Prefix*\n\nپرفیکس مورد نظر خود را توضیح دهید:\n"
            "_مثال: [VIP] با رنگ طلایی_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.cancel_keyboard(),
        )
    elif ca:
        db.set_user_state(user.id, S_AWAIT_ABILITY_DESC, json.dumps(draft))
        await query.edit_message_text(
            "⚡ *Custom Ability*\n\nقابلیت مورد نظر خود را توضیح دهید:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.cancel_keyboard(),
        )
    else:
        db.set_user_state(user.id, S_AWAIT_IGN, json.dumps(draft))
        await query.edit_message_text(
            "✏️ *مرحله ۱ از ۲ — نام کاربری ماینکرافت*\n\n"
            "لطفاً نام کاربری دقیق خود در ماینکرافت (IGN) را بنویسید:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.cancel_keyboard(),
        )


async def cb_cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    db.clear_user_state(update.effective_user.id)
    await query.edit_message_text(
        "❌ سفارش لغو شد.\n\nهر زمان خواستی می‌تونی دوباره خرید کنی!",
        reply_markup=kb.back_to_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )


async def cb_back_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    db.clear_user_state(update.effective_user.id)
    await _send_main_menu(update, "🏠 *منوی اصلی*\n\nچه کاری می‌تونم برات انجام بدم؟")


async def cb_my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    pending = db.get_pending_order(user.id)
    if pending:
        text = (
            "📋 *سفارش‌های من*\n\n"
            f"🔄 *سفارش در انتظار بررسی:*\n"
            f"📦 شماره سفارش: `{pending['id']}`\n"
            f"🏅 رنک: *{pending['rank_label']}* — {pending['duration']}\n"
            f"🎮 IGN: `{pending['ign']}`\n\n"
            "_ادمین سفارش شما را بررسی می‌کند._"
        )
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.my_orders_keyboard(True, pending["id"]),
        )
    else:
        await query.edit_message_text(
            "📋 *سفارش‌های من*\n\n"
            "هیچ سفارش فعالی ندارید.\n\n"
            "برای پیگیری با ادمین در ارتباط باش:\n"
            "👤 @Goodvilen\n"
            "👤 @DigiWinner12",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.my_orders_keyboard(False),
        )


async def cb_cancel_pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    _, order_id = query.data.split(":", 1)
    order = db.get_order(order_id)
    if not order or order["user_id"] != user.id:
        await query.answer("سفارش پیدا نشد.", show_alert=True)
        return
    if order["status"] != db.STATUS_PENDING:
        await query.answer("این سفارش دیگر در انتظار بررسی نیست.", show_alert=True)
        return
    db.update_order_status(order_id, db.STATUS_REJECTED)
    await query.edit_message_text(
        "❌ *سفارش شما لغو شد.*\n\nهر زمان خواستی می‌تونی دوباره خرید کنی!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.back_to_menu_keyboard(),
    )


async def cb_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = (
        "📖 *راهنمای خرید رنک*\n\n"
        "1️⃣ روی *خرید رنک* بزن\n"
        "2️⃣ رنک و مدت زمان رو انتخاب کن\n"
        "3️⃣ افزودنی‌های دلخواه رو انتخاب کن\n"
        "4️⃣ نام کاربری ماینکرافتت رو بنویس\n"
        "5️⃣ پرداخت رو انجام بده و رسید بفرست\n"
        "6️⃣ ادمین بررسی می‌کنه و رنک فعال میشه ✅\n\n"
        "_برای خرید با @Goodvilen یا @DigiWinner12 در ارتباط باش._"
    )
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.back_to_menu_keyboard(),
    )


# ── Message FSM ───────────────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user    = update.effective_user
    message = update.effective_message
    state, data_json = db.get_user_state(user.id)

    if state == S_AWAIT_PREFIX_DESC:
        desc = message.text.strip() if message.text else None
        if not desc:
            await message.reply_text(
                "⚠️ لطفاً توضیحات پرفیکس را به صورت متن بنویس.",
                reply_markup=kb.cancel_keyboard(),
            )
            return
        draft = json.loads(data_json)
        draft["prefix_desc"] = desc
        if draft.get("custom_ability"):
            db.set_user_state(user.id, S_AWAIT_ABILITY_DESC, json.dumps(draft))
            await message.reply_text(
                f"✅ پرفیکس ثبت شد: `{desc}`\n\n"
                "⚡ *Custom Ability*\n\nقابلیت مورد نظر خود را توضیح دهید:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.cancel_keyboard(),
            )
        else:
            db.set_user_state(user.id, S_AWAIT_IGN, json.dumps(draft))
            await message.reply_text(
                f"✅ پرفیکس ثبت شد: `{desc}`\n\n"
                "✏️ *نام کاربری ماینکرافت*\n\nلطفاً IGN خود را بنویسید:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.cancel_keyboard(),
            )
        return

    if state == S_AWAIT_ABILITY_DESC:
        desc = message.text.strip() if message.text else None
        if not desc:
            await message.reply_text(
                "⚠️ لطفاً توضیحات قابلیت را به صورت متن بنویس.",
                reply_markup=kb.cancel_keyboard(),
            )
            return
        draft = json.loads(data_json)
        draft["ability_desc"] = desc
        db.set_user_state(user.id, S_AWAIT_IGN, json.dumps(draft))
        await message.reply_text(
            f"✅ قابلیت ثبت شد: `{desc}`\n\n"
            "✏️ *نام کاربری ماینکرافت*\n\nلطفاً IGN خود را بنویسید:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.cancel_keyboard(),
        )
        return

    if state == S_AWAIT_IGN:
        ign = message.text.strip() if message.text else None
        if not ign:
            await message.reply_text(
                "⚠️ لطفاً نام کاربری ماینکرافتت رو به صورت متن بنویس.",
                reply_markup=kb.cancel_keyboard(),
            )
            return

        if not re.fullmatch(r"[A-Za-z0-9_]{3,16}", ign):
            await message.reply_text(
                "⚠️ این نام کاربری معتبر نیست.\n"
                "نام کاربری ماینکرافت باید ۳ تا ۱۶ کاراکتر و فقط شامل حروف انگلیسی، عدد و آندرلاین باشد.",
                reply_markup=kb.cancel_keyboard(),
            )
            return

        draft = json.loads(data_json)
        draft["ign"] = ign
        db.set_user_state(user.id, S_AWAIT_RECEIPT, json.dumps(draft))

        rank_key  = draft["rank_key"]
        dur_index = draft["dur_index"]

        await message.reply_text(
            f"✅ نام کاربری ثبت شد: `{ign}`\n\n"
            f"{_order_summary(draft)}\n\n"
            f"{config.PAYMENT_INFO}\n\n"
            "📸 *مرحله آخر* — بعد از پرداخت، *تصویر رسید* را اینجا ارسال کنید.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.cancel_keyboard(),
        )
        return

    if state == S_AWAIT_RECEIPT:
        if not message.photo:
            await message.reply_text(
                "⚠️ لطفاً *تصویر* رسید پرداخت را ارسال کنید.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.cancel_keyboard(),
            )
            return

        draft      = json.loads(data_json)
        rank_key   = draft["rank_key"]
        dur_index  = draft["dur_index"]
        ign        = draft["ign"]
        rank       = config.RANKS[rank_key]
        dur        = rank["durations"][dur_index]
        file_id    = message.photo[-1].file_id
        cp         = draft.get("custom_prefix", False)
        ca         = draft.get("custom_ability", False)
        prefix_desc  = draft.get("prefix_desc")
        ability_desc = draft.get("ability_desc")
        extra_price  = (CUSTOM_PRICE if cp else 0) + (CUSTOM_PRICE if ca else 0)
        total_price  = dur["price"] + extra_price

        order_id = db.create_order(
            user_id=user.id,
            username=user.username,
            ign=ign,
            rank_key=rank_key,
            rank_label=rank["label"],
            duration=dur["label"],
            months=dur["months"],
            price=total_price,
            receipt_file_id=file_id,
            custom_prefix=cp,
            custom_ability=ca,
            prefix_desc=prefix_desc,
            ability_desc=ability_desc,
        )
        db.clear_user_state(user.id)

        await message.reply_text(
            f"🎉 *سفارش شما ثبت شد!*\n\n"
            f"📦 شماره سفارش: `{order_id}`\n"
            f"{_order_summary(draft)}\n"
            f"👤 IGN: `{ign}`\n\n"
            "_ادمین سفارش شما را بررسی می‌کند و به زودی نتیجه اعلام می‌شود._",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.back_to_menu_keyboard(),
        )

        await _notify_admins(context, order_id, user, ign, rank, dur, file_id, cp, ca, prefix_desc, ability_desc, total_price)
        return

    # idle
    await message.reply_text(
        "از منوی زیر شروع کن 👇",
        reply_markup=kb.main_menu_keyboard(),
    )


async def _notify_admins(context, order_id, user, ign, rank, dur, file_id, cp, ca, prefix_desc, ability_desc, total_price) -> None:
    username_str = f"@{user.username}" if user.username else f"ID: {user.id}"
    extras = ""
    if cp:
        extras += f"\n🎨 Custom Prefix: `{prefix_desc}`"
    if ca:
        extras += f"\n⚡ Custom Ability: `{ability_desc}`"
    caption = (
        f"🔔 *سفارش جدید — #{order_id}*\n\n"
        f"👤 کاربر: {username_str} (`{user.id}`)\n"
        f"🎮 IGN: `{ign}`\n"
        f"{rank['emoji']} رنک: *{rank['label']}* — {dur['label']}\n"
        f"💰 مجموع: *{total_price:,} T*"
        f"{extras}"
    )
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=file_id,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.admin_order_keyboard(order_id),
            )
        except Exception as e:
            logger.error("Could not notify admin %s: %s", admin_id, e)


# ── Admin callbacks ───────────────────────────────────────────────────────────

async def cb_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user  = update.effective_user

    if not _is_admin(user.id):
        await query.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    parts = query.data.split(":")
    action   = parts[1]
    order_id = parts[2]
    order = db.get_order(order_id)

    if not order:
        await query.answer("سفارش پیدا نشد.", show_alert=True)
        return

    if action == "revoke":
        await _admin_revoke(query, order_id, order, context)
        return

    if order["status"] != db.STATUS_PENDING:
        await query.answer(f"این سفارش قبلاً {order['status']} شده.", show_alert=True)
        return

    if action == "approve":
        await _admin_approve(query, order_id, order, context)
    elif action == "reject":
        await _admin_reject(query, order_id, order, context)


async def _admin_approve(query, order_id: str, order, context) -> None:
    lp_group = config.RANKS[order["rank_key"]]["luckperms_group"]
    try:
        response = rcon.grant_rank(order["ign"], lp_group)
        db.update_order_status(order_id, db.STATUS_APPROVED)

        await query.edit_message_caption(
            caption=(
                f"✅ *تأیید شد — #{order_id}*\n\n"
                f"🎮 IGN: `{order['ign']}`\n"
                f"🏅 رنک: *{order['rank_label']}* — {order['duration']}\n\n"
                f"_RCON: {response or 'دستور ارسال شد'}_"
            ),
            parse_mode="Markdown",
            reply_markup=kb.admin_manage_keyboard(order_id),
        )
        await query.answer("✅ رنک با موفقیت فعال شد!")

        await context.bot.send_message(
            chat_id=order["user_id"],
            text=(
                f"🎉 *رنک شما فعال شد!*\n\n"
                f"🏅 رنک: *{order['rank_label']}* — {order['duration']}\n"
                f"🎮 IGN: `{order['ign']}`\n\n"
                "وارد سرور بشو و از رنکت لذت ببر! 🚀\n"
                "آدرس سرور: *TCC*"
            ),
            parse_mode="Markdown",
            reply_markup=kb.back_to_menu_keyboard(),
        )

    except rcon.RCONError as exc:
        logger.error("RCON error: %s", exc)
        await query.answer(
            f"⚠️ خطا در RCON: {exc}\nرنک فعال نشد!", show_alert=True
        )


async def _admin_reject(query, order_id: str, order, context) -> None:
    db.update_order_status(order_id, db.STATUS_REJECTED)

    await query.edit_message_caption(
        caption=(
            f"❌ *رد شد — #{order_id}*\n\n"
            f"🎮 IGN: `{order['ign']}`\n"
            f"🏅 رنک: *{order['rank_label']}* — {order['duration']}"
        ),
        parse_mode="Markdown",
    )
    await query.answer("❌ سفارش رد شد.")

    await context.bot.send_message(
        chat_id=order["user_id"],
        text=(
            f"❌ *سفارش #{order_id} رد شد.*\n\n"
            "ممکن است رسید پرداخت تأیید نشده باشد.\n"
            "برای پیگیری با ادمین در ارتباط باش:\n"
            "👤 @Goodvilen\n"
            "👤 @DigiWinner12"
        ),
        parse_mode="Markdown",
        reply_markup=kb.back_to_menu_keyboard(),
    )


async def _admin_revoke(query, order_id: str, order, context) -> None:
    lp_group = config.RANKS[order["rank_key"]]["luckperms_group"]
    try:
        rcon.revoke_rank(order["ign"], lp_group)
        db.update_order_status(order_id, db.STATUS_REJECTED)
        await query.edit_message_caption(
            caption=(
                f"🚫 *رنک لغو شد — #{order_id}*\n\n"
                f"🎮 IGN: `{order['ign']}`\n"
                f"🏅 رنک: *{order['rank_label']}* — {order['duration']}"
            ),
            parse_mode="Markdown",
        )
        await query.answer("🚫 رنک لغو شد.")
        await context.bot.send_message(
            chat_id=order["user_id"],
            text=(
                f"🚫 *رنک شما لغو شد — #{order_id}*\n\n"
                "برای اطلاعات بیشتر با ادمین در ارتباط باش:\n"
                "👤 @Goodvilen\n"
                "👤 @DigiWinner12"
            ),
            parse_mode="Markdown",
            reply_markup=kb.back_to_menu_keyboard(),
        )
    except rcon.RCONError as exc:
        logger.error("RCON error: %s", exc)
        await query.answer(f"⚠️ خطا در RCON: {exc}", show_alert=True)


# ── Error handler ─────────────────────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled exception:", exc_info=context.error)
