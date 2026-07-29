# -*- coding: utf-8 -*-
"""
Telegram Bot - Complete System
Version: 1.0.0
Last Update: 1405/04/22
"""

import asyncio
import logging
import json
import uuid
import re
import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from decimal import Decimal

# Third-party imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
class Config:
    TOKEN = "8883032492:AAGUNmCljCd2AMf8n6hxlo9pUgSaQRpW0MU"
    DATABASE_URL = "sqlite:///bot.db"
    TIMEZONE = "Asia/Tehran"
    
    # Admin Users (Telegram IDs)
    OWNER_IDS = ["8961040480"]
    ADMIN_IDS = ["8961040480"]
    
    # Channel and Group
    CHANNEL_LINK = "https://t.me/+NnHHB5BhE785OTRk"
    GROUP_LINK = "https://t.me/+9-hhQFaMoiAwYjc0"
    SUPPORT_USERNAME = "@XMrHadi"
    
    # Default settings
    DEFAULT_LANGUAGE = "fa"
    DIAMOND_PRICE = 8000
    GIFT_DIAMONDS = 31
    MAINTENANCE_MODE = False
    
    # Premium Plans
    PREMIUM_PLANS = {
        "1_month": {"days": 30, "diamonds": 40, "price": 50000},
        "2_month": {"days": 60, "diamonds": 60, "price": 90000},
        "4_month": {"days": 120, "diamonds": 100, "price": 150000},
        "8_month": {"days": 240, "diamonds": 130, "price": 200000},
        "12_month": {"days": 365, "diamonds": 180, "price": 350000}
    }
    
    # Diamond Packs
    DIAMOND_PACKS = {
        10: 80000,
        25: 180000,
        50: 350000,
        100: 650000,
        250: 1500000,
        500: 2800000
    }
    
    # Bank Card
    BANK_CARD = {
        "number": "6037-9918-1234-5678",
        "owner": "Ali Rezaei",
        "bank": "Melli"
    }
    
    AD_PRICE = 250000
    RATE_LIMIT = {"messages_per_second": 5}

# ==================== DATABASE MODELS ====================
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(50), unique=True, nullable=False, index=True)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    language = Column(String(5), default=Config.DEFAULT_LANGUAGE)
    role = Column(String(20), default='user')
    is_premium = Column(Boolean, default=False)
    premium_expire = Column(DateTime)
    diamonds_balance = Column(Integer, default=0)
    gifted_diamonds = Column(Integer, default=0)
    wallet_balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    transactions = relationship("Transaction", back_populates="user", lazy='dynamic')
    invoices = relationship("Invoice", back_populates="user", lazy='dynamic')
    purchases = relationship("Purchase", back_populates="user", lazy='dynamic')
    ads = relationship("Ad", back_populates="user", lazy='dynamic')
    audit_logs = relationship("AuditLog", back_populates="user", lazy='dynamic')

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey('users.id'))
    type = Column(String(20))
    status = Column(String(20), default='pending')
    amount = Column(Float, default=0)
    diamonds_amount = Column(Integer, default=0)
    description = Column(Text)
    reference_id = Column(String(100))
    balance_before = Column(Float)
    balance_after = Column(Float)
    diamonds_before = Column(Integer)
    diamonds_after = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime)
    
    user = relationship("User", back_populates="transactions")
    audit_logs = relationship("AuditLog", back_populates="transaction", lazy='dynamic')

class Invoice(Base):
    __tablename__ = 'invoices'
    
    id = Column(Integer, primary_key=True)
    invoice_number = Column(String(50), unique=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    amount = Column(Float)
    description = Column(Text)
    sender_card = Column(String(20))
    receipt_image = Column(String(200))
    status = Column(String(20), default='pending')
    verified_by = Column(Integer, ForeignKey('users.id'))
    verified_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    
    user = relationship("User", foreign_keys=[user_id])
    verifier = relationship("User", foreign_keys=[verified_by])

class Purchase(Base):
    __tablename__ = 'purchases'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey('users.id'))
    plan_type = Column(String(20))
    duration_days = Column(Integer)
    diamonds_cost = Column(Integer)
    amount = Column(Float)
    status = Column(String(20), default='completed')
    started_at = Column(DateTime)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    
    user = relationship("User", back_populates="purchases")

class Ad(Base):
    __tablename__ = 'ads'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey('users.id'))
    content = Column(Text)
    media_type = Column(String(20))
    media_id = Column(String(200))
    price = Column(Float)
    status = Column(String(20), default='pending')
    views = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    started_at = Column(DateTime)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    
    user = relationship("User", back_populates="ads")

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey('users.id'))
    transaction_id = Column(Integer, ForeignKey('transactions.id'))
    action = Column(String(100))
    description = Column(Text)
    details = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    
    user = relationship("User", back_populates="audit_logs")
    transaction = relationship("Transaction", back_populates="audit_logs")

class SystemSetting(Base):
    __tablename__ = 'system_settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True)
    value = Column(Text)
    category = Column(String(50))
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

# Create database
engine = create_engine(Config.DATABASE_URL)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# ==================== UTILITY FUNCTIONS ====================
class Utils:
    @staticmethod
    def generate_invoice_number() -> str:
        return f"INV-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    
    @staticmethod
    def format_price(amount: float) -> str:
        return f"{amount:,.0f}".replace(',', '٫')
    
    @staticmethod
    def get_expiry_date(days: int) -> datetime:
        return datetime.now() + timedelta(days=days)
    
    @staticmethod
    def validate_card_number(card: str) -> bool:
        card = re.sub(r'\D', '', card)
        if not card.isdigit() or len(card) != 16:
            return False
        total = 0
        for i, digit in enumerate(reversed(card)):
            n = int(digit)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        return total % 10 == 0
    
    @staticmethod
    def generate_uuid() -> str:
        return str(uuid.uuid4())

# ==================== TRANSLATION SYSTEM ====================
class I18n:
    translations = {
        'fa': {
            'welcome_new': "🎉 به ربات خوش آمدید {name} عزیز!\n\n"
                          "💎 شما {gift} الماس هدیه دریافت کردید.\n"
                          "از منوی زیر استفاده کنید:",
            'welcome_back': "👋 خوش برگشتید {name} عزیز!",
            'profile': "👤 *پروفایل*\n\n"
                      "🆔 شناسه: {id}\n"
                      "👤 نام: {name}\n"
                      "💎 الماس: {diamonds}\n"
                      "⭐ پریمیوم: {premium}\n"
                      "💰 کیف پول: {wallet:,} تومان",
            'diamonds_shop': "💎 *خرید الماس*\n\n"
                           "💰 قیمت: {price:,} تومان\n"
                           "💎 موجودی: {balance}",
            'premium_plans': "⭐ *پریمیوم*\n\n"
                           "📅 {days} روز = {diamonds} 💎\n"
                           "💎 موجودی: {balance}",
            'wallet': "💰 *کیف پول*\n\n"
                     "💎 الماس: {diamonds}\n"
                     "💰 موجودی: {wallet:,} تومان",
            'payment': "💳 *پرداخت*\n\n"
                      "شماره کارت: `{card}`\n"
                      "بانک: {bank}\n"
                      "صاحب حساب: {owner}",
            'maintenance': "🛠 در حال بروزرسانی...",
            'admin_required': "⛔ فقط ادمین",
            'success': "✅ موفق",
            'failed': "❌ ناموفق",
            'help_text': "📚 *راهنما*\n\n"
                        "/start - شروع\n"
                        "/profile - پروفایل\n"
                        "/wallet - کیف پول\n"
                        "/diamonds - الماس\n"
                        "/premium - پریمیوم\n"
                        "/payment - پرداخت\n"
                        "/support - پشتیبانی"
        },
        'en': {
            'welcome_new': "🎉 Welcome {name}!\n\n"
                          "💎 You received {gift} diamonds.",
            'welcome_back': "👋 Welcome back {name}!",
            'profile': "👤 *Profile*\n\n"
                      "🆔 ID: {id}\n"
                      "👤 Name: {name}\n"
                      "💎 Diamonds: {diamonds}\n"
                      "⭐ Premium: {premium}\n"
                      "💰 Wallet: {wallet:,} IRR",
            'diamonds_shop': "💎 *Diamond Shop*\n\n"
                           "💰 Price: {price:,} IRR\n"
                           "💎 Balance: {balance}",
            'premium_plans': "⭐ *Premium*\n\n"
                           "📅 {days} days = {diamonds} 💎\n"
                           "💎 Balance: {balance}",
            'wallet': "💰 *Wallet*\n\n"
                     "💎 Diamonds: {diamonds}\n"
                     "💰 Balance: {wallet:,} IRR",
            'payment': "💳 *Payment*\n\n"
                      "Card: `{card}`\n"
                      "Bank: {bank}\n"
                      "Owner: {owner}",
            'maintenance': "🛠 Under maintenance...",
            'admin_required': "⛔ Admin only",
            'success': "✅ Success",
            'failed': "❌ Failed",
            'help_text': "📚 *Help*\n\n"
                        "/start - Start\n"
                        "/profile - Profile\n"
                        "/wallet - Wallet\n"
                        "/diamonds - Diamonds\n"
                        "/premium - Premium\n"
                        "/payment - Payment\n"
                        "/support - Support"
        }
    }
    
    @staticmethod
    def get_text(key: str, lang: str = 'fa', **kwargs) -> str:
        translations = I18n.translations.get(lang, I18n.translations['fa'])
        text = translations.get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except:
                return text
        return text

# ==================== DATABASE MANAGER ====================
class DBManager:
    @staticmethod
    def get_user(telegram_id: str) -> Optional[User]:
        session = Session()
        try:
            return session.query(User).filter_by(telegram_id=telegram_id).first()
        finally:
            session.close()
    
    @staticmethod
    def create_user(telegram_id: str, username: str = None, 
                   first_name: str = None, last_name: str = None) -> User:
        session = Session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user:
                return user
            
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                diamonds_balance=Config.GIFT_DIAMONDS,
                gifted_diamonds=Config.GIFT_DIAMONDS,
                created_at=datetime.now()
            )
            
            if telegram_id in Config.OWNER_IDS:
                user.role = 'owner'
            
            session.add(user)
            session.commit()
            
            # Log registration
            audit = AuditLog(
                user_id=user.id,
                action='register',
                description='New user registered',
                details={'gifted': Config.GIFT_DIAMONDS}
            )
            session.add(audit)
            session.commit()
            
            return user
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating user: {e}")
            raise
        finally:
            session.close()
    
    @staticmethod
    def update_balance(user_id: int, diamonds: int = 0, wallet: float = 0):
        session = Session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                user.diamonds_balance += diamonds
                user.wallet_balance += wallet
                session.commit()
            return user
        finally:
            session.close()
    
    @staticmethod
    def create_transaction(user_id: int, type: str, amount: float = 0, 
                          diamonds_amount: int = 0, description: str = None,
                          reference_id: str = None) -> Transaction:
        session = Session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            transaction = Transaction(
                user_id=user_id,
                type=type,
                amount=amount,
                diamonds_amount=diamonds_amount,
                description=description,
                reference_id=reference_id,
                balance_before=user.wallet_balance if user else 0,
                diamonds_before=user.diamonds_balance if user else 0
            )
            session.add(transaction)
            session.commit()
            return transaction
        finally:
            session.close()
    
    @staticmethod
    def complete_transaction(transaction_id: int, status: str = 'completed'):
        session = Session()
        try:
            transaction = session.query(Transaction).filter_by(id=transaction_id).first()
            if transaction:
                transaction.status = status
                transaction.completed_at = datetime.now()
                
                if status == 'completed':
                    user = session.query(User).filter_by(id=transaction.user_id).first()
                    if user:
                        if transaction.diamonds_amount:
                            user.diamonds_balance += transaction.diamonds_amount
                        if transaction.amount:
                            user.wallet_balance += transaction.amount
                        transaction.diamonds_after = user.diamonds_balance
                        transaction.balance_after = user.wallet_balance
                
                session.commit()
            return transaction
        finally:
            session.close()

# ==================== MAIN BOT ====================
class Bot:
    def __init__(self, token: str):
        self.token = token
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone(Config.TIMEZONE))
        
        # Conversation states
        self.WAITING_FOR_AMOUNT = 1
        self.WAITING_FOR_CARD = 2
        self.WAITING_FOR_RECEIPT = 3
        self.WAITING_FOR_AD_TEXT = 4
        self.WAITING_FOR_BROADCAST = 5
        
        self.application = ApplicationBuilder().token(token).build()
        self.setup_handlers()
        self.setup_jobs()
        
        logger.info("Bot initialized")
    
    def setup_handlers(self):
        # Commands
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("menu", self.menu))
        self.application.add_handler(CommandHandler("profile", self.profile))
        self.application.add_handler(CommandHandler("wallet", self.wallet))
        self.application.add_handler(CommandHandler("diamonds", self.diamonds))
        self.application.add_handler(CommandHandler("premium", self.premium))
        self.application.add_handler(CommandHandler("payment", self.payment))
        self.application.add_handler(CommandHandler("support", self.support))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("admin", self.admin))
        self.application.add_handler(CommandHandler("stats", self.stats))
        self.application.add_handler(CommandHandler("broadcast", self.broadcast))
        self.application.add_handler(CommandHandler("backup", self.backup))
        self.application.add_handler(CommandHandler("cancel", self.cancel))
        
        # Callback
        self.application.add_handler(CallbackQueryHandler(self.callback))
        
        # Messages
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.photo))
        
        # Error
        self.application.add_error_handler(self.error)
    
    def setup_jobs(self):
        self.scheduler.add_job(
            self.daily_backup,
            CronTrigger(hour=2, minute=0),
            id='daily_backup'
        )
        self.scheduler.add_job(
            self.cleanup_premium,
            CronTrigger(hour=3, minute=0),
            id='cleanup_premium'
        )
        self.scheduler.start()
    
    # ==================== COMMANDS ====================
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        db_user = DBManager.create_user(
            str(user.id), user.username, user.first_name, user.last_name
        )
        
        name = user.first_name or user.username or 'کاربر'
        lang = db_user.language
        
        if db_user.created_at.date() == datetime.now().date():
            text = I18n.get_text('welcome_new', lang, name=name, gift=Config.GIFT_DIAMONDS)
        else:
            text = I18n.get_text('welcome_back', lang, name=name)
        
        keyboard = [
            [InlineKeyboardButton("💎 الماس", callback_data="diamonds"),
             InlineKeyboardButton("⭐ پریمیوم", callback_data="premium")],
            [InlineKeyboardButton("💰 کیف پول", callback_data="wallet"),
             InlineKeyboardButton("👤 پروفایل", callback_data="profile")],
            [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    async def menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await self.get_user(update)
        keyboard = [
            [InlineKeyboardButton("💎 الماس", callback_data="diamonds"),
             InlineKeyboardButton("⭐ پریمیوم", callback_data="premium")],
            [InlineKeyboardButton("💰 کیف پول", callback_data="wallet"),
             InlineKeyboardButton("👤 پروفایل", callback_data="profile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("📋 *منوی اصلی*", reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    async def profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await self.get_user(update)
        lang = user.language
        
        premium = "✅ فعال" if user.is_premium else "❌ غیرفعال"
        if user.is_premium and user.premium_expire:
            premium += f"\n⏳ تا {user.premium_expire.strftime('%Y/%m/%d')}"
        
        text = I18n.get_text('profile', lang,
            id=user.telegram_id,
            name=user.first_name or 'نامشخص',
            diamonds=user.diamonds_balance,
            premium=premium,
            wallet=user.wallet_balance
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await self.get_user(update)
        lang = user.language
        
        text = I18n.get_text('wallet', lang,
            diamonds=user.diamonds_balance,
            wallet=user.wallet_balance
        )
        
        keyboard = [
            [InlineKeyboardButton("💳 شارژ", callback_data="charge"),
             InlineKeyboardButton("🏦 برداشت", callback_data="withdraw")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    async def diamonds(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await self.get_user(update)
        lang = user.language
        
        text = I18n.get_text('diamonds_shop', lang,
            price=Config.DIAMOND_PRICE,
            balance=user.diamonds_balance
        )
        
        keyboard = []
        packs = list(Config.DIAMOND_PACKS.items())
        for i in range(0, len(packs), 2):
            row = []
            for j in range(i, min(i+2, len(packs))):
                amount, price = packs[j]
                row.append(InlineKeyboardButton(
                    f"{amount} 💎 {price:,}تومان",
                    callback_data=f"buy_{amount}"
                ))
            keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    async def premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await self.get_user(update)
        lang = user.language
        
        plans = ""
        for plan, data in Config.PREMIUM_PLANS.items():
            plans += f"• {data['days']} روز = {data['diamonds']} 💎\n"
        
        premium_status = "✅ فعال" if user.is_premium else "❌ غیرفعال"
        if user.is_premium and user.premium_expire:
            premium_status += f"\n⏳ تا {user.premium_expire.strftime('%Y/%m/%d')}"
        
        text = f"⭐ *پریمیوم*\n\n{plans}\n💎 موجودی: {user.diamonds_balance}\nوضعیت: {premium_status}"
        
        keyboard = []
        for plan, data in Config.PREMIUM_PLANS.items():
            keyboard.append([
                InlineKeyboardButton(
                    f"{data['days']} روز ({data['diamonds']}💎)",
                    callback_data=f"premium_{plan}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    async def payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await self.get_user(update)
        lang = user.language
        
        text = I18n.get_text('payment', lang,
            card=Config.BANK_CARD['number'],
            bank=Config.BANK_CARD['bank'],
            owner=Config.BANK_CARD['owner']
        )
        
        keyboard = [
            [InlineKeyboardButton("📋 کپی کارت", callback_data="copy_card")],
            [InlineKeyboardButton("📤 ارسال رسید", callback_data="send_receipt")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    async def support(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = f"📞 *پشتیبانی*\n\n🆔 {Config.SUPPORT_USERNAME}\n👥 {Config.GROUP_LINK}\n📢 {Config.CHANNEL_LINK}"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await self.get_user(update)
        text = I18n.get_text('help_text', user.language)
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        if not await self.is_admin(user_id):
            await update.message.reply_text("⛔ فقط ادمین")
            return
        
        keyboard = [
            [InlineKeyboardButton("👑 کاربران", callback_data="admin_users")],
            [InlineKeyboardButton("✅ تایید پرداخت", callback_data="admin_verify")],
            [InlineKeyboardButton("📢 تبلیغات", callback_data="admin_ads")],
            [InlineKeyboardButton("📊 آمار", callback_data="admin_stats")],
            [InlineKeyboardButton("🛠 حالت نگهداری", callback_data="admin_maintenance")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("👑 *پنل مدیریت*", reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        if not await self.is_admin(user_id):
            return
        
        session = Session()
        try:
            total_users = session.query(User).count()
            premium_users = session.query(User).filter_by(is_premium=True).count()
            total_revenue = session.query(Transaction).filter_by(status='completed').with_entities(
                func.sum(Transaction.amount)
            ).scalar() or 0
            
            text = f"📊 *آمار*\n\n👤 کاربران: {total_users}\n⭐ پریمیوم: {premium_users}\n💰 درآمد: {total_revenue:,.0f} تومان"
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        finally:
            session.close()
    
    async def broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        if not await self.is_admin(user_id):
            return
        
        context.user_data['step'] = self.WAITING_FOR_BROADCAST
        await update.message.reply_text("📢 پیام خود را ارسال کنید:")
    
    async def backup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        if not await self.is_admin(user_id):
            return
        
        try:
            backup_file = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2("bot.db", backup_file)
            with open(backup_file, 'rb') as f:
                await update.message.reply_document(document=f, filename=backup_file)
            os.remove(backup_file)
        except Exception as e:
            await update.message.reply_text(f"❌ خطا: {str(e)}")
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data.clear()
        await update.message.reply_text("✅ لغو شد")
    
    # ==================== CALLBACK ====================
    
    async def callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        data = query.data
        
        # Handle callbacks
        if data == "diamonds":
            await self.diamonds(update, context)
        elif data == "premium":
            await self.premium(update, context)
        elif data == "wallet":
            await self.wallet(update, context)
        elif data == "profile":
            await self.profile(update, context)
        elif data == "support":
            await self.support(update, context)
        elif data == "copy_card":
            await query.edit_message_text(f"✅ کپی شد:\n`{Config.BANK_CARD['number']}`", parse_mode=ParseMode.MARKDOWN)
        elif data == "send_receipt":
            context.user_data['step'] = self.WAITING_FOR_RECEIPT
            await query.edit_message_text("📤 لطفاً رسید را ارسال کنید:")
        elif data == "charge":
            context.user_data['step'] = self.WAITING_FOR_AMOUNT
            await query.edit_message_text("💰 مبلغ را به تومان وارد کنید:")
        elif data == "withdraw":
            context.user_data['step'] = self.WAITING_FOR_AMOUNT
            await query.edit_message_text("🏦 مبلغ برداشت را وارد کنید:")
        elif data.startswith("buy_"):
            amount = int(data.split("_")[1])
            await self.buy_diamonds(user_id, amount, query)
        elif data.startswith("premium_"):
            plan = data.split("_")[1]
            await self.buy_premium(user_id, plan, query)
        elif data.startswith("admin_"):
            await self.admin_actions(user_id, data, query)
    
    # ==================== BUSINESS LOGIC ====================
    
    async def buy_diamonds(self, user_id: str, amount: int, query):
        session = Session()
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                await query.edit_message_text("❌ کاربر یافت نشد")
                return
            
            price = Config.DIAMOND_PACKS.get(amount)
            if not price:
                await query.edit_message_text("❌ پکیج نامعتبر")
                return
            
            # Create invoice
            invoice_number = Utils.generate_invoice_number()
            invoice = Invoice(
                invoice_number=invoice_number,
                user_id=user.id,
                amount=price,
                description=f"خرید {amount} الماس",
                status='pending',
                created_at=datetime.now()
            )
            session.add(invoice)
            session.commit()
            
            # Create transaction
            transaction = DBManager.create_transaction(
                user.id, 'purchase', amount=price, 
                diamonds_amount=amount, description=f"خرید {amount} الماس",
                reference_id=invoice_number
            )
            
            text = f"🧾 *فاکتور*\nشماره: `{invoice_number}`\nمبلغ: {price:,} تومان\nوضعیت: در انتظار پرداخت\n\nشماره کارت: `{Config.BANK_CARD['number']}`"
            keyboard = [[InlineKeyboardButton("📤 ارسال رسید", callback_data="send_receipt")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        finally:
            session.close()
    
    async def buy_premium(self, user_id: str, plan: str, query):
        session = Session()
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                await query.edit_message_text("❌ کاربر یافت نشد")
                return
            
            plan_data = Config.PREMIUM_PLANS.get(plan)
            if not plan_data:
                await query.edit_message_text("❌ پلن نامعتبر")
                return
            
            if user.diamonds_balance < plan_data['diamonds']:
                await query.edit_message_text(f"❌ الماس کافی نیست!\nنیاز: {plan_data['diamonds']} 💎\nموجودی: {user.diamonds_balance} 💎")
                return
            
            # Deduct diamonds
            user.diamonds_balance -= plan_data['diamonds']
            user.is_premium = True
            user.premium_expire = Utils.get_expiry_date(plan_data['days'])
            
            # Create purchase
            purchase = Purchase(
                user_id=user.id,
                plan_type=plan,
                duration_days=plan_data['days'],
                diamonds_cost=plan_data['diamonds'],
                amount=plan_data['price'],
                started_at=datetime.now(),
                expires_at=user.premium_expire
            )
            session.add(purchase)
            
            # Create transaction
            transaction = Transaction(
                user_id=user.id,
                type='premium',
                status='completed',
                diamonds_amount=-plan_data['diamonds'],
                description=f"پریمیوم {plan_data['days']} روزه",
                diamonds_before=user.diamonds_balance + plan_data['diamonds'],
                diamonds_after=user.diamonds_balance,
                completed_at=datetime.now()
            )
            session.add(transaction)
            session.commit()
            
            await query.edit_message_text(
                f"⭐ *پریمیوم فعال شد!*\nاعتبار تا: {user.premium_expire.strftime('%Y/%m/%d')}",
                parse_mode=ParseMode.MARKDOWN
            )
        finally:
            session.close()
    
    # ==================== ADMIN ACTIONS ====================
    
    async def admin_actions(self, user_id: str, data: str, query):
        if not await self.is_admin(user_id):
            await query.edit_message_text("⛔ فقط ادمین")
            return
        
        action = data.split("_")[1]
        
        if action == "users":
            await self.admin_users(query)
        elif action == "verify":
            await self.admin_verify(query)
        elif action == "ads":
            await self.admin_ads(query)
        elif action == "stats":
            await self.stats(query.message, None)
        elif action == "maintenance":
            await self.admin_maintenance(query)
        elif action == "broadcast":
            await self.broadcast(query.message, None)
    
    async def admin_users(self, query):
        session = Session()
        try:
            users = session.query(User).order_by(User.created_at.desc()).limit(10).all()
            text = "👑 *کاربران*\n\n"
            for user in users:
                text += f"🆔 {user.telegram_id}\n👤 {user.first_name or 'نامشخص'}\n💎 {user.diamonds_balance}\n---\n"
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        finally:
            session.close()
    
    async def admin_verify(self, query):
        session = Session()
        try:
            invoices = session.query(Invoice).filter_by(status='pending').limit(5).all()
            if not invoices:
                await query.edit_message_text("✅ هیچ پرداخت در انتظار تایید نیست")
                return
            
            text = "✅ *تایید پرداخت*\n\n"
            keyboard = []
            for inv in invoices:
                user = session.query(User).filter_by(id=inv.user_id).first()
                text += f"🧾 {inv.invoice_number}\n👤 {user.telegram_id}\n💰 {inv.amount:,.0f} تومان\n---\n"
                keyboard.append([
                    InlineKeyboardButton(f"✅ تایید {inv.invoice_number}", callback_data=f"verify_{inv.id}"),
                    InlineKeyboardButton(f"❌ رد", callback_data=f"reject_{inv.id}")
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        finally:
            session.close()
    
    async def admin_ads(self, query):
        await query.edit_message_text("📢 *مدیریت تبلیغات*\nدر حال توسعه...")
    
    async def admin_maintenance(self, query):
        if str(query.from_user.id) not in Config.OWNER_IDS:
            await query.edit_message_text("⛔ فقط OWNER")
            return
        
        session = Session()
        try:
            setting = session.query(SystemSetting).filter_by(key='maintenance').first()
            if not setting:
                setting = SystemSetting(key='maintenance', value='false', category='system')
                session.add(setting)
            else:
                setting.value = 'false' if setting.value == 'true' else 'true'
            session.commit()
            
            status = "فعال" if setting.value == 'true' else "غیرفعال"
            await query.edit_message_text(f"🛠 حالت نگهداری {status} شد")
        finally:
            session.close()
    
    # ==================== MESSAGE HANDLERS ====================
    
    async def text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        text = update.message.text
        step = context.user_data.get('step')
        
        if step == self.WAITING_FOR_AMOUNT:
            try:
                amount = float(text.replace(',', '').replace('٫', ''))
                if amount < 10000:
                    await update.message.reply_text("❌ حداقل مبلغ ۱۰,۰۰۰ تومان")
                    return
                
                # Create invoice
                session = Session()
                try:
                    user = session.query(User).filter_by(telegram_id=user_id).first()
                    invoice_number = Utils.generate_invoice_number()
                    invoice = Invoice(
                        invoice_number=invoice_number,
                        user_id=user.id,
                        amount=amount,
                        description="شارژ کیف پول",
                        status='pending',
                        created_at=datetime.now()
                    )
                    session.add(invoice)
                    session.commit()
                    
                    text = f"🧾 *فاکتور*\nشماره: `{invoice_number}`\nمبلغ: {amount:,.0f} تومان\n\nشماره کارت: `{Config.BANK_CARD['number']}`"
                    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
                finally:
                    session.close()
                context.user_data['step'] = None
            except:
                await update.message.reply_text("❌ عدد معتبر وارد کنید")
        
        elif step == self.WAITING_FOR_RECEIPT:
            await update.message.reply_text("📤 لطفاً عکس رسید را ارسال کنید")
            context.user_data['step'] = None
        
        elif step == self.WAITING_FOR_BROADCAST:
            await self.send_broadcast(update, context)
    
    async def photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        
        # Save receipt
        photo = update.message.photo[-1]
        file = await photo.get_file()
        
        os.makedirs('receipts', exist_ok=True)
        file_path = f"receipts/{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        await file.download_to_drive(file_path)
        
        # Find pending invoice
        session = Session()
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if user:
                invoice = session.query(Invoice).filter_by(
                    user_id=user.id, status='pending'
                ).order_by(Invoice.created_at.desc()).first()
                
                if invoice:
                    invoice.receipt_image = file_path
                    session.commit()
                    
                    await update.message.reply_text("✅ رسید دریافت شد. در انتظار تایید ادمین.")
                    
                    # Notify admins
                    for admin_id in Config.ADMIN_IDS:
                        try:
                            await self.application.bot.send_message(
                                chat_id=admin_id,
                                text=f"📤 رسید جدید\nکاربر: {user.telegram_id}\nفاکتور: {invoice.invoice_number}\nمبلغ: {invoice.amount:,.0f} تومان"
                            )
                        except:
                            pass
                else:
                    await update.message.reply_text("❌ فاکتور در انتظار پرداختی یافت نشد")
        finally:
            session.close()
    
    async def send_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        if not await self.is_admin(user_id):
            return
        
        content = update.message.text
        session = Session()
        try:
            users = session.query(User).all()
            sent = 0
            for user in users:
                try:
                    await self.application.bot.send_message(
                        chat_id=user.telegram_id,
                        text=content
                    )
                    sent += 1
                except:
                    pass
            
            await update.message.reply_text(f"✅ Broadcast ارسال شد!\nارسال شده: {sent} از {len(users)}")
        finally:
            session.close()
        context.user_data['step'] = None
    
    # ==================== HELPER FUNCTIONS ====================
    
    async def get_user(self, update: Update) -> User:
        user = update.effective_user
        return DBManager.create_user(
            str(user.id), user.username, user.first_name, user.last_name
        )
    
    async def is_admin(self, user_id: str) -> bool:
        if user_id in Config.OWNER_IDS or user_id in Config.ADMIN_IDS:
            return True
        session = Session()
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            return user and user.role in ['owner', 'admin']
        finally:
            session.close()
    
    # ==================== SCHEDULED JOBS ====================
    
    async def daily_backup(self):
        try:
            backup_file = f"backup_{datetime.now().strftime('%Y%m%d')}.db"
            shutil.copy2("bot.db", backup_file)
            logger.info(f"Backup created: {backup_file}")
        except Exception as e:
            logger.error(f"Backup error: {e}")
    
    async def cleanup_premium(self):
        session = Session()
        try:
            expired = session.query(User).filter(
                User.is_premium == True,
                User.premium_expire < datetime.now()
            ).all()
            
            for user in expired:
                user.is_premium = False
                user.premium_expire = None
            
            session.commit()
            logger.info(f"Cleaned {len(expired)} expired premium users")
        finally:
            session.close()
    
    # ==================== ERROR HANDLER ====================
    
    async def error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Error: {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text("❌ خطا! دوباره تلاش کنید.")
    
    # ==================== RUN ====================
    
    def run(self):
        logger.info("Starting bot...")
        os.makedirs('receipts', exist_ok=True)
        self.scheduler.start()
        self.application.run_polling()

# ==================== MAIN ====================

def main():
    try:
        bot = Bot(Config.TOKEN)
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == '__main__':
    main()
