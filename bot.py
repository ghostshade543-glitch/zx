# -*- coding: utf-8 -*-
"""
Telegram Bot - Complete System with Payment Verification & Ads System
Version: 2.0.0
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
from cryptography.fernet import Fernet

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
    
    # Encryption
    ENCRYPTION_KEY = Fernet.generate_key()
    
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
    phone_number = Column(String(20))
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
    user_phone = Column(String(20))
    user_card = Column(String(20))
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
    user_phone = Column(String(20))
    user_card = Column(String(20))
    content = Column(Text)
    media_type = Column(String(20))
    media_id = Column(String(200))
    price = Column(Float)
    status = Column(String(20), default='pending')  # pending, active, rejected, completed
    views = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    started_at = Column(DateTime)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    verified_by = Column(Integer, ForeignKey('users.id'))
    verified_at = Column(DateTime)
    
    user = relationship("User", foreign_keys=[user_id])
    verifier = relationship("User", foreign_keys=[verified_by])

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
    def validate_phone_number(phone: str) -> bool:
        phone = re.sub(r'\D', '', phone)
        if len(phone) == 10:
            phone = '0' + phone
        return len(phone) == 11 and phone.startswith('09')
    
    @staticmethod
    def generate_uuid() -> str:
        return str(uuid.uuid4())
    
    @staticmethod
    def encrypt_data(data: str) -> str:
        f = Fernet(Config.ENCRYPTION_KEY)
        return f.encrypt(data.encode()).decode()
    
    @staticmethod
    def decrypt_data(data: str) -> str:
        f = Fernet(Config.ENCRYPTION_KEY)
        return f.decrypt(data.encode()).decode()

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
                      "📱 موبایل: {phone}\n"
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
                      "صاحب حساب: {owner}\n\n"
                      "📝 لطفاً اطلاعات زیر را وارد کنید:\n"
                      "1. شماره موبایل\n"
                      "2. شماره کارت مبدا",
            'payment_info': "💳 *اطلاعات پرداخت*\n\n"
                          "شماره موبایل: {phone}\n"
                          "شماره کارت: {card}\n"
                          "مبلغ: {amount:,} تومان\n"
                          "وضعیت: {status}",
            'ad_registration': "📢 *ثبت تبلیغ*\n\n"
                             "هزینه: {price:,} تومان\n"
                             "مدت: ۳۰ روز\n\n"
                             "📝 اطلاعات زیر را وارد کنید:\n"
                             "1. شماره موبایل\n"
                             "2. شماره کارت\n"
                             "3. متن تبلیغ",
            'ad_info': "📢 *اطلاعات تبلیغ*\n\n"
                      "شماره موبایل: {phone}\n"
                      "شماره کارت: {card}\n"
                      "متن: {content}\n"
                      "وضعیت: {status}",
            'maintenance': "🛠 در حال بروزرسانی...",
            'admin_required': "⛔ فقط ادمین",
            'success': "✅ موفق",
            'failed': "❌ ناموفق",
            'verify_success': "✅ پرداخت تایید شد!\n"
                            "فاکتور: {invoice}\n"
                            "کاربر: {user}\n"
                            "مبلغ: {amount:,} تومان",
            'verify_failed': "❌ پرداخت رد شد!\n"
                           "فاکتور: {invoice}",
            'ad_approve': "✅ تبلیغ تایید شد!\n"
                         "🆔 {uuid}\n"
                         "کاربر: {user}",
            'ad_reject': "❌ تبلیغ رد شد!\n"
                        "🆔 {uuid}",
            'help_text': "📚 *راهنما*\n\n"
                        "/start - شروع\n"
                        "/profile - پروفایل\n"
                        "/wallet - کیف پول\n"
                        "/diamonds - الماس\n"
                        "/premium - پریمیوم\n"
                        "/payment - پرداخت\n"
                        "/ads - تبلیغات\n"
                        "/support - پشتیبانی"
        },
        'en': {
            'welcome_new': "🎉 Welcome {name}!\n\n"
                          "💎 You received {gift} diamonds.",
            'welcome_back': "👋 Welcome back {name}!",
            'profile': "👤 *Profile*\n\n"
                      "🆔 ID: {id}\n"
                      "👤 Name: {name}\n"
                      "📱 Phone: {phone}\n"
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
                      "Owner: {owner}\n\n"
                      "📝 Please enter:\n"
                      "1. Phone number\n"
                      "2. Sender card number",
            'payment_info': "💳 *Payment Info*\n\n"
                          "Phone: {phone}\n"
                          "Card: {card}\n"
                          "Amount: {amount:,} IRR\n"
                          "Status: {status}",
            'ad_registration': "📢 *Ad Registration*\n\n"
                             "Price: {price:,} IRR\n"
                             "Duration: 30 days\n\n"
                             "📝 Enter:\n"
                             "1. Phone number\n"
                             "2. Card number\n"
                             "3. Ad content",
            'ad_info': "📢 *Ad Info*\n\n"
                      "Phone: {phone}\n"
                      "Card: {card}\n"
                      "Content: {content}\n"
                      "Status: {status}",
            'maintenance': "🛠 Under maintenance...",
            'admin_required': "⛔ Admin only",
            'success': "✅ Success",
            'failed': "❌ Failed",
            'verify_success': "✅ Payment verified!\n"
                            "Invoice: {invoice}\n"
                            "User: {user}\n"
                            "Amount: {amount:,} IRR",
            'verify_failed': "❌ Payment rejected!\n"
                           "Invoice: {invoice}",
            'ad_approve': "✅ Ad approved!\n"
                         "🆔 {uuid}\n"
                         "User: {user}",
            'ad_reject': "❌ Ad rejected!\n"
                        "🆔 {uuid}",
            'help_text': "📚 *Help*\n\n"
                        "/start - Start\n"
                        "/profile - Profile\n"
                        "/wallet - Wallet\n"
                        "/diamonds - Diamonds\n"
                        "/premium - Premium\n"
                        "/payment - Payment\n"
                        "/ads - Ads\n"
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
    def update_user(user_id: int, **kwargs):
        session = Session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                for key, value in kwargs.items():
                    setattr(user, key, value)
                session.commit()
            return user
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
        self.WAITING_FOR_PAYMENT_PHONE = 1
        self.WAITING_FOR_PAYMENT_CARD = 2
        self.WAITING_FOR_RECEIPT = 3
        self.WAITING_FOR_AD_PHONE = 4
        self.WAITING_FOR_AD_CARD = 5
        self.WAITING_FOR_AD_TEXT = 6
        self.WAITING_FOR_AD_RECEIPT = 7
        self.WAITING_FOR_BROADCAST = 8
        self.WAITING_FOR_AMOUNT = 9
        
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
        self.application.add_handler(CommandHandler("ads", self.ads))
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
        self.scheduler.add_job(
            self.cleanup_expired_ads,
            CronTrigger(hour=4, minute=0),
            id='cleanup_ads'
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
            [InlineKeyboardButton("📢 تبلیغات", callback_data="ads"),
             InlineKeyboardButton("📞 پشتیبانی", callback_data="support")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    async def menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("💎 الماس", callback_data="diamonds"),
             InlineKeyboardButton("⭐ پریمیوم", callback_data="premium")],
            [InlineKeyboardButton("💰 کیف پول", callback_data="wallet"),
             InlineKeyboardButton("👤 پروفایل", callback_data="profile")],
            [InlineKeyboardButton("📢 تبلیغات", callback_data="ads")]
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
            phone=user.phone_number or 'ثبت نشده',
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
            [InlineKeyboardButton("📤 ثبت اطلاعات پرداخت", callback_data="payment_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    async def ads(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await self.get_user(update)
        lang = user.language
        
        text = I18n.get_text('ad_registration', lang, price=Config.AD_PRICE)
        
        keyboard = [
            [InlineKeyboardButton("📝 ثبت تبلیغ جدید", callback_data="register_ad")],
            [InlineKeyboardButton("📊 آمار تبلیغات من", callback_data="my_ads")]
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
            [InlineKeyboardButton("📢 تایید تبلیغات", callback_data="admin_ads")],
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
            pending_invoices = session.query(Invoice).filter_by(status='pending').count()
            pending_ads = session.query(Ad).filter_by(status='pending').count()
            total_revenue = session.query(Transaction).filter_by(status='completed').with_entities(
                func.sum(Transaction.amount)
            ).scalar() or 0
            
            text = f"📊 *آمار سیستم*\n\n"
            text += f"👤 کاربران: {total_users}\n"
            text += f"⭐ پریمیوم: {premium_users}\n"
            text += f"🧾 پرداخت‌های در انتظار: {pending_invoices}\n"
            text += f"📢 تبلیغات در انتظار: {pending_ads}\n"
            text += f"💰 درآمد کل: {total_revenue:,.0f} تومان"
            
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
        elif data == "ads":
            await self.ads(update, context)
        elif data == "copy_card":
            await query.edit_message_text(f"✅ کپی شد:\n`{Config.BANK_CARD['number']}`", parse_mode=ParseMode.MARKDOWN)
        elif data == "payment_info":
            context.user_data['step'] = self.WAITING_FOR_PAYMENT_PHONE
            context.user_data['payment_type'] = 'diamond'
            await query.edit_message_text("📱 لطفاً شماره موبایل خود را وارد کنید:")
        elif data == "register_ad":
            context.user_data['step'] = self.WAITING_FOR_AD_PHONE
            await query.edit_message_text("📱 لطفاً شماره موبایل خود را وارد کنید:")
        elif data == "my_ads":
            await self.show_my_ads(query)
        elif data == "charge":
            context.user_data['step'] = self.WAITING_FOR_AMOUNT
            context.user_data['payment_type'] = 'charge'
            await query.edit_message_text("💰 مبلغ شارژ را به تومان وارد کنید:")
        elif data == "withdraw":
            context.user_data['step'] = self.WAITING_FOR_AMOUNT
            context.user_data['payment_type'] = 'withdraw'
            await query.edit_message_text("🏦 مبلغ برداشت را وارد کنید:")
        elif data.startswith("buy_"):
            amount = int(data.split("_")[1])
            await self.buy_diamonds(user_id, amount, query)
        elif data.startswith("premium_"):
            plan = data.split("_")[1]
            await self.buy_premium(user_id, plan, query)
        elif data.startswith("verify_"):
            invoice_id = int(data.split("_")[1])
            await self.verify_payment(user_id, invoice_id, query)
        elif data.startswith("reject_"):
            invoice_id = int(data.split("_")[1])
            await self.reject_payment(user_id, invoice_id, query)
        elif data.startswith("ad_approve_"):
            ad_id = int(data.split("_")[2])
            await self.approve_ad(user_id, ad_id, query)
        elif data.startswith("ad_reject_"):
            ad_id = int(data.split("_")[2])
            await self.reject_ad(user_id, ad_id, query)
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
            
            text = f"🧾 *فاکتور*\nشماره: `{invoice_number}`\n"
            text += f"مبلغ: {price:,} تومان\n"
            text += f"تعداد: {amount} 💎\n"
            text += f"وضعیت: در انتظار پرداخت\n\n"
            text += f"🏦 شماره کارت: `{Config.BANK_CARD['number']}`\n"
            text += f"👤 صاحب حساب: {Config.BANK_CARD['owner']}\n"
            text += f"🏛 بانک: {Config.BANK_CARD['bank']}\n\n"
            text += "📝 پس از واریز، اطلاعات پرداخت را ثبت کنید."
            
            keyboard = [[InlineKeyboardButton("📤 ثبت اطلاعات پرداخت", callback_data="payment_info")]]
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
    
    # ==================== PAYMENT SYSTEM ====================
    
    async def verify_payment(self, admin_id: str, invoice_id: int, query):
        """Admin verifies a payment"""
        if not await self.is_admin(admin_id):
            await query.edit_message_text("⛔ فقط ادمین")
            return
        
        session = Session()
        try:
            invoice = session.query(Invoice).filter_by(id=invoice_id).first()
            if not invoice:
                await query.edit_message_text("❌ فاکتور یافت نشد")
                return
            
            user = session.query(User).filter_by(id=invoice.user_id).first()
            if not user:
                await query.edit_message_text("❌ کاربر یافت نشد")
                return
            
            # Update invoice
            invoice.status = 'verified'
            invoice.verified_by = session.query(User).filter_by(telegram_id=admin_id).first().id
            invoice.verified_at = datetime.now()
            
            # Add diamonds if it's a diamond purchase
            if 'الماس' in invoice.description:
                import re
                match = re.search(r'(\d+)', invoice.description)
                if match:
                    diamonds = int(match.group(1))
                    user.diamonds_balance += diamonds
                    
                    # Create completed transaction
                    transaction = Transaction(
                        user_id=user.id,
                        type='purchase',
                        status='completed',
                        amount=invoice.amount,
                        diamonds_amount=diamonds,
                        description=invoice.description,
                        diamonds_before=user.diamonds_balance - diamonds,
                        diamonds_after=user.diamonds_balance,
                        completed_at=datetime.now()
                    )
                    session.add(transaction)
            
            session.commit()
            
            # Audit log
            audit = AuditLog(
                user_id=session.query(User).filter_by(telegram_id=admin_id).first().id,
                action='verify_payment',
                description=f'Verified payment {invoice.invoice_number}',
                details={'invoice': invoice.invoice_number, 'user': user.telegram_id}
            )
            session.add(audit)
            session.commit()
            
            await query.edit_message_text(
                I18n.get_text('verify_success', 'fa',
                    invoice=invoice.invoice_number,
                    user=user.telegram_id,
                    amount=invoice.amount
                ),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Notify user
            try:
                await self.application.bot.send_message(
                    chat_id=user.telegram_id,
                    text=f"✅ *پرداخت شما تایید شد!*\n\nفاکتور: {invoice.invoice_number}\nمبلغ: {invoice.amount:,.0f} تومان\n\nاز شما متشکریم!",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
                
        except Exception as e:
            session.rollback()
            await query.edit_message_text(f"❌ خطا: {str(e)}")
        finally:
            session.close()
    
    async def reject_payment(self, admin_id: str, invoice_id: int, query):
        """Admin rejects a payment"""
        if not await self.is_admin(admin_id):
            await query.edit_message_text("⛔ فقط ادمین")
            return
        
        session = Session()
        try:
            invoice = session.query(Invoice).filter_by(id=invoice_id).first()
            if not invoice:
                await query.edit_message_text("❌ فاکتور یافت نشد")
                return
            
            user = session.query(User).filter_by(id=invoice.user_id).first()
            
            invoice.status = 'rejected'
            invoice.verified_by = session.query(User).filter_by(telegram_id=admin_id).first().id
            invoice.verified_at = datetime.now()
            session.commit()
            
            await query.edit_message_text(
                I18n.get_text('verify_failed', 'fa',
                    invoice=invoice.invoice_number
                ),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Notify user
            try:
                await self.application.bot.send_message(
                    chat_id=user.telegram_id,
                    text=f"❌ *پرداخت شما رد شد!*\n\nفاکتور: {invoice.invoice_number}\n\nلطفاً با پشتیبانی تماس بگیرید.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
                
        except Exception as e:
            session.rollback()
            await query.edit_message_text(f"❌ خطا: {str(e)}")
        finally:
            session.close()
    
    # ==================== ADS SYSTEM ====================
    
    async def register_ad(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Register a new ad"""
        user = await self.get_user(update)
        
        # Check if user already has active ad
        session = Session()
        try:
            active_ad = session.query(Ad).filter_by(
                user_id=user.id,
                status='active'
            ).first()
            if active_ad:
                await update.message.reply_text("❌ شما یک تبلیغ فعال دارید!")
                return
        finally:
            session.close()
        
        context.user_data['step'] = self.WAITING_FOR_AD_PHONE
        await update.message.reply_text("📱 لطفاً شماره موبایل خود را وارد کنید:")
    
    async def process_ad_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process ad phone number"""
        phone = update.message.text.strip()
        
        if not Utils.validate_phone_number(phone):
            await update.message.reply_text("❌ شماره موبایل نامعتبر!\nلطفاً یک شماره ۱۱ رقمی وارد کنید:")
            return
        
        context.user_data['ad_phone'] = phone
        context.user_data['step'] = self.WAITING_FOR_AD_CARD
        await update.message.reply_text("💳 لطفاً شماره کارت خود را وارد کنید:")
    
    async def process_ad_card(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process ad card number"""
        card = update.message.text.strip()
        
        if not Utils.validate_card_number(card):
            await update.message.reply_text("❌ شماره کارت نامعتبر!\nلطفاً یک شماره ۱۶ رقمی وارد کنید:")
            return
        
        context.user_data['ad_card'] = card
        context.user_data['step'] = self.WAITING_FOR_AD_TEXT
        await update.message.reply_text("📝 متن تبلیغ خود را ارسال کنید:")
    
    async def process_ad_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process ad content"""
        content = update.message.text.strip()
        
        if len(content) < 10:
            await update.message.reply_text("❌ متن تبلیغ باید حداقل ۱۰ کاراکتر باشد!")
            return
        
        user = await self.get_user(update)
        
        session = Session()
        try:
            # Create ad
            ad = Ad(
                user_id=user.id,
                user_phone=context.user_data['ad_phone'],
                user_card=Utils.encrypt_data(context.user_data['ad_card']),
                content=content,
                price=Config.AD_PRICE,
                status='pending',
                created_at=datetime.now()
            )
            session.add(ad)
            session.commit()
            
            # Create invoice for ad
            invoice_number = Utils.generate_invoice_number()
            invoice = Invoice(
                invoice_number=invoice_number,
                user_id=user.id,
                amount=Config.AD_PRICE,
                description=f"ثبت تبلیغ - {ad.uuid[:8]}",
                user_phone=context.user_data['ad_phone'],
                user_card=Utils.encrypt_data(context.user_data['ad_card']),
                status='pending',
                created_at=datetime.now()
            )
            session.add(invoice)
            session.commit()
            
            # Clear context
            context.user_data['step'] = None
            
            text = f"📢 *تبلیغ شما ثبت شد!*\n\n"
            text += f"🆔 شناسه: `{ad.uuid[:8]}`\n"
            text += f"📱 موبایل: {context.user_data['ad_phone']}\n"
            text += f"💳 کارت: {context.user_data['ad_card'][:4]}****{context.user_data['ad_card'][-4:]}\n"
            text += f"💰 هزینه: {Config.AD_PRICE:,} تومان\n"
            text += f"📝 متن: {content[:50]}...\n\n"
            text += f"🧾 فاکتور: `{invoice_number}`\n"
            text += f"وضعیت: در انتظار پرداخت\n\n"
            text += f"🏦 شماره کارت: `{Config.BANK_CARD['number']}`\n"
            text += f"👤 صاحب حساب: {Config.BANK_CARD['owner']}\n\n"
            text += "📝 پس از واریز، رسید را ارسال کنید."
            
            keyboard = [[InlineKeyboardButton("📤 ارسال رسید", callback_data="send_receipt")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            
            # Notify admins
            for admin_id in Config.ADMIN_IDS:
                try:
                    await self.application.bot.send_message(
                        chat_id=admin_id,
                        text=f"📢 *تبلیغ جدید*\n\nکاربر: {user.telegram_id}\n🆔 {ad.uuid[:8]}\n📱 {context.user_data['ad_phone']}\n💰 {Config.AD_PRICE:,} تومان",
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
                    
        except Exception as e:
            session.rollback()
            await update.message.reply_text(f"❌ خطا: {str(e)}")
        finally:
            session.close()
    
    async def approve_ad(self, admin_id: str, ad_id: int, query):
        """Admin approves an ad"""
        if not await self.is_admin(admin_id):
            await query.edit_message_text("⛔ فقط ادمین")
            return
        
        session = Session()
        try:
            ad = session.query(Ad).filter_by(id=ad_id).first()
            if not ad:
                await query.edit_message_text("❌ تبلیغ یافت نشد")
                return
            
            user = session.query(User).filter_by(id=ad.user_id).first()
            
            ad.status = 'active'
            ad.started_at = datetime.now()
            ad.expires_at = datetime.now() + timedelta(days=30)
            ad.verified_by = session.query(User).filter_by(telegram_id=admin_id).first().id
            ad.verified_at = datetime.now()
            session.commit()
            
            await query.edit_message_text(
                I18n.get_text('ad_approve', 'fa',
                    uuid=ad.uuid[:8],
                    user=user.telegram_id if user else 'نامشخص'
                ),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Notify user
            try:
                await self.application.bot.send_message(
                    chat_id=user.telegram_id,
                    text=f"✅ *تبلیغ شما تایید شد!*\n\n🆔 {ad.uuid[:8]}\n📅 فعال تا: {ad.expires_at.strftime('%Y/%m/%d')}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
                
        except Exception as e:
            session.rollback()
            await query.edit_message_text(f"❌ خطا: {str(e)}")
        finally:
            session.close()
    
    async def reject_ad(self, admin_id: str, ad_id: int, query):
        """Admin rejects an ad"""
        if not await self.is_admin(admin_id):
            await query.edit_message_text("⛔ فقط ادمین")
            return
        
        session = Session()
        try:
            ad = session.query(Ad).filter_by(id=ad_id).first()
            if not ad:
                await query.edit_message_text("❌ تبلیغ یافت نشد")
                return
            
            user = session.query(User).filter_by(id=ad.user_id).first()
            
            ad.status = 'rejected'
            ad.verified_by = session.query(User).filter_by(telegram_id=admin_id).first().id
            ad.verified_at = datetime.now()
            session.commit()
            
            await query.edit_message_text(
                I18n.get_text('ad_reject', 'fa',
                    uuid=ad.uuid[:8]
                ),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Notify user
            try:
                await self.application.bot.send_message(
                    chat_id=user.telegram_id,
                    text=f"❌ *تبلیغ شما رد شد!*\n\n🆔 {ad.uuid[:8]}\nلطفاً با پشتیبانی تماس بگیرید.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
                
        except Exception as e:
            session.rollback()
            await query.edit_message_text(f"❌ خطا: {str(e)}")
        finally:
            session.close()
    
    async def show_my_ads(self, query):
        """Show user's ads"""
        user_id = str(query.from_user.id)
        session = Session()
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                await query.edit_message_text("❌ کاربر یافت نشد")
                return
            
            ads = session.query(Ad).filter_by(user_id=user.id).order_by(Ad.created_at.desc()).all()
            
            if not ads:
                await query.edit_message_text("📊 شما هیچ تبلیغی ثبت نکرده‌اید.")
                return
            
            text = "📊 *تبلیغات شما*\n\n"
            for ad in ads:
                status_emoji = "✅" if ad.status == 'active' else "⏳" if ad.status == 'pending' else "❌"
                text += f"{status_emoji} 🆔 {ad.uuid[:8]}\n"
                text += f"📝 {ad.content[:50]}...\n"
                text += f"👁 بازدید: {ad.views}\n"
                text += f"🖱 کلیک: {ad.clicks}\n"
                text += f"📅 {ad.created_at.strftime('%Y/%m/%d')}\n"
                text += f"وضعیت: {ad.status}\n"
                text += "---\n"
            
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
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
            users = session.query(User).order_by(User.created_at.desc()).limit(20).all()
            text = "👑 *کاربران*\n\n"
            for user in users:
                text += f"🆔 {user.telegram_id}\n"
                text += f"👤 {user.first_name or 'نامشخص'}\n"
                text += f"📱 {user.phone_number or 'ثبت نشده'}\n"
                text += f"💎 {user.diamonds_balance} | ⭐ {'✅' if user.is_premium else '❌'}\n"
                text += f"📅 {user.created_at.strftime('%Y/%m/%d')}\n"
                text += "---\n"
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        finally:
            session.close()
    
    async def admin_verify(self, query):
        session = Session()
        try:
            invoices = session.query(Invoice).filter_by(status='pending').order_by(Invoice.created_at).limit(10).all()
            
            if not invoices:
                await query.edit_message_text("✅ هیچ پرداخت در انتظار تایید نیست")
                return
            
            text = "✅ *تایید پرداخت*\n\n"
            keyboard = []
            for inv in invoices:
                user = session.query(User).filter_by(id=inv.user_id).first()
                text += f"🧾 {inv.invoice_number}\n"
                text += f"👤 {user.telegram_id if user else 'نامشخص'}\n"
                text += f"📱 {inv.user_phone or 'ثبت نشده'}\n"
                text += f"💳 {inv.user_card[:4] if inv.user_card else '****'}****{inv.user_card[-4:] if inv.user_card else '****'}\n"
                text += f"💰 {inv.amount:,.0f} تومان\n"
                text += f"📝 {inv.description}\n"
                text += "---\n"
                keyboard.append([
                    InlineKeyboardButton(f"✅ تایید", callback_data=f"verify_{inv.id}"),
                    InlineKeyboardButton(f"❌ رد", callback_data=f"reject_{inv.id}")
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        finally:
            session.close()
    
    async def admin_ads(self, query):
        session = Session()
        try:
            pending_ads = session.query(Ad).filter_by(status='pending').order_by(Ad.created_at).limit(10).all()
            
            if not pending_ads:
                await query.edit_message_text("📢 هیچ تبلیغ در انتظار تایید نیست")
                return
            
            text = "📢 *تایید تبلیغات*\n\n"
            keyboard = []
            for ad in pending_ads:
                user = session.query(User).filter_by(id=ad.user_id).first()
                decrypted_card = Utils.decrypt_data(ad.user_card) if ad.user_card else 'نامشخص'
                text += f"🆔 {ad.uuid[:8]}\n"
                text += f"👤 {user.telegram_id if user else 'نامشخص'}\n"
                text += f"📱 {ad.user_phone or 'ثبت نشده'}\n"
                text += f"💳 {decrypted_card[:4]}****{decrypted_card[-4:]}\n"
                text += f"📝 {ad.content[:100]}...\n"
                text += f"💰 {ad.price:,.0f} تومان\n"
                text += "---\n"
                keyboard.append([
                    InlineKeyboardButton(f"✅ تایید", callback_data=f"ad_approve_{ad.id}"),
                    InlineKeyboardButton(f"❌ رد", callback_data=f"ad_reject_{ad.id}")
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        finally:
            session.close()
    
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
        
        # Payment flow
        if step == self.WAITING_FOR_PAYMENT_PHONE:
            if not Utils.validate_phone_number(text):
                await update.message.reply_text("❌ شماره موبایل نامعتبر!\nلطفاً یک شماره ۱۱ رقمی وارد کنید:")
                return
            context.user_data['payment_phone'] = text
            context.user_data['step'] = self.WAITING_FOR_PAYMENT_CARD
            await update.message.reply_text("💳 لطفاً شماره کارت مبدا را وارد کنید:")
        
        elif step == self.WAITING_FOR_PAYMENT_CARD:
            if not Utils.validate_card_number(text):
                await update.message.reply_text("❌ شماره کارت نامعتبر!\nلطفاً یک شماره ۱۶ رقمی وارد کنید:")
                return
            
            # Save payment info to latest pending invoice
            session = Session()
            try:
                user = session.query(User).filter_by(telegram_id=user_id).first()
                if user:
                    invoice = session.query(Invoice).filter_by(
                        user_id=user.id,
                        status='pending'
                    ).order_by(Invoice.created_at.desc()).first()
                    
                    if invoice:
                        invoice.user_phone = context.user_data['payment_phone']
                        invoice.user_card = Utils.encrypt_data(text)
                        session.commit()
                        
                        await update.message.reply_text(
                            f"✅ اطلاعات پرداخت ثبت شد!\n\n"
                            f"📱 شماره موبایل: {context.user_data['payment_phone']}\n"
                            f"💳 شماره کارت: {text[:4]}****{text[-4:]}\n"
                            f"🧾 فاکتور: {invoice.invoice_number}\n\n"
                            f"📤 لطفاً رسید پرداخت را ارسال کنید."
                        )
                        
                        context.user_data['step'] = self.WAITING_FOR_RECEIPT
                        context.user_data['invoice_id'] = invoice.id
                    else:
                        await update.message.reply_text("❌ فاکتور در انتظار پرداختی یافت نشد!")
            finally:
                session.close()
        
        # Receipt flow
        elif step == self.WAITING_FOR_RECEIPT:
            await update.message.reply_text("📤 لطفاً عکس رسید را ارسال کنید")
            context.user_data['step'] = None
        
        # Ad phone
        elif step == self.WAITING_FOR_AD_PHONE:
            await self.process_ad_phone(update, context)
        
        # Ad card
        elif step == self.WAITING_FOR_AD_CARD:
            await self.process_ad_card(update, context)
        
        # Ad text
        elif step == self.WAITING_FOR_AD_TEXT:
            await self.process_ad_text(update, context)
        
        # Broadcast
        elif step == self.WAITING_FOR_BROADCAST:
            await self.send_broadcast(update, context)
        
        # Amount for charge/withdraw
        elif step == self.WAITING_FOR_AMOUNT:
            try:
                amount = float(text.replace(',', '').replace('٫', ''))
                if amount < 10000:
                    await update.message.reply_text("❌ حداقل مبلغ ۱۰,۰۰۰ تومان")
                    return
                
                payment_type = context.user_data.get('payment_type', 'charge')
                
                if payment_type == 'charge':
                    # Create invoice for charge
                    session = Session()
                    try:
                        user = session.query(User).filter_by(telegram_id=user_id).first()
                        invoice_number = Utils.generate_invoice_number()
                        invoice = Invoice(
                            invoice_number=invoice_number,
                            user_id=user.id,
                            amount=amount,
                            description=f"شارژ کیف پول",
                            status='pending',
                            created_at=datetime.now()
                        )
                        session.add(invoice)
                        session.commit()
                        
                        text = f"🧾 *فاکتور شارژ*\n"
                        text += f"شماره: `{invoice_number}`\n"
                        text += f"مبلغ: {amount:,.0f} تومان\n"
                        text += f"وضعیت: در انتظار پرداخت\n\n"
                        text += f"🏦 شماره کارت: `{Config.BANK_CARD['number']}`\n"
                        text += f"👤 صاحب حساب: {Config.BANK_CARD['owner']}\n\n"
                        text += "📝 پس از واریز، اطلاعات پرداخت را ثبت کنید."
                        
                        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
                        context.user_data['step'] = None
                    finally:
                        session.close()
                
                elif payment_type == 'withdraw':
                    # Process withdrawal
                    session = Session()
                    try:
                        user = session.query(User).filter_by(telegram_id=user_id).first()
                        if user.wallet_balance < amount:
                            await update.message.reply_text(f"❌ موجودی کافی نیست!\nموجودی: {user.wallet_balance:,.0f} تومان")
                            return
                        
                        # Create transaction
                        transaction = DBManager.create_transaction(
                            user.id, 'withdraw', amount=amount,
                            description=f"برداشت {amount:,.0f} تومان"
                        )
                        
                        text = f"🏦 *درخواست برداشت*\n"
                        text += f"مبلغ: {amount:,.0f} تومان\n"
                        text += f"وضعیت: در انتظار تایید ادمین\n\n"
                        text += f"شماره کارت: {user.phone_number or 'ثبت نشده'}"
                        
                        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
                        context.user_data['step'] = None
                    finally:
                        session.close()
                        
            except:
                await update.message.reply_text("❌ عدد معتبر وارد کنید")
    
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
                                text=f"📤 *رسید جدید*\n\n"
                                     f"کاربر: {user.telegram_id}\n"
                                     f"فاکتور: {invoice.invoice_number}\n"
                                     f"مبلغ: {invoice.amount:,.0f} تومان\n"
                                     f"موبایل: {invoice.user_phone or 'ثبت نشده'}\n"
                                     f"کارت: {invoice.user_card[:4] if invoice.user_card else '****'}****{invoice.user_card[-4:] if invoice.user_card else '****'}\n\n"
                                     f"برای تایید به پنل ادمین مراجعه کنید.",
                                parse_mode=ParseMode.MARKDOWN
                            )
                        except:
                            pass
                    
                    context.user_data['step'] = None
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
    
    async def cleanup_expired_ads(self):
        session = Session()
        try:
            expired_ads = session.query(Ad).filter(
                Ad.status == 'active',
                Ad.expires_at < datetime.now()
            ).all()
            
            for ad in expired_ads:
                ad.status = 'completed'
            
            session.commit()
            logger.info(f"Cleaned {len(expired_ads)} expired ads")
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
