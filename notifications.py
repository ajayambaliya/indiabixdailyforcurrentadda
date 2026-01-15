import requests
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

class NotificationSender:
    """Handles sending push notifications via OneSignal REST API."""
    
    def __init__(self, app_id: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize the notification sender.
        
        Args:
            app_id: OneSignal App ID
            api_key: OneSignal REST API Key
        """
        self.app_id = (app_id or os.getenv("ONESIGNAL_APP_ID", "")).strip()
        self.api_key = (api_key or os.getenv("ONESIGNAL_REST_API_KEY", "")).strip()
        
        if not self.app_id or not self.api_key:
            logger.warning("OneSignal App ID or API Key missing. Notifications will be skipped.")
            self.enabled = False
        else:
            self.enabled = True
            self.header = {
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Basic {self.api_key}"
            }

    def send_quiz_notification(self, date_str: str, quiz_slug: str) -> bool:
        """
        Send a notification to all subscribed users about a new quiz.
        
        Args:
            date_str: The date string to display (e.g., "13 January 2026")
            quiz_slug: The slug used to build the live link
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False

        url = "https://onesignal.com/api/v1/notifications"
        
        # Build the message
        title = "🎯 IndiaBix નવી ક્વિઝ ઉપલબ્ધ છે!"
        message = f"તારીખ {date_str} IndiaBixની ડેઈલી કરંટ અફેસ ક્વિઝ લાઈવ થઈ ગઈ છે. હમણાં જ રમો!"
        launch_url = f"https://currentadda.vercel.app/quiz/{quiz_slug}"

        payload = {
            "app_id": self.app_id,
            # Use filters instead of segments for 100% targeting
            "filters": [
                {"field": "last_session", "relation": ">", "value": "0"}
            ],
            "headings": {"en": title},
            "contents": {"en": message},
            "url": launch_url,
            "isAnyWeb": True,
            "chrome_web_icon": "https://currentadda.vercel.app/newlogo.png",
            "chrome_web_badge": "https://currentadda.vercel.app/newlogo.png",
            "android_visibility": 1,
            "priority": 10
        }

        try:
            response = requests.post(url, headers=self.header, data=json.dumps(payload))
            response_data = response.json()
            
            if response.status_code == 200:
                recipients = response_data.get('recipients', 0)
                if recipients == 0:
                    logger.warning(f"⚠️ OneSignal sent message but targeted 0 recipients. Response: {response_data}")
                    logger.info("Tip: Check your OneSignal Dashboard -> Audience -> Segments to ensure 'Subscribed Users' isn't empty.")
                else:
                    logger.info(f"✅ OneSignal: Notification sent! Recipients: {recipients}")
                return True
            else:
                logger.error(f"❌ OneSignal API Error: {response_data}")
                return False
        except Exception as e:
            logger.error(f"❌ Network Error: {str(e)}")
            return False

class TelegramSender:
    """Handles sending notifications to Telegram via Bot API."""
    
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None, base_url: Optional[str] = None):
        self.bot_token = (bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")).strip()
        self.chat_id = (chat_id or os.getenv("TELEGRAM_CHAT_ID", "")).strip()
        self.base_url = (base_url or os.getenv("DOMAIN_URL", "https://currentadda.vercel.app")).strip().rstrip("/")
        self.channel_link = os.getenv("TELEGRAM_CHANNEL_LINK", "https://t.me/currentadda").strip()
        
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram Bot Token or Chat ID missing. Telegram notifications will be skipped.")
            self.enabled = False
        else:
            self.enabled = True

    def send_quiz_notification(self, date_str: str, quiz_slug: str) -> bool:
        if not self.enabled:
            return False

        quiz_url = f"{self.base_url}/quiz/{quiz_slug}"
        
        # Beautifully formatted message in Gujarati
        message = (
            f"🎯 *IndiaBix નવી ડેઈલી કરંટ અફેસ ક્વિઝ લાઈવ!*\n\n"
            f"📅 *તારીખ:* {date_str}\n\n"
            f"📝 દરેક પ્રશ્નના જવાબ સાથે સમજૂતી પણ આપવામાં આવેલ છે.\n\n"
            f"🔗 *ક્વિઝ રમવા માટે નીચેની લિંક પર ક્લિક કરો:*\n"
            f"{quiz_url}\n\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📢 વધુ અપડેટ્સ માટે અમારી ચેનલ જોઈન કરો:\n"
            f"👉 {self.channel_link}\n\n"
            f"#CurrentAffairs #IndiaBix #DailyQuiz #GSSSB #GPSC #GujaratGK #CurrentAdda"
        )

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False
        }

        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                logger.info("✅ Telegram: Notification sent successfully!")
                return True
            else:
                logger.error(f"❌ Telegram API Error: {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Telegram Network Error: {str(e)}")
            return False
