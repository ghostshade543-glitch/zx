# -*- coding: utf-8 -*-
"""
Ghost Assistant Bot - Complete Telegram Bot System
Version: 1.0.0
Last Update: 1405/04/22
"""

import asyncio
import logging
import json
import uuid
import hashlib
import re
import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal

# Third-party imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON, BigInteger, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import IntegrityError
import redis
from redis import Redis
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
    DATABASE_URL = "sqlite:///ghost_bot.db"
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_DB = 0
    ENCRYPTION_KEY = Fernet.generate_key()
    TIMEZONE = "Asia/Tehran"
    
    # Admin Users (Telegram IDs)
    OWNER_IDS = ["8961040480"]  # Replace with actual owner IDs
    ADMIN_IDS = ["8961040480"]  # Add other admin IDs
    
    # Channel and Group IDs
    CHANNEL_ID = "-1001234567890"  # Replace with your channel ID
    GROUP_ID = "-1001234567891"    # Replace with your group ID
    SUPPORT_USERNAME = "@XMrHadi"
    
    # Default settings
    DEFAULT_LANGUAGE = "fa"
    DIAMOND_PRICE = 8000  # IRR per diamond
    GIFT_DIAMONDS = 31
    MAINTENANCE_MODE = False
    MAINTENANCE_MESSAGE = "🛠 ربات در حال بروزرسانی است. زمان تقریبی: 15 دقیقه"
    
    # Premium Plans (in days and diamonds)
    PREMIUM_PLANS = {
        "1_month": {"days": 30, "diamonds": 40, "price": 50000},
        "2_month": {"days": 60, "diamonds": 60, "price": 90000},
        "4_month": {"days": 120, "diamonds": 100, "price": 150000},
        "8_month": {"days": 240, "diamonds": 130, "price": 200000},
        "12_month": {"days": 365, "diamonds": 180, "price": 350000}
    }
    
    # Diamond Purchase Packs
    DIAMOND_PACKS = {
        10: 80000,
        25: 180000,
        50: 350000,
        100: 650000,
        250: 1500000,
        500: 2800000
    }
    
    # Bank Card Information
    BANK_CARD = {
        "number": "6037-9918-1234-5678",
        "owner": "Ali Rezaei",
        "bank": "Melli"
    }
    
    # Ad Prices
    AD_PRICE = 250000  # Monthly ad price
    
    # Rate Limits
    RATE_LIMIT = {
        "messages_per_second": 5,
        "withdraw_per_day": 3,
        "max_invoices": 10,
        "failed_attempts": 5
    }

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
    is_verified = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    premium_expire = Column(DateTime)
    diamonds_balance = Column(Integer, default=0)
    gifted_diamonds = Column(Integer, default=0)
    wallet_balance = Column(Float, default=0.0)
    last_activity = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    transactions = relationship("Transaction", back_populates="user", lazy='dynamic')
    invoices = relationship("Invoice", back_populates="user", lazy='dynamic')
    purchases = relationship("Purchase", back_populates="user", lazy='dynamic')
    ads = relationship("Ad", back_populates="user", lazy='dynamic')
    audit_logs = relationship("AuditLog", back_populates="user", lazy='dynamic')
    broadcasts = relationship("Broadcast", back_populates="creator", lazy='dynamic')

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
    card_number = Column(String(20))
    sender_card = Column(String(20))
    receipt_image = Column(String(200))
    status = Column(String(20), default='pending')
    verified_by = Column(Integer, ForeignKey('users.id'))
    verified_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
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
    status = Column(String(20), default='pending')
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
    plan_type = Column(String(20))
    price = Column(Float)
    status = Column(String(20), default='pending')
    views = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    started_at = Column(DateTime)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    user = relationship("User", back_populates="ads")

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey('users.id'))
    transaction_id = Column(Integer, ForeignKey('transactions.id'))
    action = Column(String(100))
    description = Column(Text)
    ip_address = Column(String(50))
    user_agent = Column(String(200))
    details = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    
    user = relationship("User", back_populates="audit_logs")
    transaction = relationship("Transaction", back_populates="audit_logs")

class Broadcast(Base):
    __tablename__ = 'broadcasts'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    content = Column(Text)
    media_type = Column(String(20))
    media_id = Column(String(200))
    target_users = Column(Text)
    sent_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)
    status = Column(String(20), default='pending')
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.now)
    sent_at = Column(DateTime)
    
    creator = relationship("User", back_populates="broadcasts")

class SystemSetting(Base):
    __tablename__ = 'system_settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True)
    value = Column(Text)
    category = Column(String(50))
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

# Create database
engine = create_engine(Config.DATABASE_URL)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# ==================== REDIS MANAGER ====================
class RedisManager:
    def __init__(self):
        try:
            self.client = Redis(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                db=Config.REDIS_DB,
                decode_responses=True
            )
        except:
            self.client = None
            logger.warning("Redis not available, using fallback")
    
    def get(self, key: str) -> Optional[str]:
        if self.client:
            return self.client.get(key)
        return None
    
    def set(self, key: str, value: str, expire: int = None):
        if self.client:
            if expire:
                self.client.setex(key, expire, value)
            else:
                self.client.set(key, value)
    
    def delete(self, key: str):
        if self.client:
            self.client.delete(key)
    
    def incr(self, key: str) -> int:
        if self.client:
            return self.client.incr(key)
        return 0
    
    def exists(self, key: str) -> bool:
        if self.client:
            return self.client.exists(key) > 0
        return False
    
    def hset(self, name: str, key: str, value: str):
        if self.client:
            self.client.hset(name, key, value)
    
    def hget(self, name: str, key: str) -> Optional[str]:
        if self.client:
            return self.client.hget(name, key)
        return None
    
    def hgetall(self, name: str) -> Dict:
        if self.client:
            return self.client.hgetall(name)
        return {}

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
            'welcome_new': "🎉 به ربات Ghost Assistant خوش آمدید {name} عزیز!\n\n"
                          "💎 شما {gift} الماس هدیه دریافت کردید.\n"
                          "از منوی زیر استفاده کنید:",
            'welcome_back': "👋 خوش برگشتید {name} عزیز!\n"
                           "از منوی زیر استفاده کنید:",
            'menu_header': "📋 *منوی اصلی*\n"
                          "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            'profile': "👤 *پروفایل کاربری*\n\n"
                      "🆔 شناسه: {id}\n"
                      "👤 نام: {name}\n"
                      "🌐 زبان: {lang}\n"
                      "💎 الماس: {diamonds}\n"
                      "  ├─ هدیه: {gifted}\n"
                      "  └─ خریداری: {purchased}\n"
                      "⭐ پریمیوم: {premium}\n"
                      "💰 کیف پول: {wallet:,} تومان\n"
                      "📅 عضو از: {joined}",
            'diamonds_shop': "💎 *خرید الماس*\n\n"
                           "💰 قیمت هر الماس: {price:,} تومان\n"
                           "💎 موجودی شما: {balance}\n\n"
                           "📦 پکیج‌های ویژه:",
            'premium_plans': "⭐ *اشتراک پریمیوم*\n\n"
                           "💎 الماس مورد نیاز:\n"
                           "{plans}\n"
                           "💎 موجودی شما: {balance}\n"
                           "⭐ وضعیت: {status}",
            'wallet': "💰 *کیف پول*\n\n"
                     "💎 الماس: {diamonds}\n"
                     "💰 موجودی ریال: {wallet:,} تومان\n\n"
                     "📊 آخرین تراکنش‌ها:\n{transactions}",
            'payment': "💳 *پرداخت*\n\n"
                      "🏦 اطلاعات واریز:\n"
                      "شماره کارت: `{card}`\n"
                      "بانک: {bank}\n"
                      "صاحب حساب: {owner}\n\n"
                      "📝 دستورالعمل:\n"
                      "۱. مبلغ را واریز کنید\n"
                      "۲. رسید را ارسال کنید\n"
                      "۳. شماره کارت مبدا را اعلام کنید",
            'maintenance': "🛠 ربات در حال بروزرسانی است.\n"
                          "زمان تقریبی: 15 دقیقه",
            'rate_limit': "⏳ لطفاً کمی صبر کنید.\n"
                         "سرعت درخواست‌های شما بالاست.",
            'language_changed': "🌐 زبان شما به {lang} تغییر کرد.",
            'admin_required': "⛔ این دستور فقط برای ادمین‌ها قابل استفاده است.",
            'owner_required': "⛔ این دستور فقط برای مالک اصلی است.",
            'user_not_found': "❌ کاربر یافت نشد.",
            'success': "✅ عملیات با موفقیت انجام شد.",
            'failed': "❌ عملیات ناموفق بود.",
            'pending': "⏳ در حال انتظار برای تایید.",
            'invoice_created': "🧾 فاکتور ایجاد شد.\n"
                              "شماره فاکتور: {number}\n"
                              "مبلغ: {amount:,} تومان\n"
                              "وضعیت: در انتظار تایید",
            'premium_activated': "⭐ اشتراک پریمیوم شما فعال شد!\n"
                               "اعتبار تا: {expire}",
            'diamonds_purchased': "💎 {amount} الماس به حساب شما اضافه شد.",
            'withdraw_request': "🏦 درخواست برداشت ثبت شد.\n"
                              "مبلغ: {amount:,} تومان\n"
                              "وضعیت: در انتظار بررسی",
            'insufficient_diamonds': "❌ الماس کافی ندارید!\n"
                                    "نیاز: {need} 💎\n"
                                    "موجودی: {balance} 💎",
            'no_invoices': "📋 هیچ فاکتوری ثبت نشده است.",
            'receipt_received': "✅ رسید شما دریافت شد.\n"
                              "پس از تایید ادمین، الماس به حساب شما اضافه می‌شود.",
            'receipt_error': "❌ فاکتور در انتظار پرداختی یافت نشد.",
            'broadcast_sent': "✅ Broadcast ارسال شد!\n"
                            "تعداد کل: {total}\n"
                            "ارسال شده: {sent}",
            'backup_created': "🔄 بکاپ ایجاد شد.\n"
                             "📅 {date}",
            'version': "🤖 Ghost Assistant\n"
                      "نسخه: {version}\n"
                      "آخرین بروزرسانی: {update}",
            'help_text': "📚 *راهنمای ربات*\n\n"
                        "/start - شروع و منوی اصلی\n"
                        "/menu - منوی اصلی\n"
                        "/profile - پروفایل کاربری\n"
                        "/wallet - کیف پول\n"
                        "/diamonds - خرید الماس\n"
                        "/premium - اشتراک پریمیوم\n"
                        "/payment - پرداخت\n"
                        "/invoice - فاکتورها\n"
                        "/history - تاریخچه تراکنش‌ها\n"
                        "/settings - تنظیمات\n"
                        "/language - تغییر زبان\n"
                        "/support - پشتیبانی\n"
                        "/ads - تبلیغات\n"
                        "/ai - هوش مصنوعی\n\n"
                        "📢 کانال: https://t.me/+NnHHB5BhE785OTRk\n"
                        "👥 گروه: https://t.me/+9-hhQFaMoiAwYjc0\n"
                        "🆔 پشتیبانی: @XMrHadi",
            'support_text': "📞 *پشتیبانی*\n\n"
                           "برای ارتباط با پشتیبانی، از راه‌های زیر استفاده کنید:\n"
                           "🆔 تلگرام: @XMrHadi\n"
                           "👥 گروه: https://t.me/+9-hhQFaMoiAwYjc0\n"
                           "📢 کانال: https://t.me/+NnHHB5BhE785OTRk\n\n"
                           "ساعات پاسخگویی: ۹ صبح تا ۱۱ شب"
        },
        'en': {
            'welcome_new': "🎉 Welcome to Ghost Assistant {name}!\n\n"
                          "💎 You received {gift} diamonds as a gift.\n"
                          "Use the menu below:",
            'welcome_back': "👋 Welcome back {name}!\n"
                           "Use the menu below:",
            'menu_header': "📋 *Main Menu*\n"
                          "Please select an option:",
            'profile': "👤 *User Profile*\n\n"
                      "🆔 ID: {id}\n"
                      "👤 Name: {name}\n"
                      "🌐 Language: {lang}\n"
                      "💎 Diamonds: {diamonds}\n"
                      "  ├─ Gifted: {gifted}\n"
                      "  └─ Purchased: {purchased}\n"
                      "⭐ Premium: {premium}\n"
                      "💰 Wallet: {wallet:,} IRR\n"
                      "📅 Joined: {joined}",
            'diamonds_shop': "💎 *Diamond Shop*\n\n"
                           "💰 Price per diamond: {price:,} IRR\n"
                           "💎 Your balance: {balance}\n\n"
                           "📦 Special packs:",
            'premium_plans': "⭐ *Premium Subscription*\n\n"
                           "💎 Diamonds required:\n"
                           "{plans}\n"
                           "💎 Your balance: {balance}\n"
                           "⭐ Status: {status}",
            'wallet': "💰 *Wallet*\n\n"
                     "💎 Diamonds: {diamonds}\n"
                     "💰 IRR Balance: {wallet:,}\n\n"
                     "📊 Recent transactions:\n{transactions}",
            'payment': "💳 *Payment*\n\n"
                      "🏦 Transfer information:\n"
                      "Card Number: `{card}`\n"
                      "Bank: {bank}\n"
                      "Account Holder: {owner}\n\n"
                      "📝 Instructions:\n"
                      "1. Transfer the amount\n"
                      "2. Send receipt\n"
                      "3. Provide sender card number",
            'maintenance': "🛠 Bot is under maintenance.\n"
                          "Estimated time: 15 minutes",
            'rate_limit': "⏳ Please wait a moment.\n"
                         "Your request rate is too high.",
            'language_changed': "🌐 Your language changed to {lang}.",
            'admin_required': "⛔ This command is only for admins.",
            'owner_required': "⛔ This command is only for the owner.",
            'user_not_found': "❌ User not found.",
            'success': "✅ Operation successful.",
            'failed': "❌ Operation failed.",
            'pending': "⏳ Waiting for confirmation.",
            'invoice_created': "🧾 Invoice created.\n"
                              "Invoice Number: {number}\n"
                              "Amount: {amount:,} IRR\n"
                              "Status: Pending",
            'premium_activated': "⭐ Your premium subscription activated!\n"
                               "Expires: {expire}",
            'diamonds_purchased': "💎 {amount} diamonds added to your account.",
            'withdraw_request': "🏦 Withdrawal request submitted.\n"
                              "Amount: {amount:,} IRR\n"
                              "Status: Pending review",
            'insufficient_diamonds': "❌ Insufficient diamonds!\n"
                                    "Need: {need} 💎\n"
                                    "Balance: {balance} 💎",
            'no_invoices': "📋 No invoices found.",
            'receipt_received': "✅ Receipt received.\n"
                              "After admin verification, diamonds will be added.",
            'receipt_error': "❌ No pending invoice found.",
            'broadcast_sent': "✅ Broadcast sent!\n"
                            "Total: {total}\n"
                            "Sent: {sent}",
            'backup_created': "🔄 Backup created.\n"
                             "📅 {date}",
            'version': "🤖 Ghost Assistant\n"
                      "Version: {version}\n"
                      "Last Update: {update}",
            'help_text': "📚 *Bot Help*\n\n"
                        "/start - Start and main menu\n"
                        "/menu - Main menu\n"
                        "/profile - User profile\n"
                        "/wallet - Wallet\n"
                        "/diamonds - Buy diamonds\n"
                        "/premium - Premium subscription\n"
                        "/payment - Payment\n"
                        "/invoice - Invoices\n"
                        "/history - Transaction history\n"
                        "/settings - Settings\n"
                        "/language - Change language\n"
                        "/support - Support\n"
                        "/ads - Ads\n"
                        "/ai - AI Assistant\n\n"
                        "📢 Channel: https://t.me/+NnHHB5BhE785OTRk\n"
                        "👥 Group: https://t.me/+9-hhQFaMoiAwYjc0\n"
                        "🆔 Support: @XMrHadi",
            'support_text': "📞 *Support*\n\n"
                           "Contact us through:\n"
                           "🆔 Telegram: @XMrHadi\n"
                           "👥 Group: https://t.me/+9-hhQFaMoiAwYjc0\n"
                           "📢 Channel: https://t.me/+NnHHB5BhE785OTRk\n\n"
                           "Response time: 9 AM to 11 PM"
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
        except:
            return None
        finally:
            session.close()
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        session = Session()
        try:
            return session.query(User).filter_by(id=user_id).first()
        except:
            return None
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
            
            transaction = Transaction(
                user_id=user.id,
                type='gift',
                status='completed',
                diamonds_amount=Config.GIFT_DIAMONDS,
                description='هدیه ثبت‌نام / Welcome gift',
                diamonds_before=0,
                diamonds_after=Config.GIFT_DIAMONDS,
                completed_at=datetime.now()
            )
            session.add(transaction)
            
            audit = AuditLog(
                user_id=user.id,
                action='register',
                description='New user registered',
                details={'gifted_diamonds': Config.GIFT_DIAMONDS}
            )
            session.add(audit)
            session.commit()
            
            logger.info(f"New user registered: {telegram_id}")
            return user
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating user: {e}")
            raise
        finally:
            session.close()
    
    @staticmethod
    def update_user_balance(user_id: int, diamonds: int = None, wallet: float = None):
        session = Session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return None
            
            if diamonds is not None:
                user.diamonds_balance += diamonds
            if wallet is not None:
                user.wallet_balance += wallet
            
            user.updated_at = datetime.now()
            session.commit()
            return user
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating user balance: {e}")
            raise
        finally:
            session.close()
    
    @staticmethod
    def create_transaction(user_id: int, type: str, amount: float = 0, 
                          diamonds_amount: int = 0, description: str = None,
                          reference_id: str = None) -> Transaction:
        session = Session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                raise ValueError("User not found")
            
            transaction = Transaction(
                user_id=user_id,
                type=type,
                status='pending',
                amount=amount,
                diamonds_amount=diamonds_amount,
                description=description,
                reference_id=reference_id,
                balance_before=user.wallet_balance,
                diamonds_before=user.diamonds_balance
            )
            session.add(transaction)
            session.commit()
            return transaction
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating transaction: {e}")
            raise
        finally:
            session.close()
    
    @staticmethod
    def complete_transaction(transaction_id: int, status: str = 'completed'):
        session = Session()
        try:
            transaction = session.query(Transaction).filter_by(id=transaction_id).first()
            if not transaction:
                raise ValueError("Transaction not found")
            
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
        except Exception as e:
            session.rollback()
            logger.error(f"Error completing transaction: {e}")
            raise
        finally:
            session.close()

# ==================== MAIN BOT CLASS ====================
class GhostBot:
    def __init__(self, token: str):
        self.token = token
        self.redis = RedisManager()
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone(Config.TIMEZONE))
        
        self.WAITING_FOR_BROADCAST = 1
        self.WAITING_FOR_RECEIPT = 2
        self.WAITING_FOR_WITHDRAW = 3
        self.WAITING_FOR_CARD = 4
        
        self.application = ApplicationBuilder().token(token).build()
        self.setup_handlers()
        self.setup_scheduled_jobs()
        
        logger.info("Bot initialized successfully")
    
    def setup_handlers(self):
        """Register all handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("menu", self.menu_command))
        self.application.add_handler(CommandHandler("profile", self.profile_command))
        self.application.add_handler(CommandHandler("wallet", self.wallet_command))
        self.application.add_handler(CommandHandler("diamonds", self.diamonds_command))
        self.application.add_handler(CommandHandler("premium", self.premium_command))
        self.application.add_handler(CommandHandler("payment", self.payment_command))
        self.application.add_handler(CommandHandler("invoice", self.invoice_command))
        self.application.add_handler(CommandHandler("history", self.history_command))
        self.application.add_handler(CommandHandler("settings", self.settings_command))
        self.application.add_handler(CommandHandler("language", self.language_command))
        self.application.add_handler(CommandHandler("support", self.support_command))
        self.application.add_handler(CommandHandler("ads", self.ads_command))
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("broadcast", self.broadcast_command))
        self.application.add_handler(CommandHandler("backup", self.backup_command))
        self.application.add_handler(CommandHandler("ai", self.ai_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("version", self.version_command))
        self.application.add_handler(CommandHandler("cancel", self.cancel_command))
        
        self.application.add_handler(CallbackQueryHandler(self.callback_handler))
        
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_handler))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.photo_handler))
        self.application.add_handler(MessageHandler(filters.VOICE, self.voice_handler))
        self.application.add_handler(MessageHandler(filters.Document.ALL, self.document_handler))
        
        self.application.add_error_handler(self.error_handler)
    
    def setup_scheduled_jobs(self):
        """Setup scheduled jobs"""
        self.scheduler.add_job(
            self.daily_backup,
            CronTrigger(hour=2, minute=0),
            id='daily_backup'
        )
        
        self.scheduler.add_job(
            self.cleanup_expired_premium,
            CronTrigger(hour=3, minute=0),
            id='cleanup_premium'
        )
        
        self.scheduler.add_job(
            self.update_ad_stats,
            CronTrigger(hour='*/6'),
            id='update_ads'
        )
        
        self.scheduler.start()
        logger.info("Scheduled jobs started")
    
    # ==================== COMMAND HANDLERS ====================
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        if await self.is_maintenance_mode() and str(user.id) not in Config.OWNER_IDS:
            await update.message.reply_text(I18n.get_text('maintenance'))
            return
        
        db_user = DBManager.create_user(
            str(user.id),
            user.username,
            user.first_name,
            user.last_name
        )
        
        lang = db_user.language
        name = user.first_name or user.username or 'کاربر'
        
        if db_user.created_at.date() == datetime.now().date():
            welcome = I18n.get_text('welcome_new', lang, name=name, gift=Config.GIFT_DIAMONDS)
        else:
            welcome = I18n.get_text('welcome_back', lang, name=name)
        
        keyboard = [
            [InlineKeyboardButton("💎 الماس", callback_data="diamonds"),
             InlineKeyboardButton("⭐ پریمیوم", callback_data="premium")],
            [InlineKeyboardButton("💰 کیف پول", callback_data="wallet"),
             InlineKeyboardButton("👤 پروفایل", callback_data="profile")],
            [InlineKeyboardButton("📢 تبلیغات", callback_data="ads"),
             InlineKeyboardButton("🤖 هوش مصنوعی", callback_data="ai")],
            [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings"),
             InlineKeyboardButton("📊 تاریخچه", callback_data="history")],
            [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")]
        ]
        reply
